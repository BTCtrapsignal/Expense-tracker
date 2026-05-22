"""
Parser — right-anchored parsing so decimals in amounts never confuse card code.

Formats supported:
  g.157.ks                    normal
  g.163.66.ks                 decimal amount
  sh.12000/6.s                installment
  sh.9999.99/10.s             installment with decimal
  ot.500.ks.parking           note after card code (any merchant, not just ot)
  ot.500.ks.ค่าจอดรถ          note supports Thai text

Parse order:
  1. Check if last segment (after final dot) is a KNOWN card code
       → if yes: card = last segment, note = None
  2. If not a card, check second-to-last segment
       → if yes: card = second-to-last, note = last segment
  3. Otherwise invalid
  4. From remaining body: merchant = first segment, amount = middle
"""

import re
from merchants import MERCHANT_MAP
from cards import CARD_MAP

CARD_RE   = re.compile(r"^[a-zA-Z]+$")
MERCH_RE  = re.compile(r"^[a-zA-Z0-9]+$")
AMOUNT_RE = re.compile(r"^\d+(\.\d+)?$")
INSTALL_RE = re.compile(r"^(?P<amount>\d+(?:\.\d+)?)/(?P<months>\d+)$")


def _try_parse_body(merchant_code: str, amount_str: str, card_code: str,
                    card_name: str, note: str | None, raw: str) -> dict | None:
    """Given already-split parts, build the entry dict or return None."""
    if not MERCH_RE.match(merchant_code):
        return None

    merchant = MERCHANT_MAP.get(merchant_code, merchant_code.capitalize())

    # Apply note to merchant display name
    display = f"{merchant} ({note})" if note else merchant

    # Installment?
    m = INSTALL_RE.match(amount_str)
    if m:
        amount = float(m.group("amount"))
        months = int(m.group("months"))
        if months <= 0:
            return None
        monthly = round(amount / months, 2)
        return {
            "type":          "installment",
            "raw":           raw,
            "merchant_code": merchant_code,
            "merchant":      display,
            "card_code":     card_code,
            "card_name":     card_name,
            "amount":        amount,
            "months":        months,
            "monthly":       monthly,
            "note":          note,
        }

    # Normal — amount_str must be plain number
    if not AMOUNT_RE.match(amount_str):
        return None

    amount = float(amount_str)
    return {
        "type":          "normal",
        "raw":           raw,
        "merchant_code": merchant_code,
        "merchant":      display,
        "card_code":     card_code,
        "card_name":     card_name,
        "amount":        amount,
        "months":        None,
        "monthly":       None,
        "note":          note,
    }


def parse_entry(text: str) -> dict | None:
    text = text.strip().lower()   # normalize — supports G.157.KS, SH.12000/6.S etc.
    if not text:
        return None

    parts = text.split(".")

    # Need at least: merchant . amount . card  → 3 parts minimum
    if len(parts) < 3:
        return None

    # ── Strategy A: last part is card code (no note) ───────────────────────
    # e.g.  g . 157 . ks
    #        g . 163 . 66 . ks   (decimal amount has extra dot → parts=4)
    last = parts[-1].lower()
    if CARD_RE.match(last) and CARD_MAP.get(last):
        card_code = last
        card_name = CARD_MAP[card_code]
        # body = everything before last part, re-joined with dots
        body = ".".join(parts[:-1])
        first_dot = body.find(".")
        if first_dot == -1:
            return None
        merchant_code = body[:first_dot].lower()
        amount_str    = body[first_dot + 1:]
        return _try_parse_body(merchant_code, amount_str, card_code, card_name, None, text)

    # ── Strategy B: second-to-last is card code, last is note ─────────────
    # e.g.  ot . 500 . ks . parking
    #        ot . 500 . ks . ค่าจอดรถ
    if len(parts) >= 4:
        second_last = parts[-2].lower()
        if CARD_RE.match(second_last) and CARD_MAP.get(second_last):
            card_code = second_last
            card_name = CARD_MAP[card_code]
            note      = parts[-1]          # raw note, preserve original case
            body      = ".".join(parts[:-2])
            first_dot = body.find(".")
            if first_dot == -1:
                return None
            merchant_code = body[:first_dot].lower()
            amount_str    = body[first_dot + 1:]
            return _try_parse_body(merchant_code, amount_str, card_code, card_name, note, text)

    return None
