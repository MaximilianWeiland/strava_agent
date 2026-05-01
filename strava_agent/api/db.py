import json
import asyncpg

pool: asyncpg.Pool | None = None


async def init_db(dsn: str) -> None:
    # ensure to modify the global (module-level) pool variable
    global pool
    # create connection via database url
    pool = await asyncpg.create_pool(dsn)
    # create the table storing conversation history
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                session_id TEXT PRIMARY KEY,
                input_items JSONB NOT NULL DEFAULT '[]',
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)


async def close_db() -> None:
    if pool:
        await pool.close()


async def get_input_items(session_id: str) -> list:
    # get conversation history from the current session id
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT input_items FROM conversations WHERE session_id = $1",
            session_id,
        )
        return json.loads(row["input_items"]) if row else []


async def save_input_items(session_id: str, items: list) -> None:
    # insert message into the table, if session already exists update the row
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO conversations (session_id, input_items, updated_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (session_id) DO UPDATE
            SET input_items = $2::jsonb, updated_at = NOW()
            """,
            session_id,
            json.dumps(items),
        )
