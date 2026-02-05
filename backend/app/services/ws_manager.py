from fastapi import WebSocket
from typing import Dict, Any, Optional
import json
import asyncio
import random
from ..models.content import ContentUnit
from datetime import datetime
from sqlalchemy import select, func
from app.core.database import db_helper
from app.models.content import Task
from app.repositories.pvp_repository import PVPMatchRepository, UserRepository
from jose import jwt
from app.core.config import settings

class PVPGameManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.matchmaking_queue: Dict[int, Dict[str, Any]] = {}
        self.private_rooms: Dict[str, Dict[str, Any]] = {}
        self.active_games: Dict[str, Dict[str, Any]] = {}
        self.user_games: Dict[int, str] = {}
        self.game_timers: Dict[str, asyncio.Task] = {}
        self.game_locks: Dict[str, asyncio.Lock] = {}
        self.K = 32

    # --- АВТОРИЗАЦИЯ ---
    async def authenticate_user(self, token: str) -> Optional[int]:
        if not token:
            print("🔴 WS Auth: Токен отсутствует")
            return None
        try:
            if token.startswith("Bearer "):
                token = token.split(" ")[1]
            secret = settings.security.JWT_SECRET_KEY.get_secret_value()
            algo = settings.security.JWT_ALGORITHM
            payload = jwt.decode(token, secret, algorithms=[algo])
            return int(payload.get("sub"))
        except Exception as e:
            print(f"🔴 WS Auth Error: {e}")
            return None

    # --- ПОДКЛЮЧЕНИЕ ---
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"🟢 User {user_id} connected")
        
        # Реконнект
        if user_id in self.user_games:
            game_id = self.user_games[user_id]
            if game_id in self.active_games:
                await self._handle_reconnect(user_id, game_id)
                return

        # Приветствие
        async with db_helper.session_factory() as session:
            user = await UserRepository(session).get_user_by_id(user_id)
            rating = user.elo_rating if user else 1000
            await self.send_personal_message({
                "type": "welcome", 
                "user_id": user_id, 
                "elo_rating": rating
            }, user_id)

    async def _handle_reconnect(self, user_id: int, game_id: str):
        game = self.active_games[game_id]
        uid_str = str(user_id)
        current_idx = game["task_index"].get(uid_str, 0)
        
        if current_idx < len(game["tasks"]):
            current_task = game["tasks"][current_idx]
            await self.send_personal_message({
                "type": "game_restore",
                "game_id": game_id,
                "status": game["status"],
                "timer": game["timer"],
                "scores": game["scores"],
                "current_task": current_task,
                "task_number": current_idx + 1,
                "total_tasks": len(game["tasks"])
            }, user_id)

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.matchmaking_queue:
            del self.matchmaking_queue[user_id]
        rooms_to_delete = [
            code for code, data in self.private_rooms.items() 
            if isinstance(data, dict) and data.get('host_id') == user_id
        ]
        for code in rooms_to_delete:
            del self.private_rooms[code]
        
        if user_id in self.user_games:
            game_id = self.user_games[user_id]
            if game_id in self.active_games:
                print(f"⚠️ Player {user_id} disconnected during game {game_id}")
                asyncio.create_task(self.finish_game(game_id, error=True))

    # --- ОТПРАВКА СООБЩЕНИЙ ---
    async def send_personal_message(self, message: dict, user_id: int):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                self.disconnect(user_id)

    async def broadcast_to_game(self, game_id: str, message: dict):
        game = self.active_games.get(game_id)
        if game:
            await self.send_personal_message(message, game["p1"])
            await self.send_personal_message(message, game["p2"])

    # --- МАТЧЕЙКИНГ ---
    async def find_match(self, user_id: int):
        if user_id in self.user_games:
            return
        
        async with db_helper.session_factory() as session:
            user = await UserRepository(session).get_user_by_id(user_id)
            rating = user.elo_rating if user else 1000

        self.matchmaking_queue[user_id] = {
            "joined_at": datetime.utcnow(),
            "rating": rating
        }
        await self.send_personal_message({"type": "status", "status": "searching"}, user_id)
        await self._attempt_matchmaking(user_id, rating)

    async def _attempt_matchmaking(self, user_id: int, rating: int):
        candidates = [(uid, data) for uid, data in self.matchmaking_queue.items() if uid != user_id]
        if candidates:
            best_opponent = candidates[0][0]
            del self.matchmaking_queue[user_id]
            del self.matchmaking_queue[best_opponent]
            await self.start_game(user_id, best_opponent)

    # --- ПРИВАТНЫЕ КОМНАТЫ ---
    async def create_private_room(self, user_id: int, topic_id: Optional[int] = None, task_count: int = 5):
        code = str(random.randint(1000, 9999))
        while code in self.private_rooms:
            code = str(random.randint(1000, 9999))
        
        self.private_rooms[code] = {
            "host_id": user_id,
            "topic_id": topic_id,
            "task_count": max(1, min(task_count, 10))
        }
        
        await self.send_personal_message({
            "type": "room_created",
            "room_code": code,
            "topic_id": topic_id,
            "task_count": task_count
        }, user_id)

    async def join_private_room(self, user_id: int, code: str):
        room = self.private_rooms.get(code)
        if not room:
            await self.send_personal_message({"type": "error", "message": "Комната не найдена"}, user_id)
            return
        
        del self.private_rooms[code]
        await self.start_game(
            room["host_id"], 
            user_id, 
            room.get("topic_id"), 
            room.get("task_count", 5)
        )

    # --- СТАРТ ИГРЫ (ЕДИНСТВЕННЫЙ МЕТОД) ---
    async def start_game(self, p1_id: int, p2_id: int, topic_id: Optional[int] = None, task_count: int = 5):
        task_count = max(1, min(task_count, 10))
        tasks = await self._get_random_tasks(task_count, topic_id)
        
        if not tasks or len(tasks) < 1:
            error_msg = "Недостаточно задач в системе. Обратитесь к администратору."
            print(f"❌ NO TASKS! Notifying players {p1_id}, {p2_id}")
            await self._notify_players_and_cleanup(p1_id, p2_id, error_msg)
            return

        async with db_helper.session_factory() as session:
            user_repo = UserRepository(session)
            p1 = await user_repo.get_user_by_id(p1_id)
            p2 = await user_repo.get_user_by_id(p2_id)
            
            if not p1 or not p2:
                await self._notify_players_and_cleanup(p1_id, p2_id, "Один из игроков не найден в системе")
                return

            p1_rating = p1.elo_rating if p1.elo_rating is not None else 1000
            p2_rating = p2.elo_rating if p2.elo_rating is not None else 1000

            match_repo = PVPMatchRepository(session)
            tasks_meta = [{"id": t["id"], "type": t["type"]} for t in tasks]
            match = await match_repo.create_match(p1_id, p2_id, p1_rating, p2_rating, tasks_meta)
            await session.commit()
            match_id = match.id

        # 🎯 СОЗДАЁМ ИГРУ С НОВОЙ СТРУКТУРОЙ
        game_id = f"game_{match_id}"
        self.user_games[p1_id] = game_id
        self.user_games[p2_id] = game_id
        self.game_locks[game_id] = asyncio.Lock()
        
        # 🔑 КРИТИЧЕСКИ ВАЖНАЯ СТРУКТУРА (БЕЗ СТАРЫХ ПОЛЕЙ!)
        game_state = {
            "game_id": game_id,
            "match_id": match_id,
            "p1": p1_id, 
            "p2": p2_id,
            "p1_rating": p1_rating, 
            "p2_rating": p2_rating,
            "scores": {str(p1_id): 0, str(p2_id): 0},
            "tasks": tasks,
            "task_index": {str(p1_id): 0, str(p2_id): 0},  # ← НОВОЕ
            "finished_players": set(),  # ← НОВОЕ
            "status": "countdown",
            "timer": 60
        }
        self.active_games[game_id] = game_state  # ← СОХРАНЯЕМ СРАЗУ!

        # 📡 ОБРАТНЫЙ ОТСЧЁТ
        print(f"📤 Sending countdown to {game_id}")
        for i in [3, 2, 1]:
            await self.broadcast_to_game(game_id, {"type": "countdown", "value": i})
            await asyncio.sleep(1)
        
        # 🚀 СТАРТ ИГРЫ С ПРОГРЕССОМ СОПЕРНИКА
        game_state["status"] = "playing"
        print(f"🚀 GAME STARTED: {game_id}")
        
        # 🔑 ОТПРАВЛЯЕМ КАЖДОМУ ИГРОКУ ОТДЕЛЬНОЕ СООБЩЕНИЕ С ПРОГРЕССОМ СОПЕРНИКА
        for player_id in [p1_id, p2_id]:
            await self.send_personal_message({
                "type": "game_start",
                "current_task": tasks[0],
                "task_number": 1,
                "total_tasks": len(tasks),
                "timer": 60,
                "opponent_solved": 0,   # ← Прогресс соперника
                "opponent_score": 0     # ← Счёт соперника
            }, player_id)
        
        # ⏱️ ЗАПУСКАЕМ ТАЙМЕР
        self.game_timers[game_id] = asyncio.create_task(self._game_loop(game_id))

    async def _notify_players_and_cleanup(self, p1_id: int, p2_id: int, message: str):
        for uid in [p1_id, p2_id]:
            if uid in self.active_connections:
                await self.send_personal_message({"type": "error", "message": message}, uid)
        
        self.matchmaking_queue.pop(p1_id, None)
        self.matchmaking_queue.pop(p2_id, None)
        
        rooms_to_delete = [
            code for code, data in self.private_rooms.items() 
            if isinstance(data, dict) and data.get('host_id') in (p1_id, p2_id)
        ]
        for code in rooms_to_delete:
            del self.private_rooms[code]

    async def _game_loop(self, game_id: str):
        try:
            while True:
                game = self.active_games.get(game_id)
                if not game or game["status"] != "playing":
                    break
                if game["timer"] <= 0:
                    await self.finish_game(game_id)
                    break
                await asyncio.sleep(1)
                game["timer"] -= 1
                await self.broadcast_to_game(game_id, {"type": "timer_update", "timer": game["timer"]})
        except Exception:
            await self.finish_game(game_id, error=True)

    # --- ОБРАБОТКА ОТВЕТОВ (НЕЗАВИСИМОЕ ПРОХОЖДЕНИЕ) ---
    async def handle_answer(self, user_id: int, game_id: str, answer: str):
        game = self.active_games.get(game_id)
        if not game or game["status"] != "playing" or user_id not in [game["p1"], game["p2"]]:
            return
        
        uid_str = str(user_id)
        current_idx = game["task_index"][uid_str]
        
        # Проверка: игрок уже завершил?
        if uid_str in game["finished_players"] or current_idx >= len(game["tasks"]):
            return
        
        # Проверка ответа
        current_task = game["tasks"][current_idx]
        is_correct = self._validate_answer(answer, current_task)
        if is_correct:
            game["scores"][uid_str] += 1
        
        # Отправка результата ТОЛЬКО этому игроку
        await self.send_personal_message({"type": "answer_result", "is_correct": is_correct}, user_id)
        
        # Переход к следующей задаче
        game["task_index"][uid_str] += 1
        next_idx = game["task_index"][uid_str]
        
        # Проверка завершения игроком
        if next_idx >= len(game["tasks"]):
            game["finished_players"].add(uid_str)
            await self.finish_game(game_id)
            return
        
        # Отправка следующей задачи ТОЛЬКО этому игроку
        await self.send_personal_message({
            "type": "next_task",
            "current_task": game["tasks"][next_idx],
            "task_number": next_idx + 1,
            "total_tasks": len(game["tasks"])
        }, user_id)
        
        # 🔑 ОТПРАВКА ПРОГРЕССА СОПЕРНИКУ
        opponent_id = game["p1"] if user_id == game["p2"] else game["p2"]
        opponent_str = str(opponent_id)
        if opponent_str not in game["finished_players"]:
            await self.send_personal_message({
                "type": "opponent_progress",
                "opponent_solved": next_idx,  # Сколько задач РЕШИЛ текущий игрок
                "opponent_score": game["scores"][uid_str]
            }, opponent_id)

    def _validate_answer(self, user_ans: str, task: dict) -> bool:
        correct = str(task["correct_answer"]).strip().lower().replace(',', '.')
        user = str(user_ans).strip().lower().replace(',', '.')
        return user == correct

    async def finish_game(self, game_id: str, error: bool = False):
        game = self.active_games.get(game_id)
        if not game:
            return
        
        if game_id in self.game_timers: 
            self.game_timers[game_id].cancel()
        
        p1_id, p2_id = game["p1"], game["p2"]
        s1 = game["scores"].get(str(p1_id), 0)
        s2 = game["scores"].get(str(p2_id), 0)
        
        # Расчёт Elo
        p1_r, p2_r = game["p1_rating"], game["p2_rating"]
        e1 = 1 / (1 + 10 ** ((p2_r - p1_r) / 400))
        e2 = 1 / (1 + 10 ** ((p1_r - p2_r) / 400))
        r1 = 1 if s1 > s2 else (0.5 if s1 == s2 else 0)
        r2 = 1 - r1
        new_r1 = round(p1_r + self.K * (r1 - e1))
        new_r2 = round(p2_r + self.K * (r2 - e2))
        
        async with db_helper.session_factory() as session:
            if not error:
                ur = UserRepository(session)
                mr = PVPMatchRepository(session)
                await ur.update_elo_rating(p1_id, new_r1)
                await ur.update_elo_rating(p2_id, new_r2)
                await mr.finish_match(game["match_id"], s1, s2, new_r1, new_r2)
                await session.commit()
            else:
                await PVPMatchRepository(session).cancel_match(game["match_id"], "server_error")
                await session.commit()
        
        # Отправка результата
        await self.broadcast_to_game(game_id, {
            "type": "game_finished",
            "scores": game["scores"],
            "rating_changes": {str(p1_id): new_r1 - p1_r, str(p2_id): new_r2 - p2_r},
            "winner_id": None if s1 == s2 else (p1_id if s1 > s2 else p2_id)
        })
        
        # Очистка
        self.user_games.pop(p1_id, None)
        self.user_games.pop(p2_id, None)
        self.active_games.pop(game_id, None)
        self.game_locks.pop(game_id, None)

    async def _get_random_tasks(self, limit: int, topic_id: Optional[int] = None):
        async with db_helper.session_factory() as session:
            stmt = select(Task).where(
                Task.validation.is_not(None),
                Task.validation["correct_answer"].astext.is_not(None)
            )
            if topic_id is not None:
                stmt = stmt.join(ContentUnit).where(ContentUnit.topic_id == topic_id)
            
            stmt = stmt.order_by(func.random()).limit(limit)
            result = await session.execute(stmt)
            raw_tasks = result.scalars().all()
            
            return [{
                "id": t.id,
                "question": t.content.get("question", "Вопрос"),
                "options": t.content.get("options", []),
                "type": t.type,
                "correct_answer": t.validation.get("correct_answer")
            } for t in raw_tasks if t.validation.get("correct_answer")]

    # --- ОБРАБОТКА СООБЩЕНИЙ ОТ КЛИЕНТА ---
    async def handle_client_message(self, websocket: WebSocket, user_id: int, data: str):
        try:
            payload = json.loads(data)
            action = payload.get("action")
            
            if action == "find_match":
                await self.find_match(user_id)
            
            elif action == "create_room":
                # 🔑 ИЗВЛЕКАЕМ ПАРАМЕТРЫ ИЗ СООБЩЕНИЯ
                topic_id = payload.get("topic_id")
                task_count = payload.get("task_count", 5)
                await self.create_private_room(user_id, topic_id, task_count)
                
            elif action == "join_room":
                code = payload.get("code")
                await self.join_private_room(user_id, code)
                
            elif action == "submit_answer":
                game_id = self.user_games.get(user_id)
                if game_id:
                    await self.handle_answer(user_id, game_id, payload.get("answer"))
            
            elif action == "cancel_search":
                if user_id in self.matchmaking_queue:
                    del self.matchmaking_queue[user_id]
                    await self.send_personal_message({"type": "status", "status": "idle"}, user_id)
                    print(f"🛑 User {user_id} cancelled matchmaking")
                
                rooms_to_del = [
                    code for code, data in self.private_rooms.items() 
                    if isinstance(data, dict) and data.get('host_id') == user_id
                ]
                for code in rooms_to_del:
                    del self.private_rooms[code]
                    print(f"🚪 Room {code} deleted by host {user_id}")
                
                if user_id in self.user_games:
                    game_id = self.user_games[user_id]
                    if game_id in self.active_games:
                        await self.finish_game(game_id, error=True)
                        print(f"⚠️ Game {game_id} cancelled by player {user_id}")
                    
        except Exception as e:
            print(f"Error msg: {e}")

manager = PVPGameManager()