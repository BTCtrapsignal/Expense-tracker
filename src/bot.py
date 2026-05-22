import io
import os
import logging
from datetime import date
from telegram import Update, InputFile
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

from parser import parse_entry
from storage import Storage
from formatter import format_sum, format_today
from excel_export import build_xlsx
from weekly import week_bounds, build_weekly_xlsx, current_week_label
from scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Suppress noisy polling / HTTP logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

BOT_TOKEN          = os.environ["TELEGRAM_BOT_TOKEN"]
AUTHORIZED_CHAT_ID = int(os.environ.get("AUTHORIZED_CHAT_ID", 0))

storage = Storage()

GUIDE_TEXT = """\
Cards:
kt  = KTC
ks  = Krungsri
t   = TTB
s   = SCB
ktb = KTB
kk  = Kbank
bb  = Bangkok Bank

Food & Delivery:
g   = Grab
lm  = Line Man
ff  = Fast Food
fd  = Food

Convenience:
7   = 7-Eleven
law = Lawson
tb  = True Bill

Shopping:
sh  = Shopee
tt  = TikTok Shop
lz  = Lazada

Shoes:
nk  = Nike
nb  = New Balance

Tech:
ap  = Apple
cs  = Apple (ComSeven)

Transport:
bts = BTS
mrt = MRT
srt = SRT Red Line
rl  = Railway

Travel / Booking:
ct  = Ctrip
tlk = Traveloka
agd = Agoda

Health:
dnt = Dental
ph  = Pharmacy

Lifestyle:
op  = Origin Place
sp  = Smart Plan
mam = Thai Art Museum
bc  = Bonchon
meg = Mega Bangna
sct = Central
mk  = MK
sw  = Swensen's
cf  = Coffee
rst = Restaurant

Other:
ot  = Other
(หรือพิมพ์ชื่อตรงๆ เช่น mymall.500.ks)

Syntax:
merchant.amount.card
merchant.full_amount/months.card
merchant.amount.card.note    ← เพิ่มโน้ตได้

Examples:
g.157.ks
lm.70.kt
sh.12000/6.s
ap.36000/12.kt
bts.31.t
ot.250.ks.parking
ot.800.ks.ค่าจอดรถ

Commands:
/sum       — TAB text + .xlsx file
/week      — This week's summary (on demand)
/raw       — Today's raw shorthand entries
/today     — Today's entries + totals
/repeat N  — Clone latest N entries
/undo      — Remove last entry
/clear     — Clear all today's entries
/guide     — This guide

Auto: Weekly summary sent every Sunday 23:00\
"""


# ── Auth ───────────────────────────────────────────────────────────────────

def is_authorized(update: Update) -> bool:
    if AUTHORIZED_CHAT_ID == 0:
        return True
    return update.effective_chat.id == AUTHORIZED_CHAT_ID


def chat_id(update: Update) -> int:
    return update.effective_chat.id


def _fmt(v: float) -> str:
    if v is None:
        return ""
    return str(int(v)) if v == int(v) else f"{v:.2f}".rstrip("0")


# ── Handlers ───────────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    text = update.message.text.strip()
    if not text:
        return

    result = parse_entry(text)
    if result is None:
        logger.warning("INVALID  chat=%s  text=%r", chat_id(update), text)
        await update.message.reply_text("Invalid format. Use /guide")
        return

    storage.add(result, chat_id=chat_id(update))
    logger.info("SAVED    chat=%s  %s → %s  %s",
                chat_id(update), result["merchant"], result["card_name"], text)

    if result["type"] == "installment":
        await update.message.reply_text(
            f"✅ {result['merchant']} → {result['card_name']}\n"
            f"{_fmt(result['amount'])} / {result['months']} mo = {_fmt(result['monthly'])}/mo"
        )
    else:
        await update.message.reply_text(
            f"✅ {result['merchant']} → {result['card_name']}  {_fmt(result['amount'])}"
        )


async def handle_sum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    entries = storage.get_today(chat_id=chat_id(update))
    if not entries:
        await update.message.reply_text("No entries for today.")
        return

    logger.info("CMD /sum  chat=%s  entries=%d", chat_id(update), len(entries))

    # 1. Plain TAB-separated text for manual copy-paste
    text_output = format_sum(entries)
    await update.message.reply_text(text_output, parse_mode=None)

    # 2. xlsx file for direct Excel open
    xlsx_bytes = build_xlsx(entries)
    filename   = f"expenses_{date.today().strftime('%Y-%m-%d')}.xlsx"
    await update.message.reply_document(
        document=InputFile(io.BytesIO(xlsx_bytes), filename=filename),
        caption=f"📊 {date.today().strftime('%d %b %Y')} — {len(entries)} entries",
    )


