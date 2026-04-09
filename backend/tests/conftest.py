import os

# Set SECRET_KEY before any app imports to satisfy config validation
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.config import Settings, get_settings
from app.db.session import get_session
from app.main import app
from app.models import (
    Circle,
    Member,
    MemberCircleHistory,
    MemberRole,
    Topic,
)
from app.services.auth import generate_token

TEST_DB_PATH = "/tmp/weft_test.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def engine():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    e = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    async with e.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield e
    await e.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture
async def session(engine):
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as s:
        yield s


@pytest.fixture
async def client(engine):
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session():
        async with sf() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    def override_get_settings():
        return Settings(
            database_url=TEST_DB_URL,
            secret_key="test-secret",
            resend_api_key="",
            base_url="http://localhost:5173",
        )

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_settings] = override_get_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
async def topic_with_creator(session):
    """Create a topic with a creator and return (topic, creator, raw_token)."""
    topic = Topic(default_title="Test Topic")
    session.add(topic)
    await session.flush()

    creator = Member(topic_id=topic.id, role=MemberRole.creator, email="creator@test.com")
    session.add(creator)
    await session.flush()

    raw_token = await generate_token(session, creator.id)
    await session.commit()

    return topic, creator, raw_token


@pytest.fixture
async def circle_with_members(session, topic_with_creator):
    """Create a circle with two recipient members."""
    topic, creator, _ = topic_with_creator

    circle = Circle(topic_id=topic.id, name="Family")
    session.add(circle)
    await session.flush()

    members = []
    tokens = []
    for i in range(2):
        m = Member(
            topic_id=topic.id,
            role=MemberRole.recipient,
            email=f"recipient{i}@test.com",
        )
        session.add(m)
        await session.flush()

        history = MemberCircleHistory(member_id=m.id, circle_id=circle.id)
        session.add(history)

        raw_token = await generate_token(session, m.id)
        members.append(m)
        tokens.append(raw_token)

    await session.commit()
    return circle, members, tokens
