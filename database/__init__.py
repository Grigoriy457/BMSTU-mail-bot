import config
from database import models

import sqlalchemy
import sqlalchemy.sql
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import IntegrityError
import asyncio
from typing import Union


class Database:
    def __init__(self):
        self.engine = create_async_engine(f"mysql+aiomysql://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}/{config.DB_NAME}", echo=False)
        self.session = async_sessionmaker(bind=self.engine, expire_on_commit=False, autoflush=True)
        self.base = models.Base

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.engine.dispose()

    async def create_all(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(self.base.metadata.create_all)

    async def add_tg_user(self, tg_user_id: int, tg_user_username: str) -> models.TgUser:
        async with self as db:
            async with db.session() as db_session:
                tg_user = await db_session.merge(models.TgUser(id=tg_user_id, username=tg_user_username))
                if tg_user is None:
                    tg_user = models.TgUser(id=tg_user_id, username=tg_user_username)
                tg_user.is_deactivated = False

                try:
                    await db_session.merge(tg_user)
                    await db_session.commit()

                    db_session.expunge(tg_user)
                    sqlalchemy.orm.make_transient(tg_user)
                    return tg_user

                except IntegrityError:
                    await db_session.rollback()


async def get_session() -> AsyncSession:
    async with Database().session() as session:
        yield session


async def _test():
    async with Database() as db:
        await db.create_all()
        # async with db.session() as db_session:
        #     pass


if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(_test())
