"""
Weekly summary helpers.

Cycle:  Monday (WK start) → Sunday 23:00 BKK (auto-send) → Monday new WK

Layout (xlsx only — no text output):
  Week header row  (dark navy, full width)
  └─ Card header   (medium navy)
     └─ Day sub-header  (light green)
        └─ Entry rows   (alternating white/grey)
     └─ Day sub-header  ...

Each entry row uses the same 3-col-per-month layout as daily xlsx.
"""

from datetime import date, timedelta
from collections import defaultdict
import io

from formatter import _fmt
from excel_export import _card_fill, HEADER_BG, HEADER_FG, INSTALL_BG, ALT_BG, NORMAL_BG, BORDER

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from cards import CARD_ORDER

# ── Colour palette ────────────────────────────────────────────────────────
CARD_BG  = "2E5090"   # medium navy  — card section header
DAY_BG   = "D9EAD3"   # light green  — day sub-header
DAY_FG   = "1C4587"   # dark blue text on day row

# ── Date helpers ──────────────────────────────────────────────────────────

def week_bounds(ref: date) -> tuple[str, str]:
    """(monday_iso, sunday_iso) for the week containing ref."""
    monday = ref - timedelta(days=ref.weekday())   # Mon=0 … Sun=6
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


def current_week_label(ref: date) -> str:
    monday = ref - timedelta(days=ref.weekday())
    sunday = monday + timedelta(days=6)
    return f"Week {monday.strftime('%d %b')} – {sunday.strftime('%d %b %Y')}"


def _day_label(iso_date: str) -> str:
    """e.g. '2026-05-18' → 'Mon 18 May'"""
    d = date.fromisoformat(iso_date)
    return d.strftime("%a %d %b")


# ── Negative amount helper (same rule as daily xlsx) ──────────────────────

def _neg(value: float) -> int | float:
    if value is None:
        return ""
    v = round(value, 2)
    v = int(v) if v == int(v) else v
    return -abs(v)


# ── xlsx builder ──────────────────────────────────────────────────────────

def build_weekly_xlsx(entries: list[dict], ref: date) -> bytes:
    """
    Layout per card:
      Card header (navy)
        Day sub-header (green) — Mon 18 May
          entry rows ...
        Day sub-header (green) — Tue 19 May
          entry rows ...
      [blank gap]
    Next card ...
    """
    wb = Workbook()
    ws = wb.active
    ws.title = current_week_label(ref)[:31]

    # Column widths
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 26
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 12
    for col_idx in range(5, 5 + 24 * 3):
        ws.column_dimensions[get_column_letter(col_idx)].width = 12

    # ── Week header ──────────────────────────────────────────────────────
    row = 1
    wk = ws.cell(row=row, column=2, value=current_week_label(ref))
    wk.font      = Font(bold=True, color=HEADER_FG, name="Arial", size=12)
    wk.fill      = _card_fill(HEADER_BG)
    wk.alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=10)
    ws.row_dimensions[row].height = 26
    row += 1

    # ── Group: card → day → [entries] ────────────────────────────────────
    # card_day_map[card][day_iso] = [entry, ...]
    card_day_map: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for e in entries:
        card_day_map[e["card_name"]][e["day"]].append(e)

    ordered_cards = [c for c in CARD_ORDER if c in card_day_map]
    for c in card_day_map:
        if c not in ordered_cards:
            ordered_cards.append(c)

    for card in ordered_cards:
        day_map = card_day_map[card]

        # Card header
        ch = ws.cell(row=row, column=2, value=card)
        ch.font      = Font(bold=True, color=HEADER_FG, name="Arial", size=11)
        ch.fill      = _card_fill(CARD_BG)
        ch.alignment = Alignment(vertical="center", indent=1)
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=10)
        ws.row_dimensions[row].height = 20
        row += 1

        # Days in ascending order within the card
        for day_iso in sorted(day_map.keys()):
            day_entries = day_map[day_iso]

            # Day sub-header
            dh = ws.cell(row=row, column=2, value=_day_label(day_iso))
            dh.font      = Font(bold=True, color=DAY_FG, name="Arial", size=10)
            dh.fill      = PatternFill("solid", start_color=DAY_BG, fgColor=DAY_BG)
            dh.alignment = Alignment(vertical="center", indent=2)
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=10)
            ws.row_dimensions[row].height = 16
            row += 1

            # Entry rows for this day
            for i, e in enumerate(day_entries):
                bg = ALT_BG if i % 2 == 0 else NORMAL_BG

                if not e["is_installment"]:
                    b = ws.cell(row=row, column=2, value=e["merchant_name"])
                    c = ws.cell(row=row, column=3, value="")
                    d = ws.cell(row=row, column=4, value=_neg(e["amount"]))
                    for cell in (b, c, d):
                        cell.fill      = _card_fill(bg)
                        cell.font      = Font(name="Arial", size=10)
                        cell.border    = BORDER
                        cell.alignment = Alignment(vertical="center")
                    b.alignment = Alignment(vertical="center", indent=1)
                    d.alignment = Alignment(horizontal="right", vertical="center")
                    d.number_format = '#,##0.##'
                    row += 1
                else:
                    months  = e["months"]
                    full    = _neg(e["full_amount"])
                    monthly = _neg(e["monthly_amount"])
                    name    = e["merchant_name"]
                    col = 2
                    for mo in range(1, months + 1):
                        b = ws.cell(row=row, column=col,     value=f"{name} {mo}/{months}")
                        c = ws.cell(row=row, column=col + 1, value=full)
                        d = ws.cell(row=row, column=col + 2, value=monthly)
                        for cell in (b, c, d):
                            cell.fill   = _card_fill(INSTALL_BG)
                            cell.font   = Font(name="Arial", size=10)
                            cell.border = BORDER
                            cell.alignment = Alignment(vertical="center")
                        b.alignment = Alignment(vertical="center", indent=1)
                        c.alignment = Alignment(horizontal="right", vertical="center")
                        d.alignment = Alignment(horizontal="right", vertical="center")
                        c.number_format = '#,##0.##'
                        d.number_format = '#,##0.##'
                        col += 3
                    ws.row_dimensions[row].height = 18
                    row += 1

        row += 1   # blank gap between cards

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
