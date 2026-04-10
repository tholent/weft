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

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.scheduler.tasks import auto_archive_task, digest_notification_task, transfer_deadline_task


async def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(auto_archive_task, "interval", hours=24, id="auto_archive")
    scheduler.add_job(transfer_deadline_task, "interval", minutes=5, id="transfer_deadline")
    scheduler.add_job(digest_notification_task, "interval", hours=1, id="digest_notifications")
    scheduler.start()
    return scheduler


async def shutdown_scheduler(scheduler: AsyncIOScheduler) -> None:
    scheduler.shutdown(wait=False)
