from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import db_helper
from app.models.pvp import PVPMatch
from app.models.user import User
from app.core.schemas.auth import UserResponse
from app.core.utils import get_current_user 
from datetime import datetime, timedelta
from typing import List

router = APIRouter(prefix="/pvp", tags=["pvp"])

@router.get("/stats")
async def get_pvp_stats(
    current_user: User = Depends(get_current_user),  # или ваш метод аутентификации
    session: AsyncSession = Depends(db_helper.session_getter)
):
    # 1. Статистика матчей
    matches_query = select(PVPMatch).where(
        (PVPMatch.player1_id == current_user.id) | 
        (PVPMatch.player2_id == current_user.id)
    ).order_by(PVPMatch.finished_at.desc())
    
    result = await session.execute(matches_query)
    all_matches = result.scalars().all()
    
    # 2. Подсчёт статистики
    total = len(all_matches)
    wins = losses = draws = 0
    
    for match in all_matches:
        if match.result == "player1_win" and match.player1_id == current_user.id:
            wins += 1
        elif match.result == "player2_win" and match.player2_id == current_user.id:
            wins += 1
        elif match.result == "draw":
            draws += 1
        else:
            losses += 1
    
    win_rate = round((wins / total * 100), 1) if total > 0 else 0
    
    # 3. История матчей (последние 10)
    history = []
    for match in all_matches[:10]:
        opponent_id = match.player2_id if match.player1_id == current_user.id else match.player1_id
        opponent = await session.get(User, opponent_id)
        
        # Определяем результат для текущего пользователя
        if match.result == "draw":
            result_str = "draw"
        elif (match.result == "player1_win" and match.player1_id == current_user.id) or \
             (match.result == "player2_win" and match.player2_id == current_user.id):
            result_str = "win"
        else:
            result_str = "loss"
        
        # Изменение рейтинга
        rating_change = 0
        if match.player1_id == current_user.id:
            rating_change = (match.player1_rating_after or 0) - match.player1_rating_before
        else:
            rating_change = (match.player2_rating_after or 0) - match.player2_rating_before
        
        history.append({
            "id": match.id,
            "date": match.finished_at.strftime("%Y-%m-%d") if match.finished_at else "—",
            "opponent": opponent.email.split("@")[0] if opponent else "Unknown",
            "result": result_str,
            "rating_change": rating_change,
            "score": f"{match.player1_score}:{match.player2_score}"
        })
    
    # 4. История рейтинга (последние 10 матчей для графика)
    rating_history = []
    current_rating = current_user.elo_rating or 1000
    for i, match in enumerate(reversed(all_matches[-10:])):  # последние 10 в хронологическом порядке
        if match.player1_id == current_user.id:
            rating = match.player1_rating_after or match.player1_rating_before
        else:
            rating = match.player2_rating_after or match.player2_rating_before
        
        rating_history.append({
            "match": i + 1,
            "rating": rating,
            "date": match.finished_at.strftime("%d.%m") if match.finished_at else "—"
        })
    
    return {
        "current_rating": current_user.elo_rating or 1000,
        "total_matches": total,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": win_rate,
        "matches_history": history,
        "rating_history": rating_history
    }