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

# 🔴 ВАЖНО: Настройка логирования с выводом в консоль
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Глобальный менеджер процессов
process_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global process_manager
    
    # Берем пути из переменных окружения или используем дефолтные
    llama_cpp_path = os.getenv("LLAMA_CPP_PATH", "./llama-server")
    models_dir = os.getenv("MODELS_DIR", "./models")
    
    # Если пути относительные, делаем их абсолютными относительно рабочей директории
    if not os.path.isabs(llama_cpp_path):
        llama_cpp_path = os.path.join(os.getcwd(), llama_cpp_path)
    if not os.path.isabs(models_dir):
        models_dir = os.path.join(os.getcwd(), models_dir)
    
    logger.info(f"🚀 Llama.cpp path: {llama_cpp_path}")
    logger.info(f"📚 Models dir: {models_dir}")
    logger.info(f"📁 Current working directory: {os.getcwd()}")
    
    process_manager = ProcessManager(
        llama_cpp_path=llama_cpp_path,
        models_dir=models_dir,
        inactivity_timeout=300
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
            logger.error(f"Error in cleanup task: {e}", exc_info=True)
        await asyncio.sleep(5)

@app.get("/v1/models")
async def list_models():
    """Список доступных моделей"""
    if not process_manager:
        raise HTTPException(status_code=500, detail="Process manager not initialized")
    
    models = process_manager.get_available_models()
    logger.info(f"📋 Available models: {models}")
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
    logger.debug(f"💬 Received chat completion request: model={request.model}, messages={len(request.messages)}")
    
    if not process_manager:
        raise HTTPException(status_code=500, detail="Process manager not initialized")
    
    try:
        # 🔴 ИСПРАВЛЕНИЕ: Получаем URL запущенного сервера
        logger.info(f"🔄 Getting server for model: {request.model}")
        base_url = await process_manager.get_server_for_model(request.model)
        logger.info(f"✅ Server URL obtained: {base_url}")
        
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
        
        logger.debug(f"📝 Generated prompt (first 200 chars): {prompt[:200]}...")
        
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
        
        logger.debug(f"⚙️ Request params: {params}")
        
        if request.stream:
            logger.info("🌊 Streaming response")
            return StreamingResponse(
                stream_completion(base_url, params, request.model),
                media_type="text/event-stream"
            )
        else:
            import httpx
            logger.info(f"📡 Sending request to {base_url}/completion")
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{base_url}/completion",
                    json=params,
                    headers={"Content-Type": "application/json"}
                )
                
                logger.info(f"📨 Response status: {response.status_code}")
                logger.debug(f"📨 Response body: {response.text[:500]}")
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"❌ llama.cpp server error: {error_detail}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error_detail
                    )
                
                result = response.json()
                logger.debug(f"✅ Got result from llama.cpp: {result}")
                
                await process_manager.update_activity(request.model)
                
                response_data = {
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
                
                logger.info(f"✅ Returning chat completion response")
                return response_data
            
    except ValueError as e:
        logger.error(f"❌ ValueError: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error in chat completion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/completions")
async def create_completion(request: CompletionRequest):
    """Text completion endpoint"""
    logger.debug(f"📝 Received completion request: model={request.model}")
    
    if not process_manager:
        raise HTTPException(status_code=500, detail="Process manager not initialized")
    
    try:
        # 🔴 КРИТИЧЕСКАЯ ОШИБКА: Было update_activity вместо get_server_for_model!
        logger.info(f"🔄 Getting server for model: {request.model}")
        base_url = await process_manager.get_server_for_model(request.model)  # ← ИСПРАВЛЕНО!
        logger.info(f"✅ Server URL obtained: {base_url}")
        
        params = {
            "prompt": request.prompt if isinstance(request.prompt, str) else "\n".join(request.prompt),
            "stream": request.stream,
            "n_predict": request.max_tokens or 512,
            "temperature": request.temperature or 0.7,
            "top_p": request.top_p or 0.95,
            "stop": request.stop,
            "repeat_penalty": 1.1
        }
        
        logger.debug(f"⚙️ Request params: {params}")
        
        if request.stream:
            logger.info("🌊 Streaming response")
            return StreamingResponse(
                stream_completion(base_url, params, request.model),
                media_type="text/event-stream"
            )
        else:
            import httpx
            logger.info(f"📡 Sending request to {base_url}/completion")
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{base_url}/completion",
                    json=params,
                    headers={"Content-Type": "application/json"}
                )
                
                logger.info(f"📨 Response status: {response.status_code}")
                logger.debug(f"📨 Response body: {response.text[:500]}")
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"❌ llama.cpp server error: {error_detail}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error_detail
                    )
                
                result = response.json()
                logger.debug(f"✅ Got result from llama.cpp: {result}")
                
                await process_manager.update_activity(request.model)
                
                response_data = {
                    "id": f"cmpl-{hash(str(request.prompt))}",
                    "object": "text_completion",
                    "created": int(time.time()),
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
                
                logger.info(f"✅ Returning completion response")
                return response_data
            
    except ValueError as e:
        logger.error(f"❌ ValueError: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error in completion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def stream_completion(base_url: str, params: Dict, model_name: str):
    """Stream ответ"""
    import httpx
    import time
    
    logger.info(f"🌊 Starting stream to {base_url}/completion")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{base_url}/completion",
            json={**params, "stream": True},
            headers={"Content-Type": "application/json"}
        ) as response:
            
            request_id = f"chatcmpl-{int(time.time())}"
            logger.debug(f"🌊 Stream request ID: {request_id}")
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    
                    # [DONE] marker
                    if data.strip() == "[DONE]":
                        logger.debug("🌊 Stream completed")
                        yield "data: [DONE]\n\n"
                        break
                    
                    try:
                        json_data = json.loads(data)
                        content = json_data.get("content", "")
                        
                        # Формируем чанк в формате OpenAI
                        chunk = {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model_name,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": content} if content else {},
                                "finish_reason": None
                            }]
                        }
                        
                        # ВАЖНО: используем ensure_ascii=False для кириллицы и спецсимволов!
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️ Failed to parse line: {line} | Error: {e}")
                        continue
            
            # Обновляем активность ПОСЛЕ завершения стрима
            if process_manager:
                await process_manager.update_activity(model_name)
                logger.debug(f"✅ Updated activity for model: {model_name}")

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
    logger.info("🚀 Starting server on http://0.0.0.0:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="debug")