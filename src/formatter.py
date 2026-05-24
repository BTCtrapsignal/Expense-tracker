"""
Formatter — clean TAB-separated Excel output. No markdown. No bullets.

Normal row  (3 cols):   Merchant [TAB] [TAB] amount
Installment row:        Merchant 1/N [TAB] full [TAB] monthly [TAB] Merchant 2/N [TAB] ...
All months on ONE single line — horizontal paste across Excel columns.

ONLY real \t characters — never spaces for alignment.

Merging rule (normal entries only):
  Same merchant name + same card → merged into ONE row, amounts summed.
  Installments are NEVER merged (each has distinct full/monthly amounts).
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


def _merge_normals(entries: list[dict]) -> list[dict]:
    """
    Merge normal entries with the same merchant name within a card.
    Installments pass through unchanged.
    Preserves card-level ordering: first occurrence of a merchant name
    determines its position; subsequent same-name entries are folded in.
    """
    seen: dict[str, dict] = {}   # merchant_name → merged entry
    order: list[str | int] = []  # track output order: str=merchant key, int=installment id

    for e in entries:
        if e["is_installment"]:
            order.append(id(e))
            seen[id(e)] = e
        else:
            key = e["merchant"]
            if key in seen:
                # Accumulate amount into existing merged entry
                seen[key] = dict(seen[key])
                seen[key]["amount"] = seen[key]["amount"] + e["amount"]
            else:
                seen[key] = dict(e)
                order.append(key)

    return [seen[k] for k in order]


def format_sum(entries: list[dict]) -> str:
    """Return clean card-grouped TAB-separated output ready for Excel paste."""
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
        merged = _merge_normals(groups[card])
        lines  = [card]
        for e in merged:
            if not e["is_installment"]:
                row = e["merchant"] + TAB + TAB + _fmt(e["amount"])
                lines.append(row)
            else:
                merchant = e["merchant"]
                full     = _fmt(e["full_amount"])
                monthly  = _fmt(e["monthly_amount"])
                n        = e["months"]
                month_groups = [
                    f"{merchant} {mo}/{n}" + TAB + full + TAB + monthly
                    for mo in range(1, n + 1)
                ]
                lines.append(TAB.join(month_groups))
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def format_today(entries: list[dict]) -> str:
    """Human-readable /today summary with totals per card.
    Normal entries with the same merchant are merged and shown with count.
    """
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
        # Count raw entries before merging for display
        raw_counts: dict[str, int] = {}
        for e in groups[card]:
            if not e["is_installment"]:
                raw_counts[e["merchant"]] = raw_counts.get(e["merchant"], 0) + 1

        merged = _merge_normals(groups[card])
        lines.append(card)
        card_total = 0.0
        for i, e in enumerate(merged, 1):
            if not e["is_installment"]:
                amt   = e["amount"]
                count = raw_counts.get(e["merchant"], 1)
                count_str = f" ×{count}" if count > 1 else ""
                lines.append(f"  {i}. {e['merchant']}{count_str}  {_fmt(amt)}")
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
