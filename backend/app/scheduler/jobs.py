from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler.tasks import auto_archive_task, transfer_deadline_task


async def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(auto_archive_task, "interval", hours=24, id="auto_archive")
    scheduler.add_job(transfer_deadline_task, "interval", minutes=5, id="transfer_deadline")
    scheduler.start()
    return scheduler


async def shutdown_scheduler(scheduler: AsyncIOScheduler) -> None:
    scheduler.shutdown(wait=False)
