from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.ws_manager import manager
import json

router = APIRouter(tags=["websocket"])

@router.websocket("/ws/pvp")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    
    if not token:
        print("🔴 WS: Попытка подключения без токена")
        await websocket.close(code=1008, reason="Token required")
        return
    
    user_id = await manager.authenticate_user(token)
    
    if not user_id:
        print(f"🔴 WS: Авторизация не удалась для токена: {token[:10]}...")
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            await manager.handle_client_message(websocket, user_id, data)
    
    except WebSocketDisconnect:
        print(f"🟡 WS: Пользователь {user_id} отключился")
        manager.disconnect(user_id)
    except Exception as e:
        print(f"🔴 WS: Ошибка сокета для пользователя {user_id}: {e}")
        manager.disconnect(user_id)