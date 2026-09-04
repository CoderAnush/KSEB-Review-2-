from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.domain.enums import Role


class UsersRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, username: str, password_hash: str, role: Role) -> int:
        user = User(username=username, password_hash=password_hash, role=role.value)
        self.session.add(user)
        await self.session.flush()
        return user.id

    async def get_by_username(self, username: str) -> dict | None:
        stmt = select(User).where(User.username == username)
        row = (await self.session.execute(stmt)).scalars().first()
        if row is None:
            return None
        return {"id": row.id, "username": row.username, "password_hash": row.password_hash, "role": row.role}

    async def list(self) -> list[dict]:
        rows = (await self.session.execute(select(User).order_by(User.id))).scalars().all()
        return [{"id": r.id, "username": r.username, "role": r.role} for r in rows]
