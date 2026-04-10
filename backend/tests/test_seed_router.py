# Copyright 2026 Chris Wells <chris@tholent.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the test-seed router.

Two classes:
  (A) env == "test"  — happy-path reset + seed, returns usable tokens.
  (B) env != "test"  — router is not mounted; endpoints return 404.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.config import Settings, get_settings
from app.db.session import get_session
from app.routers import test_seed

# ---------------------------------------------------------------------------
# (A) env == "test" — build a fresh FastAPI app that mounts the seed router
#     directly so we bypass the import-time guard in main.py.
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///./weft_seed_test.db"


@pytest.fixture
async def seed_engine():
    import os

    db_path = "./weft_seed_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    e = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    async with e.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield e
    await e.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
async def seed_client(seed_engine):
    """AsyncClient wired to a fresh FastAPI app with the seed router mounted."""
    sf = async_sessionmaker(seed_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_session():
        async with sf() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    def override_settings():
        return Settings(
            database_url=TEST_DB_URL,
            secret_key="test-secret-seed",
            resend_api_key="",
            base_url="http://localhost:5173",
            env="test",
        )

    test_app = FastAPI()
    test_app.include_router(test_seed.router)
    test_app.dependency_overrides[get_session] = override_session
    test_app.dependency_overrides[get_settings] = override_settings

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_reset_returns_ok(seed_client):
    """POST /test/seed/reset returns 200 and {ok: true}."""
    response = await seed_client.post("/test/seed/reset")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


@pytest.mark.anyio
async def test_seed_topic_minimal(seed_client):
    """POST /test/seed/topic with a minimal spec returns topic_id and owner_token."""
    payload = {"title": "Minimal Seed", "owner_email": "owner@seed.test"}
    response = await seed_client.post("/test/seed/topic", json=payload)
    assert response.status_code == 200, response.text

    data = response.json()
    assert "topic_id" in data
    assert "owner_token" in data
    assert data["owner_token"]  # non-empty string
    assert data["topic_id"]  # non-empty string


@pytest.mark.anyio
async def test_seed_topic_with_circles_and_members(seed_client):
    """POST /test/seed/topic with circles/members returns circle_ids and tokens."""
    payload = {
        "title": "E2E Full Seed",
        "owner_email": "owner@seed.test",
        "circles": [
            {
                "name": "Family",
                "members": [
                    {"email": "alice@seed.test", "role": "recipient"},
                    {"email": "mod@seed.test", "role": "moderator"},
                ],
            }
        ],
    }
    response = await seed_client.post("/test/seed/topic", json=payload)
    assert response.status_code == 200, response.text

    data = response.json()
    assert "Family" in data["circle_ids"]
    assert "alice@seed.test" in data["recipient_tokens"]
    assert "mod@seed.test" in data["moderator_tokens"]


@pytest.mark.anyio
async def test_seed_topic_with_updates_and_replies(seed_client):
    """POST /test/seed/topic with updates/replies creates them successfully."""
    payload = {
        "title": "With Updates",
        "owner_email": "owner@seed.test",
        "circles": [{"name": "All", "members": []}],
        "updates": [
            {
                "body": "Hello everyone",
                "circle_names": ["All"],
                "author_email": "owner@seed.test",
            }
        ],
        "replies": [
            {
                "update_index": 0,
                "author_email": "owner@seed.test",
                "body": "Replying to my own update",
            }
        ],
    }
    response = await seed_client.post("/test/seed/topic", json=payload)
    assert response.status_code == 200, response.text

    data = response.json()
    assert data["topic_id"]


@pytest.mark.anyio
async def test_owner_token_is_valid(seed_client, seed_engine):
    """The owner_token returned by /test/seed/topic authenticates on the real app."""
    # Seed a topic
    payload = {"title": "Token Verify Test", "owner_email": "owner@verify.test"}
    response = await seed_client.post("/test/seed/topic", json=payload)
    assert response.status_code == 200, response.text
    seed_data = response.json()
    owner_token = seed_data["owner_token"]
    topic_id = seed_data["topic_id"]

    # Build a second client wired to the same DB but using the real app
    from app.main import app as real_app

    sf = async_sessionmaker(seed_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_session():
        async with sf() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    def override_settings():
        return Settings(
            database_url=TEST_DB_URL,
            secret_key="test-secret-seed",
            resend_api_key="",
            base_url="http://localhost:5173",
            env="test",
        )

    real_app.dependency_overrides[get_session] = override_session
    real_app.dependency_overrides[get_settings] = override_settings
    try:
        transport = ASGITransport(app=real_app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            # GET /topics/{topic_id} is an authenticated endpoint; a 401 means
            # the bearer token was not recognised, anything else means it was.
            verify_response = await c.get(
                f"/topics/{topic_id}",
                headers={"Authorization": f"Bearer {owner_token}"},
            )
            assert verify_response.status_code != 401, (
                f"Owner token was rejected as unauthorised: {verify_response.text}"
            )
    finally:
        real_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# (B) env != "test" — use the existing `client` fixture which has env == "dev"
#     The seed router is not mounted; all paths under /test/seed return 404.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_seed_reset_absent_when_not_test_env(client):
    """POST /test/seed/reset returns 404 when env != 'test'."""
    response = await client.post("/test/seed/reset")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_seed_topic_absent_when_not_test_env(client):
    """POST /test/seed/topic returns 404 when env != 'test'."""
    response = await client.post("/test/seed/topic", json={})
    assert response.status_code == 404
