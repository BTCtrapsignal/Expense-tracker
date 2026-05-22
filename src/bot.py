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

logging.basicConfig(level=logging.INFO)
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
/sum    — ส่ง .xlsx file (เปิดใน Excel ได้เลย)
/today  — Today's entries + totals
/undo   — Remove last entry
/clear  — Clear all today's entries
/guide  — This guide\
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
        await update.message.reply_text("Invalid format. Use /guide")
        return

    storage.add(result, chat_id=chat_id(update))

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

    xlsx_bytes = build_xlsx(entries)
    filename   = f"expenses_{date.today().strftime('%Y-%m-%d')}.xlsx"

    await update.message.reply_document(
        document=InputFile(io.BytesIO(xlsx_bytes), filename=filename),
        caption=f"📊 {date.today().strftime('%d %b %Y')} — {len(entries)} entries",
    )


async def handle_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    entries = storage.get_today(chat_id=chat_id(update))
    output  = format_today(entries)
    await update.message.reply_text(output, parse_mode=None)


async def handle_undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    deleted = storage.undo_latest(chat_id=chat_id(update))
    if deleted is None:
        await update.message.reply_text("Nothing to undo.")
    else:
        await update.message.reply_text(f"↩️ Removed: {deleted['raw_text']}")


async def handle_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    storage.clear_today(chat_id=chat_id(update))
    await update.message.reply_text("🗑️ Today's entries cleared.")


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
    app.add_handler(CommandHandler("today", handle_today))
    app.add_handler(CommandHandler("undo",  handle_undo))
    app.add_handler(CommandHandler("clear", handle_clear))
    app.add_handler(CommandHandler("guide", handle_guide))
    app.add_handler(CommandHandler("help",  handle_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Expense bot started.")
    app.run_polling()


if __name__ == "__main__":
    main()