async def handle_raw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    entries = storage.get_today(chat_id=chat_id(update))
    logger.info("CMD /raw  chat=%s  entries=%d", chat_id(update), len(entries))
    if not entries:
        await update.message.reply_text("No entries for today.")
        return
    lines = [f"{i+1}. {e['raw_text']}" for i, e in enumerate(entries)]
    await update.message.reply_text("\n".join(lines), parse_mode=None)


async def handle_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clone the latest N entries from today."""
    if not is_authorized(update):
        return

    # Parse N from command args e.g. /repeat 3
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /repeat N  (e.g. /repeat 3)")
        return

    n = int(args[0])
    if n <= 0:
        await update.message.reply_text("N must be greater than 0.")
        return

    entries = storage.get_today(chat_id=chat_id(update))
    if not entries:
        await update.message.reply_text("No entries for today.")
        return

    to_clone = entries[-n:]   # latest N (or all if fewer than N)
    for e in to_clone:
        # storage.add() reads entry["raw"]; storage rows use "raw_text" key
        clone = dict(e)
        clone["raw"] = e.get("raw_text", e.get("raw", ""))
        storage.add(clone, chat_id=chat_id(update))

    logger.info("CMD /repeat  chat=%s  n=%d  cloned=%d", chat_id(update), n, len(to_clone))
    await update.message.reply_text(
        f"🔁 Repeated latest {len(to_clone)} {'entry' if len(to_clone)==1 else 'entries'}."
    )


async def handle_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    entries = storage.get_today(chat_id=chat_id(update))
    logger.info("CMD /today  chat=%s  entries=%d", chat_id(update), len(entries))
    output  = format_today(entries)
    await update.message.reply_text(output, parse_mode=None)


async def handle_undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    deleted = storage.undo_latest(chat_id=chat_id(update))
    if deleted is None:
        await update.message.reply_text("Nothing to undo.")
    else:
        logger.info("CMD /undo  chat=%s  removed=%r", chat_id(update), deleted["raw_text"])
        await update.message.reply_text(f"↩️ Removed: {deleted['raw_text']}")


async def handle_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    storage.clear_today(chat_id=chat_id(update))
    logger.info("CMD /clear  chat=%s", chat_id(update))
    await update.message.reply_text("🗑️ Today's entries cleared.")


async def handle_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual /week command — send this week's summary on demand."""
    if not is_authorized(update):
        return

    today   = date.today()
    monday, sunday = week_bounds(today)
    entries = storage.get_week(monday, sunday, chat_id=chat_id(update))

    if not entries:
        await update.message.reply_text("No entries this week.")
        return

    logger.info("CMD /week  chat=%s  entries=%d", chat_id(update), len(entries))

    xlsx_bytes = build_weekly_xlsx(entries, today)
    label      = current_week_label(today).replace(" ", "_").replace("–", "-")
    filename   = f"weekly_{label}.xlsx"
    await update.message.reply_document(
        document=InputFile(io.BytesIO(xlsx_bytes), filename=filename),
        caption=f"📅 {current_week_label(today)} — {len(entries)} entries",
    )


async def handle_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    await update.message.reply_text(GUIDE_TEXT, parse_mode=None)


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_guide(update, context)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("sum",   handle_sum))
    app.add_handler(CommandHandler("raw",    handle_raw))
    app.add_handler(CommandHandler("repeat", handle_repeat))
    app.add_handler(CommandHandler("today", handle_today))
    app.add_handler(CommandHandler("undo",  handle_undo))
    app.add_handler(CommandHandler("clear", handle_clear))
    app.add_handler(CommandHandler("week",  handle_week))
    app.add_handler(CommandHandler("guide", handle_guide))
    app.add_handler(CommandHandler("help",  handle_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # Start weekly auto-scheduler (Sunday 23:00 BKK)
    setup_scheduler(app.bot, storage, AUTHORIZED_CHAT_ID)
    logger.info("=== Expense bot started ===")
    app.run_polling()


if __name__ == "__main__":
    main()
