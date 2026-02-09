# app/repositories/pvp_repository.py
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.pvp import PVPMatch
from app.models.user import User
from datetime import datetime
from typing import Optional, List

class PVPMatchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_match(self, player1_id: int, player2_id: int, player1_rating: int, player2_rating: int, tasks: list) -> PVPMatch:
        """Создать новый матч"""
        match = PVPMatch(
            player1_id=player1_id,
            player2_id=player2_id,
            player1_score=0,
            player2_score=0,
            player1_rating_before=player1_rating,
            player2_rating_before=player2_rating,
            status="active",
            tasks_used=tasks
        )
        self.session.add(match)
        await self.session.flush()
        return match
    
    async def get_match(self, match_id: int) -> Optional[PVPMatch]:
        """Получить матч по ID"""
        stmt = select(PVPMatch).where(PVPMatch.id == match_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_score(self, match_id: int, player1_score: int, player2_score: int):
        """Обновить счет в матче"""
        stmt = (
            update(PVPMatch)
            .where(PVPMatch.id == match_id)
            .values(
                player1_score=player1_score,
                player2_score=player2_score
            )
        )
        await self.session.execute(stmt)
    
    async def finish_match(
        self, 
        match_id: int, 
        p1_score: int, 
        p2_score: int, 
        p1_rating_after: int, 
        p2_rating_after: int,
        result: str = None  # ← ДОБАВИТЬ ЭТУ СТРОКУ
    ):
        match = await self.session.get(PVPMatch, match_id)
        if match:
            match.player1_score = p1_score
            match.player2_score = p2_score
            match.player1_rating_after = p1_rating_after
            match.player2_rating_after = p2_rating_after
            match.status = "finished"
            match.finished_at = datetime.utcnow()
            if result:  
                match.result = result
            await self.session.commit()
    
    async def cancel_match(self, match_id: int, reason: str):
        """Отменить матч"""
        stmt = (
            update(PVPMatch)
            .where(PVPMatch.id == match_id)
            .values(
                status="cancelled",
                cancellation_reason=reason,
                finished_at=datetime.utcnow()
            )
        )
        await self.session.execute(stmt)
    
    def _calculate_result(self, p1_score: int, p2_score: int) -> str:
        """Определить результат матча"""
        if p1_score > p2_score:
            return "player1_win"
        elif p2_score > p1_score:
            return "player2_win"
        else:
            return "draw"
    
    async def get_user_matches(self, user_id: int, limit: int = 20) -> List[PVPMatch]:
        """Получить историю матчей пользователя"""
        stmt = (
            select(PVPMatch)
            .where(
                (PVPMatch.player1_id == user_id) | (PVPMatch.player2_id == user_id)
            )
            .order_by(PVPMatch.started_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_elo_rating(self, user_id: int, new_rating: int):
        """Обновить рейтинг пользователя"""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(elo_rating=new_rating)
        )
        await self.session.execute(stmt)
    
    async def get_users_by_rating_range(self, min_rating: int, max_rating: int, limit: int = 10):
        """Получить пользователей в диапазоне рейтинга"""
        stmt = (
            select(User)
            .where(
                User.elo_rating >= min_rating,
                User.elo_rating <= max_rating
            )
            .order_by(User.elo_rating.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()