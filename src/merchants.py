"""
Merchant code → display name mapping.
Codes are case-insensitive (always lowercased before lookup).
"""

MERCHANT_MAP: dict[str, str] = {
    # ── Food delivery ──────────────────────────────────────────────────────
    "g":    "Grab",
    "lm":   "Line Man",
    "fd":   "Food",

    # ── Convenience / retail ───────────────────────────────────────────────
    "7":    "7-Eleven",
    "law":  "Lawson",
    "ff":   "Fast Food",       # TMN*FAST FOOD
    "tb":   "True Bill",       # TMN*TRUEBILL

    # ── Shopping / e-commerce ──────────────────────────────────────────────
    "sh":   "Shopee",
    "spe":  "Shopee",          # FOR*(FOR SHOPEE) alias
    "tt":   "TikTok Shop",     # OMISE*TikTok Shop
    "lz":   "Lazada",

    # ── Shoes ──────────────────────────────────────────────────────────────
    "nk":   "Nike",
    "nb":   "New Balance",     # NB MONO MUANGTHONG THANI
    "nm":   "New Balance",     # alias

    # ── Tech / electronics ─────────────────────────────────────────────────
    "ap":   "Apple",           # Apple.com/bill, iTunes, Apple Accessory
    "cs":   "Apple",           # COMSEVEN - EVENT (Apple reseller)

    # ── Travel / transport ─────────────────────────────────────────────────
    "tr":   "Travel",
    "bts":  "BTS",             # LINEPAY*LP_BTS
    "mrt":  "MRT",             # MRT-BEM
    "srt":  "SRT Red Line",    # SRT RED LINE
    "rl":   "Railway",         # Railway.app
    "am":   "Amazon",          # AMZ_SD / Amazon

    # ── Booking / hotels ──────────────────────────────────────────────────
    "ct":   "Ctrip",           # CTRIP (THAILAND)
    "tlk":  "Traveloka",       # Traveloka3DS
    "agd":  "Agoda",

    # ── Health / medical ──────────────────────────────────────────────────
    "dnt":  "Dental",          # TOOTH MOOD DENTAL
    "ph":   "Pharmacy",

    # ── Entertainment / lifestyle ─────────────────────────────────────────
    "sp":   "Smart Plan",      # SMART PLAN ON CALL
    "op":   "Origin Place",    # ORIGIN PLACE LASALLE-R
    "mam":  "Thai Art Museum", # THAI ART MUSEUM
    "bc":   "Bonchon",         # BONCHON CHICKEN
    "meg":  "Mega Bangna",     # SCT-MEGA BANGNA
    "sct":  "Central",         # SCT-CENTRAL WEST GATE

    # ── Dining ────────────────────────────────────────────────────────────
    "rst":  "Restaurant",
    "cf":   "Coffee",
    "mk":   "MK",
    "sw":   "Swensen's",

    # ── Other (free-text, no fixed category) ──────────────────────────────
    # User types: ot.amount.card  → shows as "Other"
    # Or types custom name directly: mymall.500.ks → shows as "Mymall"
    "ot":   "Other",
}
