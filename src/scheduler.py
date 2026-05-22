"""
Scheduler — fires weekly summary every Sunday at 23:00 Asia/Bangkok.

Uses APScheduler (bundled with python-telegram-bot).
Sends to all chat_ids that have entries this week.
"""

import logging
from datetime import date

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import InputFile, Bot
import io

from storage import Storage
from weekly import week_bounds, build_weekly_xlsx, current_week_label

logger     = logging.getLogger(__name__)
TZ_BANGKOK = pytz.timezone("Asia/Bangkok")


async def send_weekly_summary(bot: Bot, storage: Storage, chat_id: int):
    """Build and send the weekly summary to one chat_id."""
    today  = date.today()
    monday, sunday = week_bounds(today)
    entries = storage.get_week(monday, sunday, chat_id=chat_id)

    if not entries:
        logger.info("WEEKLY  chat=%s  no entries — skipping", chat_id)
        return

    logger.info("WEEKLY  chat=%s  entries=%d  week=%s→%s", chat_id, len(entries), monday, sunday)

    xlsx_bytes = build_weekly_xlsx(entries, today)
    label      = current_week_label(today).replace(" ", "_").replace("–", "-")
    filename   = f"weekly_{label}.xlsx"
    await bot.send_document(
        chat_id=chat_id,
        document=InputFile(io.BytesIO(xlsx_bytes), filename=filename),
        caption=f"📅 Weekly summary — {current_week_label(today)}",
    )


async def _job(bot: Bot, storage: Storage, authorized_chat_id: int):
    """Scheduled job — runs every Sunday 23:00 BKK."""
    if authorized_chat_id:
        await send_weekly_summary(bot, storage, authorized_chat_id)
    else:
        # Multi-user mode: send to all known chat_ids
        for cid in storage.get_distinct_chat_ids():
            try:
                await send_weekly_summary(bot, storage, cid)
            except Exception as e:
                logger.error("WEEKLY  chat=%s  error: %s", cid, e)


def setup_scheduler(bot: Bot, storage: Storage, authorized_chat_id: int) -> AsyncIOScheduler:
    """Create and start the APScheduler. Call after bot app is running."""
    scheduler = AsyncIOScheduler(timezone=TZ_BANGKOK)
    scheduler.add_job(
        _job,
        trigger="cron",
        day_of_week="sun",   # Sunday
        hour=23,
        minute=0,
        args=[bot, storage, authorized_chat_id],
        id="weekly_summary",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — weekly summary every Sunday 23:00 BKK")
    return scheduler
