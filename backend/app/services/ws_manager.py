from fastapi import WebSocket
from typing import Dict, Any, Optional, Set
import json
import asyncio
import random
from datetime import datetime
from sqlalchemy import select, func
from app.core.database import db_helper
from app.models.content import Task, Lecture
from app.models.content import ContentUnit  
from app.repositories.pvp_repository import PVPMatchRepository, UserRepository
from app.models.pvp import PVPMatch
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
        self.MAX_ATTEMPTS_PER_TASK = 3  # Лимит попыток на задачу

    # === АВТОРИЗАЦИЯ ===
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

    # === ПОДКЛЮЧЕНИЕ/ОТКЛЮЧЕНИЕ ===
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"🟢 User {user_id} connected")
        
        # Реконнект в игру
        if user_id in self.user_games:
            game_id = self.user_games[user_id]
            if game_id in self.active_games:
                await self._handle_reconnect(user_id, game_id)
                return
        
        # Приветствие с рейтингом
        async with db_helper.session_factory() as session:
            user = await UserRepository(session).get_user_by_id(user_id)
            rating = user.elo_rating if user and user.elo_rating is not None else 1000
            await self.send_personal_message({
                "type": "welcome",
                "user_id": user_id,
                "elo_rating": rating
            }, user_id)

    async def _handle_reconnect(self, user_id: int, game_id: str):
        game = self.active_games.get(game_id)
        if not game:
            return
        
        uid_str = str(user_id)
        current_task = game["tasks"][game["current_task_index"]]
        
        await self.send_personal_message({
            "type": "game_restore",
            "game_id": game_id,
            "status": game["status"],
            "timer": game["timer"],
            "scores": game["scores"],
            "current_task": current_task,
            "task_number": game["current_task_index"] + 1,
            "total_tasks": len(game["tasks"]),
            "attempts_left": self.MAX_ATTEMPTS_PER_TASK - game["attempts"].get(uid_str, 0),
            "opponent_progress": {
                "solved": game["current_task_index"] + 1 if game["answers_submitted"].get(str(game["p2"] if user_id == game["p1"] else game["p1"]), False) else game["current_task_index"],
                "score": game["scores"].get(str(game["p2"] if user_id == game["p1"] else game["p1"]), 0)
            }
        }, user_id)

    def disconnect(self, user_id: int):
        """Обработка отключения игрока (обрыв соединения = поражение)"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        # Удаляем из очереди поиска
        self.matchmaking_queue.pop(user_id, None)
        
        # Удаляем созданные комнаты
        rooms_to_delete = [
            code for code, data in self.private_rooms.items()
            if isinstance(data, dict) and data.get('host_id') == user_id
        ]
        for code in rooms_to_delete:
            del self.private_rooms[code]
        
        # Обработка отключения во время матча
        if user_id in self.user_games:
            game_id = self.user_games[user_id]
            if game_id in self.active_games:
                print(f"⚠️ Player {user_id} DISCONNECTED during game {game_id} → FORFEIT")
                asyncio.create_task(self.finish_game(game_id, disconnected_player_id=user_id, reason="disconnection"))

    # === ОТПРАВКА СООБЩЕНИЙ ===
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

    # === МАТЧЕЙКИНГ С НАСТРОЙКАМИ ===
    async def find_match_with_settings(self, user_id: int, topic_id: Optional[int] = None, 
                                      task_count: int = 5, match_duration: int = 300):
        if user_id in self.user_games:
            return
        
        async with db_helper.session_factory() as session:
            user = await UserRepository(session).get_user_by_id(user_id)
            rating = user.elo_rating if user and user.elo_rating is not None else 1000
        
        self.matchmaking_queue[user_id] = {
            "joined_at": datetime.utcnow(),
            "rating": rating,
            "topic_id": topic_id,
            "task_count": max(1, min(task_count, 10)),
            "match_duration": max(60, min(match_duration, 1800))
        }
        await self.send_personal_message({"type": "status", "status": "searching"}, user_id)
        await self._attempt_matchmaking(user_id, rating, topic_id, task_count, match_duration)

    async def _attempt_matchmaking(self, user_id: int, rating: int, topic_id: Optional[int] = None,
                                  task_count: int = 5, match_duration: int = 300):
        candidates = [
            (uid, data) for uid, data in self.matchmaking_queue.items() 
            if uid != user_id and 
            (data.get("topic_id") == topic_id or topic_id is None)
        ]
        
        if candidates:
            best_opponent = candidates[0][0]
            opp_data = self.matchmaking_queue[best_opponent]
            
            # Используем настройки первого игрока
            final_topic = topic_id if topic_id is not None else opp_data.get("topic_id")
            final_tasks = min(task_count, opp_data.get("task_count", 5), 10)
            final_duration = min(match_duration, opp_data.get("match_duration", 300), 1800)
            
            del self.matchmaking_queue[user_id]
            del self.matchmaking_queue[best_opponent]
            
            await self.start_game(
                user_id, 
                best_opponent, 
                final_topic, 
                final_tasks, 
                final_duration
            )

    # === ПРИВАТНЫЕ КОМНАТЫ С НАСТРОЙКАМИ ===
    async def create_private_room(self, user_id: int, topic_id: Optional[int] = None, 
                                 task_count: int = 5, match_duration: int = 300):
        code = str(random.randint(1000, 9999))
        while code in self.private_rooms:
            code = str(random.randint(1000, 9999))
        
        self.private_rooms[code] = {
            "host_id": user_id,
            "topic_id": topic_id,
            "task_count": max(1, min(task_count, 10)),
            "match_duration": max(60, min(match_duration, 1800))
        }
        await self.send_personal_message({
            "type": "room_created",
            "room_code": code,
            "topic_id": topic_id,
            "task_count": task_count,
            "match_duration": match_duration
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
            room.get("task_count", 5),
            room.get("match_duration", 300)
        )

    # === СТАРТ ИГРЫ (СИНХРОННОЕ РЕШЕНИЕ ЗАДАЧ) ===
    async def start_game(self, p1_id: int, p2_id: int, topic_id: Optional[int] = None, 
                        task_count: int = 5, match_duration: int = 300):
        task_count = max(1, min(task_count, 10))
        match_duration = max(60, min(match_duration, 1800))
        
        tasks = await self._get_random_tasks(task_count, topic_id)
        if not tasks or len(tasks) < task_count:
            error_msg = f"Недостаточно задач. Доступно: {len(tasks) if tasks else 0}"
            await self._notify_players_and_cleanup(p1_id, p2_id, error_msg)
            return

        async with db_helper.session_factory() as session:
            user_repo = UserRepository(session)
            p1 = await user_repo.get_user_by_id(p1_id)
            p2 = await user_repo.get_user_by_id(p2_id)
            if not p1 or not p2:
                await self._notify_players_and_cleanup(p1_id, p2_id, "Один из игроков не найден")
                return

            p1_rating = p1.elo_rating if p1.elo_rating is not None else 1000
            p2_rating = p2.elo_rating if p2.elo_rating is not None else 1000
            
            match_repo = PVPMatchRepository(session)
            tasks_meta = [{"id": t["id"], "type": t["type"]} for t in tasks]
            match = await match_repo.create_match(p1_id, p2_id, p1_rating, p2_rating, tasks_meta)
            await session.commit()
            match_id = match.id

        game_id = f"game_{match_id}"
        self.user_games[p1_id] = game_id
        self.user_games[p2_id] = game_id
        self.game_locks[game_id] = asyncio.Lock()

        # 🔑 КРИТИЧЕСКИ ВАЖНАЯ СТРУКТУРА С СИНХРОННЫМИ ЗАДАЧАМИ
        game_state = {
            "game_id": game_id,
            "match_id": match_id,
            "p1": p1_id,
            "p2": p2_id,
            "p1_rating": p1_rating,
            "p2_rating": p2_rating,
            "scores": {str(p1_id): 0, str(p2_id): 0},
            "tasks": tasks,
            "current_task_index": 0,  # ← ОДНА ЗАДАЧА ДЛЯ ОБОИХ
            "attempts": {str(p1_id): 0, str(p2_id): 0},  # Попытки на текущей задаче
            "answers_submitted": {str(p1_id): False, str(p2_id): False},  # Ответил ли игрок на текущую задачу
            "finished_players": set(),
            "status": "countdown",
            "match_duration": match_duration,
            "timer": match_duration,
            "start_time": datetime.utcnow()
        }
        self.active_games[game_id] = game_state

        # Обратный отсчёт
        for i in [3, 2, 1]:
            await self.broadcast_to_game(game_id, {"type": "countdown", "value": i})
            await asyncio.sleep(1)

        # Старт игры
        game_state["status"] = "playing"
        current_task = tasks[0]
        await self.broadcast_to_game(game_id, {
            "type": "game_start",
            "current_task": current_task,
            "task_number": 1,
            "total_tasks": len(tasks),
            "timer": match_duration,
            "attempts_left": self.MAX_ATTEMPTS_PER_TASK
        })

        # Запуск таймера матча
        self.game_timers[game_id] = asyncio.create_task(self._game_loop(game_id))

    # === ИГРОВОЙ ЦИКЛ (ОБЩЕЕ ВРЕМЯ МАТЧА) ===
    async def _game_loop(self, game_id: str):
        try:
            while True:
                game = self.active_games.get(game_id)
                if not game or game["status"] != "playing":
                    break
                
                if game["timer"] <= 0:
                    await self.finish_game(game_id, reason="time_over")
                    break
                
                await asyncio.sleep(1)
                game["timer"] -= 1
                
                # Отправляем обновление каждые 5 сек или при критическом времени
                if game["timer"] % 5 == 0 or game["timer"] <= 10:
                    p1_done = str(game["p1"]) in game["finished_players"]
                    p2_done = str(game["p2"]) in game["finished_players"]
                    await self.broadcast_to_game(game_id, {
                        "type": "match_update",
                        "timer": game["timer"],
                        "current_task_index": game["current_task_index"],
                        "scores": game["scores"],
                        "p1_done": p1_done,
                        "p2_done": p2_done
                    })
        except Exception as e:
            print(f"⚠️ Ошибка в игровом цикле {game_id}: {e}")
            await self.finish_game(game_id, reason="error")

    # === ОБРАБОТКА ОТВЕТА (С ПОВТОРНЫМИ ПОПЫТКАМИ) ===
    async def handle_answer(self, user_id: int, game_id: str, answer: str):
        game = self.active_games.get(game_id)
        if not game or game["status"] != "playing":
            return
        
        uid_str = str(user_id)
        opponent_id = game["p2"] if user_id == game["p1"] else game["p1"]
        opponent_str = str(opponent_id)
        
        # Проверка: игрок уже завершил матч?
        if uid_str in game["finished_players"]:
            return
        
        # Проверка: игрок уже ответил на эту задачу?
        if game["answers_submitted"][uid_str]:
            await self.send_personal_message({
                "type": "error",
                "message": "Вы уже ответили на эту задачу"
            }, user_id)
            return
        
        # Проверка лимита попыток
        game["attempts"][uid_str] += 1
        attempts_left = self.MAX_ATTEMPTS_PER_TASK - game["attempts"][uid_str]
        
        current_task = game["tasks"][game["current_task_index"]]
        is_correct = self._validate_answer(answer, current_task)
        
        if is_correct:
            game["scores"][uid_str] += 1
            game["answers_submitted"][uid_str] = True
        elif attempts_left <= 0:
            # Исчерпаны попытки - помечаем как завершившего задачу без очка
            game["answers_submitted"][uid_str] = True
            # Отправляем уведомление игроку об исчерпании попыток
            await self.send_personal_message({
                "type": "attempts_exhausted",
                "correct_answer": current_task["correct_answer"]
            }, user_id)
        
        # Отправляем результат игроку
        await self.send_personal_message({
            "type": "answer_result",
            "is_correct": is_correct,
            "attempts_left": attempts_left if not is_correct and attempts_left > 0 else 0,
            "correct_answer": current_task["correct_answer"] if is_correct else None
        }, user_id)
        
        # Отправляем обновление прогресса сопернику
        await self.send_personal_message({
            "type": "opponent_progress",
            "opponent_answered": game["answers_submitted"][uid_str],
            "opponent_score": game["scores"][uid_str]
        }, opponent_id)
        
        # Проверка: оба игрока завершили текущую задачу?
        p1_submitted = game["answers_submitted"][str(game["p1"])]
        p2_submitted = game["answers_submitted"][str(game["p2"])]
        
        if p1_submitted and p2_submitted:
            # Переход к следующей задаче
            game["current_task_index"] += 1
            game["attempts"] = {str(game["p1"]): 0, str(game["p2"]): 0}
            game["answers_submitted"] = {str(game["p1"]): False, str(game["p2"]): False}
            
            if game["current_task_index"] >= len(game["tasks"]):
                # Оба игрока завершили все задачи
                game["finished_players"].update([str(game["p1"]), str(game["p2"])])
                await self.finish_game(game_id, reason="all_tasks_completed")
            else:
                # Следующая задача
                next_task = game["tasks"][game["current_task_index"]]
                await self.broadcast_to_game(game_id, {
                    "type": "next_task",
                    "current_task": next_task,
                    "task_number": game["current_task_index"] + 1,
                    "total_tasks": len(game["tasks"]),
                    "attempts_left": self.MAX_ATTEMPTS_PER_TASK
                })

    # === ВЫХОД ИЗ МАТЧА (ЗАСЧИТЫВАЕТСЯ ПОРАЖЕНИЕ) ===
    async def leave_game(self, user_id: int, game_id: str):
        """Обработка сознательного выхода игрока из матча"""
        game = self.active_games.get(game_id)
        if not game:
            return
        
        print(f"🚪 Player {user_id} LEFT game {game_id} → FORFEIT")
        await self.finish_game(game_id, disconnected_player_id=user_id, reason="player_left")

    # === ЗАВЕРШЕНИЕ МАТЧА (С РАСЧЁТОМ ELO) ===
    async def finish_game(self, game_id: str, reason: str = "completed", 
                         disconnected_player_id: Optional[int] = None, error: bool = False):
        game = self.active_games.get(game_id)
        if not game:
            return
        
        # Останавливаем таймер
        if game_id in self.game_timers:
            self.game_timers[game_id].cancel()
        
        p1_id, p2_id = game["p1"], game["p2"]
        s1 = game["scores"].get(str(p1_id), 0)
        s2 = game["scores"].get(str(p2_id), 0)
        
        # Обработка выхода/отключения игрока
        if disconnected_player_id is not None:
            if disconnected_player_id == p1_id:
                winner_id = p2_id
                s1 = -1  # Помечаем как проигравшего
            else:
                winner_id = p1_id
                s2 = -1
            result_str = "player1_win" if winner_id == p1_id else "player2_win"
        elif error:
            # Техническая ошибка - отмена матча, рейтинг не меняется
            async with db_helper.session_factory() as session:
                await PVPMatchRepository(session).cancel_match(
                    game["match_id"], 
                    f"error_{reason}"
                )
                await session.commit()
            await self.broadcast_to_game(game_id, {
                "type": "game_cancelled",
                "reason": "Техническая ошибка. Рейтинги не изменены."
            })
            self._cleanup_game(game_id)
            return
        else:
            # Обычное завершение
            if s1 > s2:
                winner_id = p1_id
                result_str = "player1_win"
            elif s2 > s1:
                winner_id = p2_id
                result_str = "player2_win"
            else:
                winner_id = None
                result_str = "draw"
        
        # Расчёт Elo
        p1_r, p2_r = game["p1_rating"], game["p2_rating"]
        if disconnected_player_id is not None:
            # Принудительная победа оставшегося игрока
            r1 = 1.0 if winner_id == p1_id else 0.0
            r2 = 1.0 - r1
        else:
            # Стандартный расчёт по формуле Elo
            e1 = 1 / (1 + 10 ** ((p2_r - p1_r) / 400))
            e2 = 1 / (1 + 10 ** ((p1_r - p2_r) / 400))
            r1 = 1.0 if s1 > s2 else (0.5 if s1 == s2 else 0.0)
            r2 = 1.0 - r1
        
        new_r1 = round(p1_r + self.K * (r1 - e1))
        new_r2 = round(p2_r + self.K * (r2 - e2))
        
        # Сохранение в БД
        async with db_helper.session_factory() as session:
            ur = UserRepository(session)
            mr = PVPMatchRepository(session)
            
            # Обновляем рейтинги
            await ur.update_elo_rating(p1_id, new_r1)
            await ur.update_elo_rating(p2_id, new_r2)
            
            # Фиксируем результат матча
            await mr.finish_match(
                game["match_id"], 
                max(s1, 0), 
                max(s2, 0), 
                new_r1, 
                new_r2,
                result=result_str
            )
            await session.commit()
        
        # Отправка результата игрокам
        rating_changes = {
            str(p1_id): new_r1 - p1_r,
            str(p2_id): new_r2 - p2_r
        }
        
        await self.broadcast_to_game(game_id, {
            "type": "game_finished",
            "scores": {
                str(p1_id): max(s1, 0),
                str(p2_id): max(s2, 0)
            },
            "rating_changes": rating_changes,
            "winner_id": winner_id,
            "reason": reason,
            "disconnected_player_id": disconnected_player_id
        })
        
        # Очистка
        self._cleanup_game(game_id)

    def _cleanup_game(self, game_id: str):
        game = self.active_games.get(game_id)
        if not game:
            return
        
        p1_id, p2_id = game["p1"], game["p2"]
        self.user_games.pop(p1_id, None)
        self.user_games.pop(p2_id, None)
        self.active_games.pop(game_id, None)
        self.game_locks.pop(game_id, None)

    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===
    def _validate_answer(self, user_ans: str, task: dict) -> bool:
        correct = str(task["correct_answer"]).strip().lower().replace(',', '.')
        user = str(user_ans).strip().lower().replace(',', '.')
        return user == correct

    async def _get_random_tasks(self, limit: int, topic_id: Optional[int] = None):
        """Получает задачи с учётом структуры: Топик → Юниты → (Задачи напрямую или через Лекцию)"""
        async with db_helper.session_factory() as session:
            # Базовые условия для всех задач
            base_conditions = [
                Task.validation.is_not(None),
                Task.validation["correct_answer"].astext.is_not(None),
                Task.validation["correct_answer"].astext != ""
            ]
            
            if topic_id is None:
                # Все задачи из системы (без привязки к теме)
                stmt = select(Task).where(*base_conditions).order_by(func.random()).limit(limit)
                result = await session.execute(stmt)
                raw_tasks = result.scalars().all()
            else:
                # ЗАДАЧИ ПО ТЕМЕ: два источника
                # 1. Задачи напрямую в юнитах типа 'task'
                stmt_direct = (
                    select(Task)
                    .join(Task.unit)
                    .where(
                        ContentUnit.topic_id == topic_id,
                        ContentUnit.type == "task",
                        *base_conditions
                    )
                )
                
                # 2. Задачи в лекциях юнитов типа 'lecture'
                stmt_via_lecture = (
                    select(Task)
                    .join(Task.lecture)
                    .join(Lecture.unit)
                    .where(
                        ContentUnit.topic_id == topic_id,
                        ContentUnit.type == "lecture",
                        *base_conditions
                    )
                )
                
                # Выполняем оба запроса
                result1 = await session.execute(stmt_direct)
                result2 = await session.execute(stmt_via_lecture)
                
                # Объединяем и перемешиваем
                all_tasks = list(result1.scalars().all()) + list(result2.scalars().all())
                random.shuffle(all_tasks)
                raw_tasks = all_tasks[:limit]
            
            # Формируем результат
            return [{
                "id": t.id,
                "question": t.content.get("question", "Вопрос"),
                "options": t.content.get("options", []),
                "type": t.type,
                "correct_answer": t.validation.get("correct_answer")
            } for t in raw_tasks if t.validation.get("correct_answer")]

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

    # === ОБРАБОТКА СООБЩЕНИЙ ОТ КЛИЕНТА ===
    async def handle_client_message(self, websocket: WebSocket, user_id: int, data: str):
        try:
            payload = json.loads(data)
            action = payload.get("action")
            
            if action == "find_match":
                topic_id = payload.get("topic_id")
                task_count = payload.get("task_count", 5)
                match_duration = payload.get("match_duration", 300)
                await self.find_match_with_settings(user_id, topic_id, task_count, match_duration)
            
            elif action == "create_room":
                topic_id = payload.get("topic_id")
                task_count = payload.get("task_count", 5)
                match_duration = payload.get("match_duration", 300)
                await self.create_private_room(user_id, topic_id, task_count, match_duration)
            
            elif action == "join_room":
                code = payload.get("code")
                await self.join_private_room(user_id, code)
            
            elif action == "submit_answer":
                game_id = self.user_games.get(user_id)
                if game_id:
                    await self.handle_answer(user_id, game_id, payload.get("answer"))
            
            elif action == "leave_game":
                game_id = self.user_games.get(user_id)
                if game_id:
                    await self.leave_game(user_id, game_id)
            
            elif action == "cancel_search":
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
                        await self.finish_game(game_id, error=True)
                await self.send_personal_message({"type": "status", "status": "idle"}, user_id)
                
        except Exception as e:
            print(f"Error handling message: {e}")

# Экземпляр менеджера
manager = PVPGameManager()