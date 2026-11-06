"""Выдача роли для разработки: python -m app.scripts.set_role <login> <user|moderator|admin>.

Роль лежит только в БД (`users.role`), в токене её нет, поэтому смена
действует со следующего же запроса пользователя.
"""

import argparse
import asyncio
import sys

from sqlalchemy import func, select

from app.core.constants import ROLE_LEVEL
from app.db.session import SessionLocal, engine
from app.models.user import User


async def set_role(login: str, role: str) -> str:
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(func.lower(User.login) == login.strip().lower()))
        if user is None:
            raise SystemExit(f"Пользователь «{login}» не найден")
        old, user.role = user.role, role
        await db.commit()
    await engine.dispose()
    return f"@{user.login}: {old} → {role}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Выдать роль пользователю (только для разработки)")
    parser.add_argument("login")
    parser.add_argument("role", choices=sorted(ROLE_LEVEL, key=ROLE_LEVEL.get))
    args = parser.parse_args(argv)
    print(asyncio.run(set_role(args.login, args.role)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
