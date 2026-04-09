import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.circle import Circle
from app.models.member import MemberCircleHistory


async def create_circle(
    session: AsyncSession,
    topic_id: uuid.UUID,
    name: str,
    scoped_title: str | None = None,
) -> Circle:
    circle = Circle(topic_id=topic_id, name=name, scoped_title=scoped_title)
    session.add(circle)
    await session.flush()
    return circle


async def rename_circle(
    session: AsyncSession,
    circle_id: uuid.UUID,
    name: str | None = None,
    scoped_title: str | None = None,
) -> Circle:
    result = await session.execute(select(Circle).where(Circle.id == circle_id))
    circle = result.scalar_one_or_none()
    if circle is None:
        raise ValueError("Circle not found")
    if name is not None:
        circle.name = name
    if scoped_title is not None:
        circle.scoped_title = scoped_title
    session.add(circle)
    await session.flush()
    return circle


async def delete_circle(session: AsyncSession, circle_id: uuid.UUID) -> None:
    # Check for active members
    result = await session.execute(
        select(MemberCircleHistory).where(
            MemberCircleHistory.circle_id == circle_id,
            MemberCircleHistory.revoked_at.is_(None),  # type: ignore[union-attr]
        )
    )
    if result.scalars().first() is not None:
        raise ValueError("Cannot delete circle with active members")

    result = await session.execute(select(Circle).where(Circle.id == circle_id))
    circle = result.scalar_one_or_none()
    if circle is None:
        raise ValueError("Circle not found")
    await session.delete(circle)


async def list_circles(session: AsyncSession, topic_id: uuid.UUID) -> list[Circle]:
    result = await session.execute(select(Circle).where(Circle.topic_id == topic_id))
    return list(result.scalars().all())
