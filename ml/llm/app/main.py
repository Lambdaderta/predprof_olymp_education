from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import asyncio
import json
import logging
import os
import time
from typing import Dict

from .process_manager import ProcessManager
from .schemas import ChatCompletionRequest, CompletionRequest, ModelListResponse

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальный менеджер процессов
process_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global process_manager
    
    # Берем пути из переменных окружения или используем дефолтные
    llama_cpp_path = os.getenv("LLAMA_CPP_PATH", "./llama.cpp/build/bin/llama-server")
    models_dir = os.getenv("MODELS_DIR", "./models")
    
    # Если пути относительные, делаем их абсолютными относительно рабочей директории
    if not os.path.isabs(llama_cpp_path):
        llama_cpp_path = os.path.join(os.getcwd(), llama_cpp_path)
    if not os.path.isabs(models_dir):
        models_dir = os.path.join(os.getcwd(), models_dir)
    
    logger.info(f"Llama.cpp path: {llama_cpp_path}")
    logger.info(f"Models dir: {models_dir}")
    
    process_manager = ProcessManager(
        llama_cpp_path=llama_cpp_path,
        models_dir=models_dir,
        inactivity_timeout=10
    )
    
    # Запускаем фоновую задачу для очистки
    cleanup_task = asyncio.create_task(cleanup_inactive_servers())
    
    yield
    
    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    
    if process_manager:
        await process_manager.cleanup_all()

app = FastAPI(
    title="Llama.cpp OpenAI API",
    description="OpenAI-compatible API for llama.cpp with on-demand server startup",
    version="1.0.0",
    lifespan=lifespan
)

async def cleanup_inactive_servers():
    """Фоновая задача для очистки неактивных серверов"""
    while True:
        try:
            if process_manager:
                await process_manager.cleanup_inactive()
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
        await asyncio.sleep(5)

@app.get("/v1/models")
async def list_models():
    """Список доступных моделей"""
    if not process_manager:
        raise HTTPException(status_code=500, detail="Process manager not initialized")
    
    models = process_manager.get_available_models()
    return ModelListResponse(data=[
        {
            "id": model_name,
            "object": "model",
            "owned_by": "local"
        }
        for model_name in models
    ])

@app.post("/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    """Chat completion endpoint (OpenAI compatible)"""
    if not process_manager:
        raise HTTPException(status_code=500, detail="Process manager not initialized")
    
    try:
        # Получаем URL запущенного сервера
        base_url = await process_manager.get_server_for_model(request.model)
        
        # Формируем промпт для llama.cpp из истории диалога
        prompt = ""
        for msg in request.messages:
            role = msg.role
            content = msg.content
            
            if role == "system":
                prompt += f"### System:\n{content}\n\n"
            elif role == "user":
                prompt += f"### User:\n{content}\n\n"
            elif role == "assistant":
                prompt += f"### Assistant:\n{content}\n\n"
        
        prompt += "### Assistant:\n"
        
        # Подготавливаем параметры для llama.cpp
        params = {
            "prompt": prompt,
            "stream": request.stream,
            "n_predict": request.max_tokens or 512,
            "temperature": request.temperature or 0.7,
            "top_p": request.top_p or 0.95,
            "stop": request.stop or ["### User:"],
            "repeat_penalty": 1.1,
            "top_k": 40
        }
        
        if request.stream:
            return StreamingResponse(
                stream_completion(base_url, params, request.model),
                media_type="text/event-stream"
            )
        else:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{base_url}/completion",
                    json=params,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=response.text
                    )
                
                result = response.json()
                await process_manager.update_activity(request.model)
                
                return {
                    "id": f"chatcmpl-{hash(prompt)}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": result.get("content", "")
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": result.get("tokens_evaluated", 0),
                        "completion_tokens": result.get("tokens_predicted", 0),
                        "total_tokens": result.get("tokens_evaluated", 0) + result.get("tokens_predicted", 0)
                    }
                }
            
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in chat completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/completions")
async def create_completion(request: CompletionRequest):
    """Text completion endpoint"""
    if not process_manager:
        raise HTTPException(status_code=500, detail="Process manager not initialized")
    
    try:
        base_url = await process_manager.update_activity(request.model)
        
        params = {
            "prompt": request.prompt if isinstance(request.prompt, str) else "\n".join(request.prompt),
            "stream": request.stream,
            "n_predict": request.max_tokens or 512,
            "temperature": request.temperature or 0.7,
            "top_p": request.top_p or 0.95,
            "stop": request.stop,
            "repeat_penalty": 1.1
        }
        
        if request.stream:
            return StreamingResponse(
                stream_completion(base_url, params, request.model),
                media_type="text/event-stream"
            )
        else:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{base_url}/completion",
                    json=params,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=response.text
                    )
                
                result = response.json()
                await process_manager.update_activity(request.model)
                
                return {
                    "id": f"cmpl-{hash(str(request.prompt))}",
                    "object": "text_completion",
                    "created": int(asyncio.get_event_loop().time()),
                    "model": request.model,
                    "choices": [{
                        "text": result.get("content", ""),
                        "index": 0,
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": result.get("tokens_evaluated", 0),
                        "completion_tokens": result.get("tokens_predicted", 0),
                        "total_tokens": result.get("tokens_evaluated", 0) + result.get("tokens_predicted", 0)
                    }
                }
            
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def stream_completion(base_url: str, params: Dict, model_name: str):
    """Stream ответ"""
    import httpx
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{base_url}/completion",
            json={**params, "stream": True},
            headers={"Content-Type": "application/json"}
        ) as response:
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        yield f"data: {data}\n\n"
                        break
                    
                    try:
                        json_data = json.loads(data)
                        content = json_data.get("content", "")
                        
                        choice = {
                            "index": 0,
                            "delta": {"content": content} if content else {},
                            "finish_reason": None
                        }
                        
                        event = {
                            "id": f"chatcmpl-{hash(str(params))}",
                            "object": "chat.completion.chunk",
                            "created": int(asyncio.get_event_loop().time()),
                            "model": model_name,
                            "choices": [choice]
                        }
                        
                        yield f"data: {json.dumps(event)}\n\n"
                        
                    except json.JSONDecodeError:
                        continue
            
            if process_manager:
                await process_manager.update_activity(model_name)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if process_manager:
        return {
            "status": "healthy", 
            "models_available": len(process_manager.get_available_models()),
            "active_servers": len(process_manager.active_servers)
        }
    return {"status": "initializing"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)