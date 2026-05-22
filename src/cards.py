"""
Card code → display name mapping.
"""

CARD_MAP: dict[str, str] = {
    "kt":  "KTC",
    "ks":  "Krungsri",
    "t":   "TTB",
    "s":   "SCB",
    "bb":  "Bangkok Bank",
    "bay": "Krungsri",     # Bank of Ayudhya alias
    "kk":  "Kbank",
    "scb": "SCB",
    "ttb": "TTB",
    "ktb": "KTB",
}

# Display order in /sum and /today output
CARD_ORDER = ["KTC", "Krungsri", "TTB", "SCB", "KTB", "Kbank", "Bangkok Bank"]
