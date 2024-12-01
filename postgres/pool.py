from asyncpg import Pool
from typing import Optional


from postgres.pool_manager import create_pool


class UninitializedDatabasePoolError(Exception):
    def __init__(
            self,
            message="The database connection pool has not been properly initialized.Please ensure setup is called",
    ):
        self.message = message
        super().__init__(self.message)


class DbPool:
    _db_pool: Optional[Pool] = None

    @classmethod
    async def create_pool(cls, timeout: Optional[None] = None):
        cls._db_pool = await create_pool()
        cls._timeout = timeout

    @classmethod
    async def get_pool(cls):
        if not cls._db_pool:
            raise UninitializedDatabasePoolError()
        return cls._db_pool

    @classmethod
    async def close_pool(cls):
        if not cls._db_pool:
            raise UninitializedDatabasePoolError()
        await cls._db_pool.close()
