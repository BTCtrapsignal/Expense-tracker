# 💳 Expense Tracker Bot

Ultra-fast Telegram bot for daily credit card expense logging via shorthand messages.
Generates clean TAB-separated, Excel-ready output grouped by card.

---

## Quick Start

### 1. Create the Telegram Bot
1. Open Telegram → search `@BotFather`
2. Send `/newbot` and follow the prompts
3. Copy the **bot token**

### 2. Get Your Chat ID
1. Send any message to your new bot
2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Copy the `chat.id` from the JSON response

### 3. Configure Environment
```bash
cp .env.example .env
# Fill in TELEGRAM_BOT_TOKEN and AUTHORIZED_CHAT_ID
```

### 4. Run Locally
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/bot.py
```

---

## Deploy on Railway

1. Push this repo to GitHub
2. [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
3. Set environment variables in the Railway dashboard:
   - `TELEGRAM_BOT_TOKEN` — your bot token
   - `AUTHORIZED_CHAT_ID` — your Telegram chat ID (strongly recommended)
4. Railway auto-detects `Procfile` and deploys

> **Persistent storage**: Add a Railway Volume and set `DB_PATH=/data/expenses.db`
> to survive redeploys.

---

## Shorthand Syntax

### Normal expense
```
merchant.amount.card
```
| Example | Meaning |
|---|---|
| `g.157.ks` | Grab ฿157 on Krungsri |
| `lm.70.kt` | Line Man ฿70 on KTC |
| `g.163.66.ks` | Grab ฿163.66 on Krungsri |

### Installment
```
merchant.full_amount/months.card
```
| Example | Meaning |
|---|---|
| `sh.12000/6.s` | Shopee ฿12,000 over 6 months on SCB |
| `sh.9999.99/10.s` | Shopee ฿9,999.99 over 10 months on SCB |

**Parser rules:**
- Card code is always the segment after the **last dot**
- Merchant is always before the **first dot**
- Everything in between is the amount (may include a decimal)

---

## Card Codes

| Code | Card |
|---|---|
| `kt` | KTC |
| `ks` | Krungsri |
| `t` | TTB |
| `s` | SCB |

## Merchant Codes

| Code | Merchant |
|---|---|
| `g` | Grab |
| `lm` | Line Man |
| `sh` | Shopee |
| `7` | 7-Eleven |
| `nk` | Nike |
| `ap` | Apple |
| `fd` | Food |
| `tr` | Travel |

> Unknown codes are auto-capitalized and used as-is.

---

## Commands

| Command | Description |
|---|---|
| `/sum` | Excel-ready TAB-separated output grouped by card |
| `/today` | Today's logged entries + totals per card |
| `/undo` | Remove the most recent entry |
| `/clear` | Clear all of today's entries |
| `/guide` | Shorthand syntax reference |
| `/help` | Alias for /guide |

---

## Output Format

### `/sum` — Excel paste output

Given input:
```
g.157.ks
lm.70.kt
sh.12000/6.s
```

Output (tabs shown as →):
```
KTC
Line Man→→70

Krungsri
Grab→→157

SCB
Shopee 1/6→12000→2000→Shopee 2/6→12000→2000→Shopee 3/6→12000→2000→Shopee 4/6→12000→2000→Shopee 5/6→12000→2000→Shopee 6/6→12000→2000
```

- **Normal rows**: 3 columns — `Merchant [TAB] [TAB] amount`
- **Installment rows**: All months on **one horizontal line** — `Name [TAB] Full [TAB] Monthly` repeated per month
- Copy each section and paste directly into your monthly Excel columns

### `/today` — Review output
```
Today 22 May 2026 — 3 entries

KTC
  1. Line Man  70

Krungsri
  1. Grab  157

SCB
  1. Shopee  12000/6mo = 2000/mo

Totals:
  KTC: 70
  Krungsri: 157
  SCB: 2000
  Grand total: 2227
```

> Installments count their **monthly amount** toward the daily total, not the full amount.

---

## Edge Cases

| Input | Result |
|---|---|
| `g.163.66.ks` | ฿163.66 normal expense |
| `sh.9999.99/10.s` | ฿9,999.99 / 10 months = ฿1,000/mo |
| `xyz.500.kt` | Accepted — merchant shown as `Xyz` |
| `g.100.xx` | Rejected — unknown card code |
| `hello` | Rejected — `Invalid format. Use /guide` |

---

## Project Structure

```
expense-tracker/
├── src/
│   ├── bot.py          — Telegram bot + all command handlers
│   ├── parser.py       — Right-anchored regex parser
│   ├── formatter.py    — TAB-separated Excel output + /today summary
│   ├── storage.py      — SQLite with full column schema
│   ├── merchants.py    — Merchant code → display name
│   └── cards.py        — Card code → display name + sort order
├── .env.example
├── .gitignore
├── Procfile
├── railway.toml
├── requirements.txt
└── README.md
```

---

## Extending

### Add a merchant
Edit `src/merchants.py`:
```python
MERCHANT_MAP["mc"] = "McDonald's"
```

### Add a card
Edit `src/cards.py`:
```python
CARD_MAP["bb"] = "Bangkok Bank"
CARD_ORDER.append("Bangkok Bank")
```
