"""
Formatter — clean TAB-separated Excel output. No markdown. No bullets.

Normal row  (3 cols):   Merchant [TAB] [TAB] amount
Installment row:        Merchant 1/N [TAB] full [TAB] monthly [TAB] Merchant 2/N [TAB] ...
All months on ONE line — horizontal paste across Excel columns.
"""

from cards import CARD_ORDER


def _fmt(value: float) -> str:
    """Drop trailing zeros after decimal; keep whole numbers as integers."""
    if value is None:
        return ""
    if value == int(value):
        return str(int(value))
    # up to 2 decimal places, strip trailing zeros
    return f"{value:.2f}".rstrip("0")


def format_sum(entries: list[dict]) -> str:
    """Return clean card-grouped output ready for Excel paste."""
    if not entries:
        return "No entries for today."

    # Group by card, preserving insertion order within each card
    groups: dict[str, list[dict]] = {}
    for e in entries:
        groups.setdefault(e["card_name"], []).append(e)

    # Canonical order; unknown cards appended at end
    ordered = [c for c in CARD_ORDER if c in groups]
    for c in groups:
        if c not in ordered:
            ordered.append(c)

    sections: list[str] = []

    for card in ordered:
        lines = [card]
        for e in groups[card]:
            if not e["is_installment"]:
                # Normal: Merchant [TAB] [TAB] amount
                lines.append(f"{e['merchant']}\t\t{_fmt(e['amount'])}")
            else:
                # Installment: all months horizontal on one line
                merchant = e["merchant"]
                full     = _fmt(e["full_amount"])
                monthly  = _fmt(e["monthly_amount"])
                n        = e["months"]
                segments = [f"{merchant} {mo}/{n}\t{full}\t{monthly}" for mo in range(1, n + 1)]
                lines.append("\t".join(segments))
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def format_today(entries: list[dict]) -> str:
    """Human-readable /today summary with totals per card."""
    if not entries:
        return "No entries today."

    from datetime import date
    header = f"Today {date.today().strftime('%d %b %Y')} — {len(entries)} entries"
    lines  = [header, ""]

    # List entries grouped by card
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
                amt = e["monthly_amount"]   # count only monthly toward daily total
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
