"""
Formatter — clean TAB-separated Excel output. No markdown. No bullets.

Normal row  (3 cols):   Merchant [TAB] [TAB] amount
Installment row:        Merchant 1/N [TAB] full [TAB] monthly [TAB] Merchant 2/N [TAB] ...
All months on ONE single line — horizontal paste across Excel columns.

ONLY real \t characters — never spaces for alignment.
"""

from cards import CARD_ORDER

TAB = "\t"   # explicit constant — guaranteed real tab, never a space


def _fmt(value: float) -> str:
    """Drop trailing zeros; whole numbers as integers."""
    if value is None:
        return ""
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}".rstrip("0")


def format_sum(entries: list[dict]) -> str:
    """Return clean card-grouped TAB-separated output ready for Excel paste.

    Normal row:      merchant \\t \\t amount
    Installment row: merchant 1/N \\t full \\t monthly \\t merchant 2/N \\t ... (ONE line)
    """
    if not entries:
        return "No entries for today."

    groups: dict[str, list[dict]] = {}
    for e in entries:
        groups.setdefault(e["card_name"], []).append(e)

    ordered = [c for c in CARD_ORDER if c in groups]
    for c in groups:
        if c not in ordered:
            ordered.append(c)

    sections: list[str] = []

    for card in ordered:
        lines = [card]
        for e in groups[card]:
            if not e["is_installment"]:
                # col1=merchant  col2=(blank)  col3=amount
                row = e["merchant"] + TAB + TAB + _fmt(e["amount"])
                lines.append(row)
            else:
                # All months on ONE line — 3 cols per month joined by TAB
                merchant = e["merchant"]
                full     = _fmt(e["full_amount"])
                monthly  = _fmt(e["monthly_amount"])
                n        = e["months"]
                month_groups = []
                for mo in range(1, n + 1):
                    month_groups.append(
                        f"{merchant} {mo}/{n}" + TAB + full + TAB + monthly
                    )
                row = TAB.join(month_groups)
                lines.append(row)
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def format_today(entries: list[dict]) -> str:
    """Human-readable /today summary with totals per card."""
    if not entries:
        return "No entries today."

    from datetime import date
    header = f"Today {date.today().strftime('%d %b %Y')} — {len(entries)} entries"
    lines  = [header, ""]

    groups: dict[str, list[dict]] = {}
    for e in entries:
        groups.setdefault(e["card_name"], []).append(e)

    ordered = [c for c in CARD_ORDER if c in groups]
    for c in groups:
        if c not in ordered:
            ordered.append(c)

    card_totals: dict[str, float] = {}
    grand_total = 0.0

    for card in ordered:
        lines.append(card)
        card_total = 0.0
        for i, e in enumerate(groups[card], 1):
            if not e["is_installment"]:
                amt = e["amount"]
                lines.append(f"  {i}. {e['merchant']}  {_fmt(amt)}")
            else:
                amt = e["monthly_amount"]
                lines.append(
                    f"  {i}. {e['merchant']}  {_fmt(e['full_amount'])}/{e['months']}mo"
                    f"  = {_fmt(amt)}/mo"
                )
            card_total += amt
        card_totals[card] = card_total
        grand_total += card_total
        lines.append("")

    lines.append("Totals:")
    for card in ordered:
        lines.append(f"  {card}: {_fmt(card_totals[card])}")
    lines.append(f"  Grand total: {_fmt(grand_total)}")

    return "\n".join(lines)
