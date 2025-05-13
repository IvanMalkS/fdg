from db.database import get_async_session
from db.models import User
from db.enums import UserRole
from sqlalchemy.future import select

async def is_user_banned(user_id: int) -> bool:
    async with get_async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalars().first()
        return user and str(user.role) == UserRole.BANNED