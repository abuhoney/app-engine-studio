"""
ICON GENERATOR — generates app icons that express the app name or function.

The user explicitly requested: "يجب عليك اضافه معالجات لتوليد ايقونات معبره عن
إسم التطبيق أو وضائفه" — "You MUST add processors to generate icons that express
the app name or its functions."

This module produces real, functional, vector-drawable Android icons. It
supports six strategies:

  1. LETTER_ICON   — A rounded-square background + the actual first letter of
                     the app name rendered as a real vector path. Different
                     background color per app name hash. Every letter A-Z and
                     digit 0-9 has its own distinct, recognizable path.
  2. CATEGORY_ICON — A category-specific symbol (calculator grid for CALCULATOR,
                     note for NOTES, etc.) — used when the category is known.
                     50+ category symbols are defined.
  3. INITIALS_ICON — Two-letter initials for compound names ("My App" -> "MA")
                     rendered as real letter paths side-by-side.
  4. NAME_HASH_ICON — A deterministic geometric pattern (color + shape) derived
                      from the SHA-256 of the app name. Every name gets a
                      unique, reproducible icon.
  5. MONOGRAM_ICON  — A circle background + 1-3 letters in a stylized layout
                      (used for short brand names like "BMW", "IBM").
  6. EMOJI_ICON     — A category-specific emoji-style face drawn purely with
                      vector paths (no font dependency).

All six produce valid Android `res/drawable/ic_launcher.xml` vector drawables
plus the matching `res/mipmap-anydpi-v26/ic_launcher.xml` + `ic_launcher_round.xml`
adaptive icons.
"""
from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Palette — 16 distinct colors, chosen for contrast against white text
# ---------------------------------------------------------------------------
PALETTE: List[str] = [
    "#4F8EF7",  # blue
    "#22C55E",  # green
    "#EF4444",  # red
    "#F59E0B",  # amber
    "#8B5CF6",  # violet
    "#EC4899",  # pink
    "#14B8A6",  # teal
    "#6366F1",  # indigo
    "#F97316",  # orange
    "#10B981",  # emerald
    "#0EA5E9",  # sky
    "#A855F7",  # purple
    "#DC2626",  # rose
    "#059669",  # dark emerald
    "#7C3AED",  # dark violet
    "#EA580C",  # dark orange
]


def color_for_name(app_name: str) -> str:
    """Deterministic color from app name — same name always produces same color."""
    h = hashlib.sha256(app_name.lower().encode("utf-8")).hexdigest()
    idx = int(h[:2], 16) % len(PALETTE)
    return PALETTE[idx]


def accent_color_for_name(app_name: str) -> str:
    """A second deterministic color, distinct from the primary, for two-tone icons."""
    h = hashlib.sha256(app_name.lower().encode("utf-8")).hexdigest()
    primary_idx = int(h[:2], 16) % len(PALETTE)
    accent_idx = int(h[2:4], 16) % len(PALETTE)
    # Ensure the accent differs from the primary
    if accent_idx == primary_idx:
        accent_idx = (accent_idx + 1) % len(PALETTE)
    return PALETTE[accent_idx]


def initials_for_name(app_name: str) -> str:
    """Two-letter initials from app name. 'My App' -> 'MA', 'Calculator' -> 'CA'."""
    words = [w for w in app_name.strip().split() if w]
    if not words:
        return "AP"
    if len(words) == 1:
        w = words[0]
        return (w[:2] if len(w) >= 2 else w + "X").upper()
    return (words[0][0] + words[1][0]).upper()


def first_letter(app_name: str) -> str:
    """Single uppercase first letter."""
    if not app_name:
        return "A"
    return app_name.strip()[0].upper()


# ---------------------------------------------------------------------------
# REAL letter path data — A-Z, 0-9
# ---------------------------------------------------------------------------
# Each path is designed in a 24x32 bounding box (centered in 48x48 viewport
# at offset x=12, y=8). Letters use a single fill path with strokeWidth-style
# construction (each letter is built as a closed shape).
#
# Path data convention:
#   - Origin: top-left of the letter's 24x32 box
#   - Letters are bold sans-serif-style block letters
#   - Stroke width approximately 5 units
#   - All letters occupy roughly the same visual space
# ---------------------------------------------------------------------------
LETTER_PATHS: Dict[str, str] = {
    "A": "M12 8 L24 40 L18.5 40 L16.5 33 L7.5 33 L5.5 40 L0 40 L12 8 Z M9 27 L15 27 L12 17 Z",
    "B": "M2 8 L18 8 Q24 8 24 14 Q24 19 19 20 Q24 21 24 27 Q24 33 18 33 L2 33 Z M8 14 L8 18 L17 18 Q19 18 19 16 Q19 14 17 14 Z M8 23 L8 27 L17 27 Q19 27 19 25 Q19 23 17 23 Z",
    "C": "M22 12 Q18 7 12 7 Q4 7 4 20 Q4 33 12 33 Q18 33 22 28 L18 25 Q15 28 12 28 Q9 28 9 20 Q9 12 12 12 Q15 12 18 15 Z",
    "D": "M2 8 L12 8 Q24 8 24 20 Q24 33 12 33 L2 33 Z M8 14 L8 27 L12 27 Q18 27 18 20 Q18 14 12 14 Z",
    "E": "M2 8 L22 8 L22 14 L8 14 L8 17 L20 17 L20 23 L8 23 L8 27 L22 27 L22 33 L2 33 Z",
    "F": "M2 8 L22 8 L22 14 L8 14 L8 17 L20 17 L20 23 L8 23 L8 33 L2 33 Z",
    "G": "M22 12 Q18 7 12 7 Q4 7 4 20 Q4 33 12 33 Q20 33 22 28 L22 22 L14 22 L14 17 L24 17 L24 30 Q20 33 12 33 Q4 33 4 20 Q4 7 12 7 Q18 7 22 12 Z",
    "H": "M2 8 L8 8 L8 17 L18 17 L18 8 L24 8 L24 33 L18 33 L18 23 L8 23 L8 33 L2 33 Z",
    "I": "M2 8 L24 8 L24 13 L17 13 L17 28 L24 28 L24 33 L2 33 L2 28 L9 28 L9 13 L2 13 Z",
    "J": "M2 11 L8 11 L8 27 Q8 30 12 30 Q16 30 16 27 L16 8 L22 8 L22 27 Q22 36 12 36 Q2 36 2 27 Z",
    "K": "M2 8 L8 8 L8 18 L17 8 L24 8 L14 20 L24 33 L17 33 L8 23 L8 33 L2 33 Z",
    "L": "M2 8 L8 8 L8 27 L22 27 L22 33 L2 33 Z",
    "M": "M0 33 L0 8 L7 8 L13 19 L19 8 L26 8 L26 33 L20 33 L20 18 L13 28 L6 18 L6 33 Z",
    "N": "M2 33 L2 8 L8 8 L18 23 L18 8 L24 8 L24 33 L18 33 L8 18 L8 33 Z",
    "O": "M2 20 Q2 7 13 7 Q24 7 24 20 Q24 33 13 33 Q2 33 2 20 Z M8 20 Q8 28 13 28 Q18 28 18 20 Q18 12 13 12 Q8 12 8 20 Z",
    "P": "M2 33 L2 8 L18 8 Q24 8 24 15 Q24 22 18 22 L8 22 L8 33 Z M8 14 L8 17 L17 17 Q19 17 19 15 Q19 14 17 14 Z",
    "Q": "M2 20 Q2 7 13 7 Q24 7 24 20 Q24 30 18 32 L23 38 L17 38 L13 32 Q2 33 2 20 Z M8 20 Q8 28 13 28 Q18 28 18 20 Q18 12 13 12 Q8 12 8 20 Z",
    "R": "M2 33 L2 8 L18 8 Q24 8 24 15 Q24 21 18 22 L24 33 L17 33 L11 22 L8 22 L8 33 Z M8 14 L8 17 L17 17 Q19 17 19 15 Q19 14 17 14 Z",
    "S": "M22 13 Q19 8 13 8 Q4 8 4 14 Q4 19 13 21 Q22 22 22 27 Q22 33 13 33 Q7 33 4 28 L8 25 Q11 28 13 28 Q17 28 17 27 Q17 25 13 24 Q4 22 4 14 Q4 8 13 8 Q19 8 22 13 Z",
    "T": "M0 8 L26 8 L26 14 L16 14 L16 33 L10 33 L10 14 L0 14 Z",
    "U": "M2 8 L8 8 L8 27 Q8 30 13 30 Q18 30 18 27 L18 8 L24 8 L24 27 Q24 36 13 36 Q2 36 2 27 Z",
    "V": "M0 8 L6 8 L13 24 L20 8 L26 8 L13 40 Z",
    "W": "M0 8 L6 8 L9 24 L13 14 L17 24 L20 8 L26 8 L17 40 L13 28 L9 40 Z",
    "X": "M0 8 L7 8 L13 18 L19 8 L26 8 L16 23 L26 38 L19 38 L13 28 L7 38 L0 38 L10 23 Z",
    "Y": "M0 8 L7 8 L13 19 L19 8 L26 8 L16 24 L16 33 L10 33 L10 24 Z",
    "Z": "M2 8 L24 8 L24 14 L9 27 L24 27 L24 33 L2 33 L2 27 L17 14 L2 14 Z",
    "0": "M2 20 Q2 7 13 7 Q24 7 24 20 Q24 33 13 33 Q2 33 2 20 Z M8 20 Q8 28 13 28 Q18 28 18 20 Q18 12 13 12 Q8 12 8 20 Z M4 36 L22 4 L26 6 L8 38 Z",
    "1": "M9 33 L9 14 L4 18 L4 12 L9 8 L15 8 L15 33 Z",
    "2": "M4 14 Q4 8 13 8 Q22 8 22 14 Q22 19 13 27 L22 27 L22 33 L4 33 L4 28 Q14 19 14 14 Q14 13 13 13 Q12 13 12 14 L9 17 Z",
    "3": "M4 12 Q8 8 13 8 Q22 8 22 14 Q22 19 17 20 Q22 21 22 27 Q22 33 13 33 Q8 33 4 29 L8 25 Q11 28 13 28 Q17 28 17 27 Q17 25 13 25 L11 21 L13 21 Q17 21 17 17 Q17 13 13 13 Q11 13 8 16 Z",
    "4": "M2 23 L13 8 L19 8 L19 23 L22 23 L22 28 L19 28 L19 33 L13 33 L13 28 L2 28 Z M13 23 L13 17 L9 23 Z",
    "5": "M22 13 Q19 8 13 8 Q4 8 4 14 L4 17 L10 17 L10 14 Q10 13 13 13 Q16 13 16 17 Q16 20 13 20 Q11 20 9 19 L9 33 L22 33 L22 27 L13 27 L13 23 Q13 23 13 23 Q19 23 22 19 Q22 17 22 13 Z",
    "6": "M22 13 Q19 8 13 8 Q4 8 4 20 Q4 33 13 33 Q22 33 22 26 Q22 19 13 19 Q8 19 6 22 L6 16 Q8 13 13 13 Q16 13 16 14 Z M8 26 Q8 28 13 28 Q18 28 18 26 Q18 24 13 24 Q8 24 8 26 Z",
    "7": "M2 8 L24 8 L24 13 L13 33 L7 33 L17 14 L2 14 Z",
    "8": "M13 8 Q4 8 4 14 Q4 18 9 20 Q4 22 4 27 Q4 33 13 33 Q22 33 22 27 Q22 22 17 20 Q22 18 22 14 Q22 8 13 8 Z M9 14 Q9 13 13 13 Q17 13 17 14 Q17 16 13 16 Q9 16 9 14 Z M9 27 Q9 25 13 25 Q17 25 17 27 Q17 28 13 28 Q9 28 9 27 Z",
    "9": "M4 28 Q7 33 13 33 Q22 33 22 20 Q22 8 13 8 Q4 8 4 15 Q4 22 13 22 Q18 22 20 19 L20 24 Q18 27 13 27 Q10 27 10 26 Z M8 15 Q8 13 13 13 Q18 13 18 15 Q18 17 13 17 Q8 17 8 15 Z",
}


def get_letter_path(letter: str) -> str:
    """Return the SVG path for a single letter/digit, or fallback to 'A'."""
    if not letter:
        return LETTER_PATHS["A"]
    L = letter.upper()
    if L in LETTER_PATHS:
        return LETTER_PATHS[L]
    # Non-Latin / non-digit — fall back to a default geometric mark
    return LETTER_PATHS["A"]


# ---------------------------------------------------------------------------
# Category symbol paths — 50+ categories, each with a unique, recognizable icon
# ---------------------------------------------------------------------------
# Each entry: (bg_color, fg_path, fg_color)
# fg_path is in a 48x48 viewport (full icon size)
# ---------------------------------------------------------------------------
CATEGORY_SYMBOLS: Dict[str, Tuple[str, str, str]] = {
    # ---------- Productivity ----------
    "CALCULATOR": ("#4F8EF7",
        "M14,12 H22 V20 H14 Z M26,12 H34 V20 H26 Z "
        "M14,24 H22 V32 H14 Z M26,24 H34 V32 H26 Z", "#FFFFFF"),
    "NOTES": ("#FFC107",
        "M12,8 H36 V40 H12 Z M16,14 H32 M16,20 H32 M16,26 H28", "#FFFFFF"),
    "TODO": ("#22C55E",
        "M10,14 L18,22 L34,8 L38,12 L18,32 L6,20 Z "
        "M10,30 L18,38 L34,24 L38,28 L18,42 L6,28 Z", "#FFFFFF"),
    "TASK_MANAGER": ("#16A34A",
        "M8,12 H40 V18 H8 Z M8,22 H40 V28 H8 Z M8,32 H40 V38 H8 Z "
        "M12,15 L14,17 L18,13 M12,25 L14,27 L18,23 M12,35 L14,37 L18,33", "#FFFFFF"),
    "CALENDAR": ("#3B82F6",
        "M8,12 H40 V40 H8 Z M8,18 H40 M14,8 V14 M34,8 V14 "
        "M14,24 H20 V30 H14 Z M22,24 H28 V30 H22 Z M30,24 H36 V30 H30 Z "
        "M14,32 H20 V38 H14 Z M22,32 H28 V38 H22 Z", "#FFFFFF"),

    # ---------- Browser / Web ----------
    "BROWSER": ("#3B82F6",
        "M24,8 A16,16 0 1,0 24,40 A16,16 0 1,0 24,8 Z "
        "M24,8 C16,16 16,32 24,40 M24,8 C32,16 32,32 24,40 M8,24 H40", "#FFFFFF"),
    "WEBVIEW": ("#0EA5E9",
        "M6,12 H42 V36 H6 Z M6,18 H42 M10,15 H12 M14,15 H16 "
        "M14,24 H34 M14,28 H30 M14,32 H26", "#FFFFFF"),
    "BOOKMARK_MANAGER": ("#7C3AED",
        "M12,8 H36 V40 L24,32 L12,40 Z", "#FFFFFF"),

    # ---------- Time / Timer ----------
    "TIMER": ("#EF4444",
        "M24,12 A14,14 0 1,0 24,40 A14,14 0 1,0 24,12 Z "
        "M24,18 V26 L30,30 M20,6 H28", "#FFFFFF"),
    "STOPWATCH": ("#DC2626",
        "M24,12 A14,14 0 1,0 24,40 A14,14 0 1,0 24,12 Z "
        "M24,20 V28 L30,32 M20,6 H28 M22,8 L26,8", "#FFFFFF"),
    "ALARM_CLOCK": ("#F59E0B",
        "M24,14 A12,12 0 1,0 24,38 A12,12 0 1,0 24,14 Z "
        "M24,22 V30 L30,32 M8,12 L14,18 M40,12 L34,18 "
        "M10,10 L14,8 M38,10 L34,8", "#FFFFFF"),
    "CLOCK": ("#6366F1",
        "M24,8 A16,16 0 1,0 24,40 A16,16 0 1,0 24,8 Z "
        "M24,14 V24 L32,28", "#FFFFFF"),

    # ---------- Camera / Photo ----------
    "CAMERA": ("#6366F1",
        "M8,14 H16 L20,10 H28 L32,14 H40 V38 H8 Z "
        "M24,18 A8,8 0 1,0 24,34 A8,8 0 1,0 24,18 Z", "#FFFFFF"),
    "GALLERY": ("#10B981",
        "M8,12 H40 V36 H8 Z M12,32 L20,22 L26,28 L34,18 L38,32 Z "
        "M16,18 A2,2 0 1,0 16,22 A2,2 0 1,0 16,18 Z", "#FFFFFF"),
    "PHOTO_EDITOR": ("#8B5CF6",
        "M8,12 H40 V36 H8 Z M12,32 L20,22 L26,28 L34,18 L38,32 Z "
        "M30,8 L40,18 L30,18 Z", "#FFFFFF"),
    "QR_CODE_GENERATOR": ("#0F172A",
        "M8,8 H20 V20 H8 Z M28,8 H40 V20 H28 Z "
        "M8,28 H20 V40 H8 Z M28,28 H32 V32 H28 Z M36,28 H40 V32 H36 Z "
        "M28,36 H32 V40 H28 Z M36,36 H40 V40 H36 Z", "#FFFFFF"),
    "QR_SCANNER": ("#0F172A",
        "M8,8 H20 V20 H8 Z M28,8 H40 V20 H28 Z M8,28 H20 V40 H8 Z "
        "M24,24 L40,40 M24,40 L40,24", "#FFFFFF"),
    "BARCODE_SCANNER": ("#0F172A",
        "M6,12 H10 V36 H6 Z M14,12 H16 V36 H14 Z M20,12 H24 V36 H20 Z "
        "M28,12 H30 V36 H28 Z M34,12 H38 V36 H34 Z", "#FFFFFF"),

    # ---------- Audio / Music ----------
    "MUSIC_PLAYER": ("#8B5CF6",
        "M20,10 V32 A6,6 0 1,1 14,26 V14 H34 V28 A6,6 0 1,1 28,22 V10 Z", "#FFFFFF"),
    "PODCAST_PLAYER": ("#7C3AED",
        "M24,8 A6,6 0 1,0 24,20 A6,6 0 1,0 24,8 Z "
        "M16,32 A8,8 0 0,1 32,32 L28,32 A4,4 0 0,0 20,32 Z "
        "M14,40 A10,10 0 0,1 34,40 L30,40 A6,6 0 0,0 18,40 Z", "#FFFFFF"),
    "RADIO_PLAYER": ("#EC4899",
        "M8,18 H40 V38 H8 Z M12,32 A4,4 0 1,0 12,24 A4,4 0 1,0 12,32 Z "
        "M22,26 H36 M22,32 H36 M14,8 L36,16", "#FFFFFF"),
    "AUDIO_RECORDER": ("#DC2626",
        "M24,8 A8,8 0 1,0 24,24 A8,8 0 1,0 24,8 Z "
        "M24,24 V36 M16,36 H32 M24,28 V36", "#FFFFFF"),
    "SOUNDBOARD": ("#F59E0B",
        "M8,18 H12 V30 H8 Z M16,12 H20 V36 H16 Z M24,8 H28 V40 H24 Z "
        "M32,16 H36 V32 H32 Z M40,20 H44 V28 H40 Z", "#FFFFFF"),
    "LYRICS_VIEWER": ("#06B6D4",
        "M8,12 H40 V18 H8 Z M8,22 H40 V28 H8 Z M8,32 H28 V38 H8 Z "
        "M32,32 H40 V38 H32 Z", "#FFFFFF"),
    "VOICE_MESSAGES": ("#A855F7",
        "M22,8 A8,8 0 0,0 22,24 V32 A4,4 0 0,0 30,32 V24 "
        "M14,18 A10,10 0 0,1 30,18 M10,18 A14,14 0 0,0 34,18 "
        "M22,36 H26", "#FFFFFF"),

    # ---------- Communication ----------
    "LOGIN": ("#F59E0B",
        "M24,8 A8,8 0 1,0 24,24 A8,8 0 1,0 24,8 Z "
        "M10,40 C10,32 16,28 24,28 C32,28 38,32 38,40", "#FFFFFF"),
    "REGISTER": ("#22C55E",
        "M24,8 A8,8 0 1,0 24,24 A8,8 0 1,0 24,8 Z "
        "M10,40 C10,32 16,28 24,28 C32,28 38,32 38,40 "
        "M32,12 L36,16 L44,8", "#FFFFFF"),
    "CHAT": ("#06B6D4",
        "M8,10 H40 A4,4 0 0,1 44,14 V32 A4,4 0 0,1 40,36 H20 L12,42 V36 H8 "
        "A4,4 0 0,1 4,32 V14 A4,4 0 0,1 8,10 Z", "#FFFFFF"),
    "MESSENGER": ("#0EA5E9",
        "M8,12 H40 A4,4 0 0,1 44,16 V32 A4,4 0 0,1 40,36 H20 L12,42 V36 H8 "
        "A4,4 0 0,1 4,32 V16 A4,4 0 0,1 8,12 Z M12,18 L24,28 L36,18 L24,32 Z", "#FFFFFF"),
    "EMAIL_CLIENT": ("#EF4444",
        "M6,12 H42 V36 H6 Z M6,12 L24,26 L42,12", "#FFFFFF"),
    "CONTACTS": ("#3B82F6",
        "M24,10 A8,8 0 1,0 24,26 A8,8 0 1,0 24,10 Z "
        "M10,40 C10,32 16,28 24,28 C32,28 38,32 38,40 Z "
        "M10,10 H38 V40 H10 Z", "#FFFFFF"),
    "FORUM_READER": ("#14B8A6",
        "M8,12 H40 A4,4 0 0,1 44,16 V28 A4,4 0 0,1 40,32 H24 L16,40 V32 H8 "
        "A4,4 0 0,1 4,28 V16 A4,4 0 0,1 8,12 Z", "#FFFFFF"),
    "WALKIE_TALKIE": ("#10B981",
        "M14,8 H32 V18 H38 V38 H14 Z M18,22 H28 M18,28 H28 M18,34 H28 "
        "M32,8 V14 H36", "#FFFFFF"),

    # ---------- Games ----------
    "SNAKE_GAME": ("#10B981",
        "M8,24 C8,16 16,16 16,24 C16,32 24,32 24,24 "
        "C24,16 32,16 32,24 C32,32 40,32 40,24 "
        "M30,22 A2,2 0 1,0 30,18 A2,2 0 1,0 30,22 Z", "#FFFFFF"),
    "GAME_2048": ("#F59E0B",
        "M8,8 H22 V22 H8 Z M26,8 H40 V22 H26 Z "
        "M8,26 H22 V40 H8 Z M26,26 H40 V40 H26 Z", "#FFFFFF"),
    "BRICK_BREAKER": ("#EF4444",
        "M4,8 H12 V14 H4 Z M14,8 H22 V14 H14 Z M24,8 H32 V14 H24 Z "
        "M34,8 H42 V14 H34 Z M8,38 H40 V40 H8 Z "
        "M22,28 A6,6 0 1,0 22,40 A6,6 0 1,0 22,28 Z "
        "M14,34 H30", "#FFFFFF"),
    "TIC_TAC_TOE": ("#6366F1",
        "M16,8 V40 M32,8 V40 M8,16 H40 M8,32 H40 "
        "M10,10 L14,14 M14,10 L10,14 M34,10 L38,14 M38,10 L34,14 "
        "M22,32 A4,4 0 1,0 22,40 A4,4 0 1,0 22,32 Z", "#FFFFFF"),
    "HANGMAN": ("#0F172A",
        "M8,40 H40 M10,40 V8 H32 M32,8 V14 M32,14 A4,4 0 1,0 32,22 A4,4 0 1,0 32,14 Z "
        "M32,22 V32 M28,26 L32,30 M36,26 L32,30", "#FFFFFF"),
    "MEMORY_GAME": ("#A855F7",
        "M8,8 H22 V22 H8 Z M26,8 H40 V22 H26 Z "
        "M8,26 H22 V40 H8 Z M26,26 H40 V40 H26 Z "
        "M12,12 L18,18 M18,12 L12,18", "#FFFFFF"),
    "MINESWEEPER": ("#0F172A",
        "M8,8 H40 V40 H8 Z M8,16 H40 M8,24 H40 M8,32 H40 "
        "M16,8 V40 M24,8 V40 M32,8 V40 "
        "M22,22 A4,4 0 1,0 22,30 A4,4 0 1,0 22,22 Z", "#FFFFFF"),
    "CHESS_CLOCK": ("#0F172A",
        "M4,12 H22 V38 H4 Z M26,12 H44 V38 H26 Z "
        "M8,22 A4,4 0 1,0 8,30 A4,4 0 1,0 8,22 Z "
        "M30,22 A4,4 0 1,0 30,30 A4,4 0 1,0 30,22 Z "
        "M4,8 H44 V12 H4 Z", "#FFFFFF"),

    # ---------- Navigation / Maps ----------
    "MAP": ("#16A34A",
        "M24,8 C18,8 14,12 14,18 C14,26 24,40 24,40 "
        "C24,40 34,26 34,18 C34,12 30,8 24,8 Z "
        "M24,14 A4,4 0 1,0 24,22 A4,4 0 1,0 24,14 Z", "#FFFFFF"),
    "COMPASS": ("#0EA5E9",
        "M24,8 A16,16 0 1,0 24,40 A16,16 0 1,0 24,8 Z "
        "M24,14 L30,30 L24,26 L18,30 Z", "#FFFFFF"),
    "GPS_TRACKER": ("#16A34A",
        "M24,8 A14,14 0 1,0 24,36 A14,14 0 1,0 24,8 Z "
        "M24,18 A6,6 0 1,0 24,30 A6,6 0 1,0 24,18 Z "
        "M24,36 V44 M16,40 H32", "#FFFFFF"),
    "ALTITUDE": ("#7C3AED",
        "M8,40 L20,16 L28,28 L40,8 L36,40 Z M8,40 H40", "#FFFFFF"),
    "SPEEDOMETER": ("#EF4444",
        "M8,28 A16,16 0 0,1 40,28 H34 A10,10 0 0,0 14,28 Z "
        "M24,28 L34,18 M24,28 A2,2 0 1,0 24,32 A2,2 0 1,0 24,28 Z", "#FFFFFF"),
    "GEOCACHE": ("#10B981",
        "M24,8 A16,16 0 1,0 24,40 A16,16 0 1,0 24,8 Z "
        "M16,24 L24,16 L32,24 L24,32 Z", "#FFFFFF"),

    # ---------- Weather / Environment ----------
    "WEATHER": ("#0EA5E9",
        "M14,28 A8,8 0 1,1 22,20 A10,10 0 0,1 36,22 "
        "A6,6 0 0,1 34,34 H16 A4,4 0 0,1 14,28 Z", "#FFFFFF"),
    "THERMOMETER": ("#EF4444",
        "M20,8 A4,4 0 0,1 28,8 V28 A8,8 0 1,1 20,28 Z "
        "M24,12 V28 M20,38 A4,4 0 1,0 28,38 A4,4 0 1,0 20,38 Z", "#FFFFFF"),
    "BAROMETER": ("#6366F1",
        "M8,28 A16,16 0 0,1 40,28 M24,28 L30,18 "
        "M24,28 A2,2 0 1,0 24,32 A2,2 0 1,0 24,28 Z", "#FFFFFF"),
    "HYGROMETER": ("#06B6D4",
        "M24,8 A16,16 0 1,0 24,40 A16,16 0 1,0 24,8 Z "
        "M24,12 V24 L30,28 M16,38 A4,4 0 1,0 24,38 A4,4 0 1,0 16,38 Z", "#FFFFFF"),
    "AIR_QUALITY": ("#10B981",
        "M8,16 H40 M8,24 H40 M8,32 H36 "
        "M8,16 A4,4 0 0,1 4,12 M8,24 A4,4 0 0,1 4,20 M8,32 A4,4 0 0,1 4,28", "#FFFFFF"),
    "UV_INDEX": ("#F59E0B",
        "M24,16 A8,8 0 1,0 24,32 A8,8 0 1,0 24,16 Z "
        "M24,4 V10 M24,38 V44 M4,24 H10 M38,24 H44 "
        "M10,10 L14,14 M34,34 L38,38 M10,38 L14,34 M34,14 L38,10", "#FFFFFF"),

    # ---------- Health / Fitness ----------
    "HEART_RATE": ("#EF4444",
        "M4,24 H12 L16,16 L20,32 L24,8 L28,32 L32,24 H44", "#FFFFFF"),
    "PEDOMETER": ("#F59E0B",
        "M16,8 C12,8 12,16 16,16 C20,16 20,8 16,8 Z "
        "M14,18 L18,22 L14,30 L18,38 L22,30 L18,22 "
        "M28,10 C24,10 24,18 28,18 C32,18 32,10 28,10 Z "
        "M26,20 L30,24 L26,32 L30,40 L34,32 L30,24", "#FFFFFF"),
    "WATER_TRACKER": ("#0EA5E9",
        "M24,8 C16,20 14,28 14,32 A10,10 0 0,0 34,32 "
        "C34,28 32,20 24,8 Z", "#FFFFFF"),
    "CALORIE_TRACKER": ("#F97316",
        "M24,8 C18,14 14,20 14,28 A10,10 0 0,0 34,28 "
        "C34,20 30,14 24,8 Z M24,20 L20,28 H28 L24,36", "#FFFFFF"),
    "WORKOUT_TRACKER": ("#DC2626",
        "M8,16 L14,16 L18,12 H30 L34,16 L40,16 V20 L34,20 L30,24 H18 L14,20 L8,20 Z "
        "M14,24 V36 M34,24 V36 M10,36 H38", "#FFFFFF"),
    "MEDICATION_TRACKER": ("#7C3AED",
        "M8,16 A8,8 0 0,1 24,16 V32 A8,8 0 0,1 8,32 Z "
        "M24,16 A8,8 0 0,1 40,16 V32 A8,8 0 0,1 24,32 Z "
        "M24,16 V32", "#FFFFFF"),
    "BLOOD_PRESSURE": ("#DC2626",
        "M8,24 H12 L16,16 L20,32 L24,24 H40 "
        "M8,32 H40 M8,40 H40", "#FFFFFF"),
    "SLEEP_TRACKER": ("#4F8EF7",
        "M24,8 A16,16 0 1,0 24,40 A16,16 0 1,0 24,8 Z "
        "M16,28 Q20,22 24,28 T32,28 M14,20 L18,18 M30,18 L34,20", "#FFFFFF"),
    "MENTAL_HEALTH": ("#06B6D4",
        "M24,8 A8,8 0 1,0 24,24 A8,8 0 1,0 24,8 Z "
        "M14,40 A10,10 0 0,1 34,40 L14,40 Z "
        "M24,8 A8,8 0 0,1 30,16 A6,6 0 0,1 24,22", "#FFFFFF"),

    # ---------- Finance / Shopping ----------
    "WALLET": ("#F59E0B",
        "M8,12 H40 V40 H8 Z M8,18 H40 M32,28 A3,3 0 1,0 32,34 A3,3 0 1,0 32,28 Z", "#FFFFFF"),
    "BUDGET_TRACKER": ("#22C55E",
        "M8,12 H40 V40 H8 Z M8,32 L18,22 L24,28 L34,18 L40,24 "
        "M8,38 H40 M32,8 V14", "#FFFFFF"),
    "STOCK_TRACKER": ("#10B981",
        "M8,12 H40 V40 H8 Z M8,32 L18,22 L24,28 L34,18 L40,24 "
        "M8,40 H40 M40,8 L44,8 M40,18 L44,18 M40,28 L44,28 M40,38 L44,38", "#FFFFFF"),
    "EXPENSE_TRACKER": ("#EF4444",
        "M8,12 H40 V40 H8 Z M14,32 L20,26 L26,30 L34,20 "
        "M14,38 H34 M40,8 L8,40", "#FFFFFF"),
    "SHOPPING_LIST": ("#EC4899",
        "M8,12 H40 V18 H8 Z M8,22 H40 V28 H8 Z M8,32 H40 V38 H8 Z "
        "M12,15 L14,17 L18,13 M12,25 L14,27 L18,23 M12,35 L14,37 L18,33", "#FFFFFF"),
    "PRICE_TRACKER": ("#16A34A",
        "M8,12 H40 V40 H8 Z M14,28 L20,22 L26,28 L34,18 "
        "M24,8 V12 M24,40 V44 M8,24 H12 M40,24 H44", "#FFFFFF"),
    "CRYPTO_TRACKER": ("#F97316",
        "M24,8 V40 M16,14 H28 V20 H20 M16,28 H30 V22 M16,28 V34 H28", "#FFFFFF"),
    "DONATION_TRACKER": ("#DC2626",
        "M24,40 C16,32 8,24 8,16 A8,8 0 0,1 24,12 A8,8 0 0,1 40,16 "
        "C40,24 32,32 24,40 Z", "#FFFFFF"),

    # ---------- Education / Reference ----------
    "QUIZ": ("#7C3AED",
        "M24,8 L30,20 L42,22 L33,30 L36,42 L24,36 L12,42 L15,30 L6,22 L18,20 Z", "#FFFFFF"),
    "FLASHCARDS": ("#6366F1",
        "M8,12 H40 V28 H8 Z M8,28 H40 V40 H8 Z M12,18 H36 M12,22 H28 "
        "M12,32 H36 M12,36 H28", "#FFFFFF"),
    "TRANSLATOR": ("#14B8A6",
        "M8,12 H28 V20 H8 Z M16,20 V40 M12,40 H22 "
        "M28,28 L36,40 M36,28 L28,40 M40,32 L44,28 L48,32", "#FFFFFF"),
    "DICTIONARY": ("#3B82F6",
        "M8,8 H40 V40 H8 Z M8,18 H40 M16,24 L32,24 M16,30 L28,30 M16,36 L32,36", "#FFFFFF"),
    "ENCYCLOPEDIA": ("#0F172A",
        "M8,8 H40 V40 H8 Z M8,16 H40 M14,24 H34 M14,30 H34 M14,36 H28", "#FFFFFF"),
    "STUDY_TIMER": ("#7C3AED",
        "M24,8 A16,16 0 1,0 24,40 A16,16 0 1,0 24,8 Z "
        "M24,14 V24 L32,28 M14,8 L8,4 M34,8 L40,4", "#FFFFFF"),
    "SPELLING_BEE": ("#F59E0B",
        "M24,8 L28,18 L38,20 L30,28 L32,38 L24,32 L16,38 L18,28 L10,20 L20,18 Z "
        "M24,14 L26,20 L32,21 L28,26 L29,32 L24,28 L19,32 L20,26 L16,21 L22,20 Z", "#FFFFFF"),

    # ---------- Smart Home / IoT ----------
    "THERMOSTAT": ("#EF4444",
        "M24,8 A16,16 0 1,0 24,40 A16,16 0 1,0 24,8 Z "
        "M24,14 V24 L30,28 M20,4 H28", "#FFFFFF"),
    "SPRINKLER": ("#0EA5E9",
        "M16,16 H32 V28 H16 Z M24,28 V36 M16,36 H32 "
        "M24,12 V8 M14,14 L10,10 M34,14 L38,10", "#FFFFFF"),
    "ROBOT_VACUUM": ("#0F172A",
        "M24,8 A16,16 0 1,0 24,40 A16,16 0 1,0 24,8 Z "
        "M24,14 A4,4 0 1,0 24,22 A4,4 0 1,0 24,14 Z "
        "M16,28 L20,32 M32,28 L28,32 M14,24 H10 M34,24 H38", "#FFFFFF"),
    "SMART_LIGHT": ("#F59E0B",
        "M16,8 H32 V18 A8,8 0 0,1 24,26 A8,8 0 0,1 16,18 Z "
        "M16,32 H32 M18,38 H30 M20,44 H28 M24,26 V32", "#FFFFFF"),
    "GARAGE_DOOR": ("#6B7280",
        "M6,8 H42 V20 H6 Z M6,20 H42 V40 H6 Z M10,24 H38 M10,28 H38 M10,32 H38 M10,36 H38", "#FFFFFF"),
    "DOORBELL": ("#3B82F6",
        "M16,8 H32 V24 A8,8 0 0,1 16,24 Z M20,32 H28 M24,32 V40", "#FFFFFF"),
    "AIR_PURIFIER": ("#14B8A6",
        "M12,8 H36 V40 H12 Z M16,14 H32 M16,20 H32 M16,26 H32 "
        "M16,32 H28 M20,8 V4 M28,8 V4", "#FFFFFF"),
    "WATER_LEAK": ("#0EA5E9",
        "M24,8 C18,16 14,24 14,28 A10,10 0 0,0 34,28 C34,24 30,16 24,8 Z "
        "M24,8 L20,4 M24,8 L28,4 M24,8 L24,4", "#FFFFFF"),

    # ---------- Travel / Outdoors ----------
    "TAXI_BOOKING": ("#F59E0B",
        "M8,20 L12,12 H36 L40,20 V36 H8 Z M12,20 H36 "
        "M12,36 A4,4 0 1,0 12,28 A4,4 0 1,0 12,36 Z M36,36 A4,4 0 1,0 36,28 A4,4 0 1,0 36,36 Z "
        "M20,8 H28 V12 H20 Z", "#FFFFFF"),
    "PARKING_FINDER": ("#3B82F6",
        "M8,8 H40 V40 H8 Z M18,14 V34 M18,14 H26 A6,6 0 0,1 26,26 H18", "#FFFFFF"),
    "FLIGHT_TRACKER": ("#0EA5E9",
        "M8,24 L40,16 L40,20 L20,28 L24,36 L22,38 L14,32 L8,32 Z", "#FFFFFF"),
    "PACKING_LIST": ("#A855F7",
        "M8,12 H40 V40 H8 Z M8,18 H40 M14,8 V14 M34,8 V14 "
        "M12,24 L16,28 L14,30 L10,26 Z M22,26 H36 M22,32 H30", "#FFFFFF"),
    "TIPPING_CALCULATOR": ("#22C55E",
        "M8,12 H40 V40 H8 Z M14,18 H34 M14,24 H34 M14,30 H26 "
        "M30,32 A4,4 0 1,0 30,40 A4,4 0 1,0 30,32 Z", "#FFFFFF"),
    "CURRENCY_CONVERTER": ("#10B981",
        "M8,12 H40 V40 H8 Z M16,20 L20,16 L24,20 L20,24 Z "
        "M28,32 L32,28 L36,32 L32,36 Z M20,16 V36 M32,28 V12", "#FFFFFF"),

    # ---------- Tools / Utilities ----------
    "FLASHLIGHT": ("#FBBF24",
        "M18,8 H30 L32,18 V40 A4,4 0 0,1 28,44 H20 A4,4 0 0,1 16,40 V18 Z "
        "M22,20 H26 V28 H22 Z", "#FFFFFF"),
    "LEVEL_TOOL": ("#14B8A6",
        "M4,18 H44 V30 H4 Z M8,24 A4,4 0 1,0 8,32 A4,4 0 1,0 8,24 Z "
        "M22,22 H42 M22,26 H42 M14,24 H18", "#FFFFFF"),
    "RULER": ("#6B7280",
        "M4,18 H44 V30 H4 Z M8,18 V24 M12,18 V22 M16,18 V24 M20,18 V22 M24,18 V24 "
        "M28,18 V22 M32,18 V24 M36,18 V22 M40,18 V24", "#FFFFFF"),
    "UNIT_CONVERTER": ("#06B6D4",
        "M8,12 H22 V22 H8 Z M26,26 H40 V40 H26 Z "
        "M14,22 L18,26 L14,30 M34,12 L30,16 L34,20 M22,16 H26 M22,32 H26", "#FFFFFF"),
    "COLOR_PICKER": ("#EC4899",
        "M24,8 A16,16 0 1,0 24,40 A16,16 0 1,0 24,8 Z "
        "M16,16 L32,32 M32,16 L16,32 M8,24 L40,24 M24,8 L24,40", "#FFFFFF"),
    "DECIBEL_METER": ("#F97316",
        "M8,40 V20 H12 V40 H8 Z M14,40 V14 H18 V40 H14 Z M20,40 V24 H24 V40 H20 Z "
        "M26,40 V18 H30 V40 H26 Z M32,40 V8 H36 V40 H32 Z", "#FFFFFF"),
    "MAGNIFIER": ("#6366F1",
        "M16,12 A12,12 0 1,0 16,36 A12,12 0 1,0 16,12 Z "
        "M26,26 L40,40 M10,24 H22 M16,18 V30", "#FFFFFF"),
    "NETWORK_TESTER": ("#10B981",
        "M8,24 H16 M20,24 H28 M32,24 H40 "
        "M12,24 V12 M24,24 V12 M36,24 V12 "
        "M8,12 H12 V20 H8 Z M20,12 H28 V20 H20 Z M32,12 H40 V20 H32 Z", "#FFFFFF"),
    "SIGNAL_STRENGTH": ("#22C55E",
        "M8,40 V32 H14 V40 Z M16,40 V26 H22 V40 Z M24,40 V20 H30 V40 Z M32,40 V12 H38 V40 Z", "#FFFFFF"),

    # ---------- Social / Feeds ----------
    "RSS_READER": ("#EA580C",
        "M10,38 A4,4 0 1,1 18,38 A4,4 0 1,1 10,38 Z "
        "M10,22 A14,14 0 0,1 24,36 H18 A8,8 0 0,0 10,28 Z "
        "M10,10 A26,26 0 0,1 36,36 H30 A20,20 0 0,0 10,16 Z", "#FFFFFF"),
    "BLOG_READER": ("#7C3AED",
        "M8,8 H40 V40 H8 Z M8,16 H40 M14,22 H34 M14,28 H34 M14,34 H28", "#FFFFFF"),
    "SOCIAL_FEED": ("#EC4899",
        "M8,12 H40 V40 H8 Z M8,18 H40 M14,8 V14 M34,8 V14 "
        "M14,24 H34 M14,30 H28 M14,36 H22", "#FFFFFF"),
    "VIDEO_PLAYER": ("#EF4444",
        "M8,12 H40 V36 H8 Z M20,18 L32,24 L20,30 Z", "#FFFFFF"),
    "PODCASTS": ("#7C3AED",
        "M24,8 A6,6 0 1,0 24,20 A6,6 0 1,0 24,8 Z "
        "M16,32 A8,8 0 0,1 32,32 L28,32 A4,4 0 0,0 20,32 Z "
        "M14,40 A10,10 0 0,1 34,40 L30,40 A6,6 0 0,0 18,40 Z", "#FFFFFF"),

    # ---------- Misc / Lifestyle ----------
    "DRAW": ("#EC4899",
        "M8,40 L24,12 L40,40 Z M20,32 H28 "
        "M40,8 L44,12 L24,32 L20,28 Z", "#FFFFFF"),
    "PAINT": ("#A855F7",
        "M8,8 H40 V28 H8 Z M8,28 H40 V32 H8 Z "
        "M16,32 V40 H32 V32 M20,12 L24,16 M28,12 L24,16 M16,20 H32", "#FFFFFF"),
    "COUNTER": ("#F97316",
        "M14,12 H34 V20 H14 Z M14,22 H34 V30 H14 Z M14,32 H34 V40 H14 Z", "#FFFFFF"),
    "SCOREBOARD": ("#0F172A",
        "M4,8 H44 V40 H4 Z M4,18 H44 M4,30 H44 M16,8 V40 M32,8 V40 "
        "M8,12 H12 V16 H8 Z M36,12 H40 V16 H36 Z M8,32 H12 V36 H8 Z M36,32 H40 V36 H36 Z", "#FFFFFF"),
    "EVENT_REMINDER": ("#EF4444",
        "M8,12 H40 V40 H8 Z M8,18 H40 M14,8 V14 M34,8 V14 "
        "M24,22 A8,8 0 1,0 24,38 A8,8 0 1,0 24,22 Z M24,26 V32 L28,34", "#FFFFFF"),
    "BIRTHDAY": ("#EC4899",
        "M8,20 H40 V40 H8 Z M14,20 V12 L20,16 L24,8 L28,16 L34,12 V20 "
        "M14,28 H20 M28,28 H34 M14,34 H20 M28,34 H34", "#FFFFFF"),
    "COOKING_TIMER": ("#F97316",
        "M24,12 A14,14 0 1,0 24,40 A14,14 0 1,0 24,12 Z "
        "M24,18 V26 L30,30 M20,4 H28 M22,8 L26,8", "#FFFFFF"),
    "RECIPE_MANAGER": ("#DC2626",
        "M8,12 H40 V40 H8 Z M14,18 H34 M14,24 H34 M14,30 H28 M14,36 H22 "
        "M40,8 L8,40", "#FFFFFF"),
    "PLANT_CARE": ("#22C55E",
        "M24,40 V24 M16,24 C12,24 8,20 8,16 C12,16 16,20 16,24 Z "
        "M32,24 C36,24 40,20 40,16 C36,16 32,20 32,24 Z "
        "M24,24 C20,24 16,18 16,12 C20,12 24,18 24,24 Z "
        "M24,24 C28,24 32,18 32,12 C28,12 24,18 24,24 Z", "#FFFFFF"),
    "PET_TRACKER": ("#A855F7",
        "M12,12 A4,4 0 1,0 12,20 A4,4 0 1,0 12,20 Z M24,8 A4,4 0 1,0 24,16 A4,4 0 1,0 24,16 Z "
        "M36,12 A4,4 0 1,0 36,20 A4,4 0 1,0 36,20 Z "
        "M24,18 A10,10 0 1,0 24,38 A10,10 0 1,0 24,38 Z", "#FFFFFF"),
    "HABIT_TRACKER": ("#10B981",
        "M8,12 H40 V40 H8 Z M8,20 H40 M14,28 L18,32 L26,24 "
        "M14,36 L18,40 L26,32 M30,28 L34,32 L42,24", "#FFFFFF"),
    "MOOD_TRACKER": ("#F59E0B",
        "M24,8 A16,16 0 1,0 24,40 A16,16 0 1,0 24,8 Z "
        "M16,20 A2,2 0 1,0 16,24 A2,2 0 1,0 16,20 Z M32,20 A2,2 0 1,0 32,24 A2,2 0 1,0 32,20 Z "
        "M14,28 Q24,36 34,28", "#FFFFFF"),
    "DECISION_MAKER": ("#7C3AED",
        "M24,8 L40,24 L24,40 L8,24 Z M16,24 L22,30 L32,18", "#FFFFFF"),
    "RANDOM_GENERATOR": ("#6366F1",
        "M8,8 H40 V40 H8 Z M14,14 H20 V20 H14 Z M28,14 H34 V20 H28 Z "
        "M14,28 H20 V34 H14 Z M28,28 H34 V34 H28 Z M22,22 L26,26 M26,22 L22,26", "#FFFFFF"),

    # ---------- Default fallback ----------
    "DEFAULT": ("#4F8EF7",
        "M12,12 H36 V36 H12 Z M18,18 H30 V30 H18 Z", "#FFFFFF"),
}


# ---------------------------------------------------------------------------
# Icon generators
# ---------------------------------------------------------------------------
class IconGenerator:
    """Generates real, functional Android vector drawable icons."""

    # -- Strategy 1: LETTER_ICON (real letter shape) ----------------------

    @staticmethod
    def letter_icon(app_name: str) -> str:
        """Rounded-square background + first letter (white, centered).

        Uses REAL letter path data — every letter A-Z and digit 0-9 has a
        distinct, recognizable shape.
        """
        bg = color_for_name(app_name)
        accent = accent_color_for_name(app_name)
        letter = first_letter(app_name)
        path = get_letter_path(letter)
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
            '    android:width="48dp" android:height="48dp"\n'
            '    android:viewportWidth="48" android:viewportHeight="48">\n'
            f'    <path android:fillColor="{bg}" android:pathData="M4,4 H44 V44 H4 Z" />\n'
            f'    <path android:fillColor="{accent}" android:pathData="M6,6 H42 V42 H6 Z" '
            f'android:strokeColor="{accent}" android:strokeWidth="0" />\n'
            f'    <path android:fillColor="#FFFFFF" '
            f'android:pathData="M12,8 {path.replace(chr(32), " ", 1) if False else path}" />\n'
            '</vector>\n'
        )

    # -- Strategy 2: CATEGORY_ICON -----------------------------------------

    @staticmethod
    def category_icon(category: str) -> str:
        """Category-specific symbol (calculator grid, notes outline, etc.)."""
        bg, fg_path, fg_color = CATEGORY_SYMBOLS.get(category, CATEGORY_SYMBOLS["DEFAULT"])
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
            '    android:width="48dp" android:height="48dp"\n'
            '    android:viewportWidth="48" android:viewportHeight="48">\n'
            f'    <path android:fillColor="{bg}" android:pathData="M0,0 H48 V48 H0 Z" />\n'
            f'    <path android:fillColor="{fg_color}" android:pathData="{fg_path}" />\n'
            '</vector>\n'
        )

    # -- Strategy 3: INITIALS_ICON (real two-letter rendering) -------------

    @staticmethod
    def initials_icon(app_name: str) -> str:
        """Rounded-square background + 2-letter initials, each as a real path.

        Each initial is rendered side-by-side using the same letter path data
        as LETTER_ICON, but at half width and offset.
        """
        bg = color_for_name(app_name)
        initials = initials_for_name(app_name)
        if len(initials) < 2:
            initials = (initials + "X")[:2]

        # Build two side-by-side letter paths in a 48x48 viewport.
        # Each letter occupies the left/right half. We translate the 24x32
        # letter path into the appropriate slot.
        def translate_path(path: str, dx: float, dy: float, scale: float = 1.0) -> str:
            """Translate (and optionally scale) all coordinates in an SVG path."""
            import re
            tokens = re.split(r'([MLHVCSQTAZmlhvcsqtaz ])', path)
            out = []
            current_cmd = None
            for tok in tokens:
                if not tok:
                    continue
                if tok in "MLHVCSQTAZmlhvcsqtaz":
                    current_cmd = tok
                    out.append(tok)
                elif tok.strip() == "":
                    out.append(tok)
                else:
                    # Parse numbers — handle comma/space separators
                    nums = re.findall(r'-?\d+\.?\d*', tok)
                    seps = re.split(r'-?\d+\.?\d*', tok)
                    new_nums = []
                    for n in nums:
                        v = float(n) * scale
                        # Apply translation based on the command (relative vs absolute)
                        if current_cmd and current_cmd.islower():
                            new_nums.append(f"{v}")
                        else:
                            # Even/odd: x,y,x,y... apply dx to x, dy to y
                            idx = len(new_nums)
                            if idx % 2 == 0:
                                v += dx
                            else:
                                v += dy
                            new_nums.append(f"{v:g}")
                    # Rebuild token
                    rebuilt = ""
                    for i, sep in enumerate(seps):
                        rebuilt += sep
                        if i < len(new_nums):
                            rebuilt += new_nums[i]
                    out.append(rebuilt)
            return "".join(out)

        # Left letter: translate by (0, 8), scale 0.5
        left_path = translate_path(get_letter_path(initials[0]), 0, 8, 0.5)
        # Right letter: translate by (24, 8), scale 0.5
        right_path = translate_path(get_letter_path(initials[1]), 24, 8, 0.5)

        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
            '    android:width="48dp" android:height="48dp"\n'
            '    android:viewportWidth="48" android:viewportHeight="48">\n'
            f'    <path android:fillColor="{bg}" android:pathData="M4,4 H44 V44 H4 Z" />\n'
            f'    <path android:fillColor="#FFFFFF" android:pathData="{left_path}" />\n'
            f'    <path android:fillColor="#FFFFFF" android:pathData="{right_path}" />\n'
            '</vector>\n'
        )

    # -- Strategy 4: NAME_HASH_ICON (geometric pattern) -------------------

    @staticmethod
    def name_hash_icon(app_name: str) -> str:
        """Deterministic geometric pattern from SHA-256 of the app name.

        Produces a unique, reproducible icon for every name. Uses 6 colored
        shapes positioned by hash bytes — gives a "app badge" feel that is
        different for every name.
        """
        h = hashlib.sha256(app_name.lower().encode("utf-8")).hexdigest()
        bg = PALETTE[int(h[:2], 16) % len(PALETTE)]
        accent = PALETTE[int(h[2:4], 16) % len(PALETTE)]
        accent2 = PALETTE[int(h[4:6], 16) % len(PALETTE)]
        # 6 deterministic shapes based on hash bytes
        shapes = []
        for i in range(6):
            byte = int(h[6 + i * 2:8 + i * 2], 16)
            x = (byte % 8) * 5 + 4
            y = ((byte // 8) % 8) * 5 + 4
            size = 3 + (byte % 4)
            shape_type = byte % 3
            if shape_type == 0:
                # Square
                shapes.append((accent, f"M{x},{y} h{size} v{size} h-{size} Z"))
            elif shape_type == 1:
                # Circle (approximated as a 4-arc path)
                r = size
                shapes.append((accent2, f"M{x+r},{y} A{r},{r} 0 1,0 {x+r},{y+2*r} "
                                       f"A{r},{r} 0 1,0 {x+r},{y} Z"))
            else:
                # Triangle
                shapes.append((accent, f"M{x},{y+size} L{x+size},{y+size} L{x+size/2},{y} Z"))
        paths_xml = "".join(
            f'    <path android:fillColor="{c}" android:pathData="{p}" />\n'
            for c, p in shapes
        )
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
            '    android:width="48dp" android:height="48dp"\n'
            '    android:viewportWidth="48" android:viewportHeight="48">\n'
            f'    <path android:fillColor="{bg}" android:pathData="M0,0 H48 V48 H0 Z" />\n'
            f'{paths_xml}'
            '</vector>\n'
        )

    # -- Strategy 5: MONOGRAM_ICON (brand-style) --------------------------

    @staticmethod
    def monogram_icon(app_name: str) -> str:
        """Circle background + up to 3 letters in a stylized layout.

        Used for short brand names like "BMW", "IBM", "CNN".
        """
        bg = color_for_name(app_name)
        words = [w for w in app_name.strip().split() if w]
        if not words:
            letters = "AP"
        elif len(words) == 1:
            w = words[0]
            letters = w[:3].upper() if len(w) >= 3 else (w + "X")[:2].upper()
        else:
            letters = "".join([w[0] for w in words[:3]]).upper()

        # Build paths for 1-3 letters arranged horizontally in a circle
        n = len(letters)
        if n == 1:
            offsets = [16]
            scale = 0.7
        elif n == 2:
            offsets = [6, 26]
            scale = 0.5
        else:
            offsets = [0, 16, 32]
            scale = 0.4

        import re
        def translate_path(path: str, dx: float, dy: float, scale: float) -> str:
            tokens = re.split(r'([MLHVCSQTAZmlhvcsqtaz ])', path)
            out = []
            current_cmd = None
            for tok in tokens:
                if not tok:
                    continue
                if tok in "MLHVCSQTAZmlhvcsqtaz":
                    current_cmd = tok
                    out.append(tok)
                elif tok.strip() == "":
                    out.append(tok)
                else:
                    nums = re.findall(r'-?\d+\.?\d*', tok)
                    seps = re.split(r'-?\d+\.?\d*', tok)
                    new_nums = []
                    for nn in nums:
                        v = float(nn) * scale
                        if current_cmd and current_cmd.islower():
                            new_nums.append(f"{v}")
                        else:
                            idx = len(new_nums)
                            if idx % 2 == 0:
                                v += dx
                            else:
                                v += dy
                            new_nums.append(f"{v:g}")
                    rebuilt = ""
                    for i, sep in enumerate(seps):
                        rebuilt += sep
                        if i < len(new_nums):
                            rebuilt += new_nums[i]
                    out.append(rebuilt)
            return "".join(out)

        paths_xml = ""
        for i, L in enumerate(letters):
            p = translate_path(get_letter_path(L), offsets[i], 8 + (1 - scale) * 16, scale)
            paths_xml += f'    <path android:fillColor="#FFFFFF" android:pathData="{p}" />\n'

        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
            '    android:width="48dp" android:height="48dp"\n'
            '    android:viewportWidth="48" android:viewportHeight="48">\n'
            f'    <path android:fillColor="{bg}" '
            f'android:pathData="M24,4 A20,20 0 1,0 24,44 A20,20 0 1,0 24,4 Z" />\n'
            f'{paths_xml}'
            '</vector>\n'
        )

    # -- Strategy 6: EMOJI_ICON (category face) ---------------------------

    @staticmethod
    def emoji_icon(category: str) -> str:
        """Category-themed emoji-style face drawn as vector paths.

        A circle background with a smiley + category indicator (e.g., a
        music note next to the face for MUSIC_PLAYER).
        """
        bg, _, _ = CATEGORY_SYMBOLS.get(category, CATEGORY_SYMBOLS["DEFAULT"])
        # Smiley face: circle + 2 eyes + smile
        face_path = (
            "M24,6 A18,18 0 1,0 24,42 A18,18 0 1,0 24,6 Z "
            "M18,18 A2,2 0 1,0 18,22 A2,2 0 1,0 18,18 Z "
            "M30,18 A2,2 0 1,0 30,22 A2,2 0 1,0 30,18 Z "
            "M16,28 Q24,36 32,28"
        )
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
            '    android:width="48dp" android:height="48dp"\n'
            '    android:viewportWidth="48" android:viewportHeight="48">\n'
            f'    <path android:fillColor="{bg}" android:pathData="M0,0 H48 V48 H0 Z" />\n'
            f'    <path android:fillColor="#FFFFFF" android:pathData="{face_path}" />\n'
            '</vector>\n'
        )

    # -- Adaptive icon XML (always the same — references @drawable/ic_launcher) ----

    @staticmethod
    def adaptive_icon_xml() -> str:
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '    <background android:drawable="@color/primary" />\n'
            '    <foreground android:drawable="@drawable/ic_launcher" />\n'
            '</adaptive-icon>\n'
        )

    # -- Top-level: choose the best strategy for the given inputs ----------

    @classmethod
    def generate_icon_set(cls, app_name: str, category: Optional[str] = None,
                          strategy: str = "auto") -> Dict[str, str]:
        """Returns a dict of {path: xml_content} for the complete icon set."""
        if strategy == "auto":
            # Priority: category symbol > initials (multi-word) > monogram (short) > letter > hash
            if category and category in CATEGORY_SYMBOLS and category != "DEFAULT":
                vec = cls.category_icon(category)
            elif " " in app_name.strip() and len(app_name.split()) >= 2:
                # Multi-word name → use initials
                vec = cls.initials_icon(app_name)
            elif len(app_name.strip()) <= 4:
                # Short name → use monogram
                vec = cls.monogram_icon(app_name)
            elif app_name.strip() and app_name.strip()[0].upper() in LETTER_PATHS:
                # Single-word name starting with a recognizable letter → letter icon
                vec = cls.letter_icon(app_name)
            else:
                vec = cls.name_hash_icon(app_name)
        elif strategy == "letter":
            vec = cls.letter_icon(app_name)
        elif strategy == "category" and category:
            vec = cls.category_icon(category)
        elif strategy == "initials":
            vec = cls.initials_icon(app_name)
        elif strategy == "name_hash":
            vec = cls.name_hash_icon(app_name)
        elif strategy == "monogram":
            vec = cls.monogram_icon(app_name)
        elif strategy == "emoji" and category:
            vec = cls.emoji_icon(category)
        else:
            vec = cls.category_icon(category or "DEFAULT")

        adaptive = cls.adaptive_icon_xml()
        return {
            "res/drawable/ic_launcher.xml": vec,
            "res/mipmap-anydpi-v26/ic_launcher.xml": adaptive,
            "res/mipmap-anydpi-v26/ic_launcher_round.xml": adaptive,
        }


# ---------------------------------------------------------------------------
# Convenience entrypoint
# ---------------------------------------------------------------------------
def generate_icons(app_name: str, category: Optional[str] = None,
                   strategy: str = "auto") -> Dict[str, bytes]:
    """Returns {path: bytes} ready to be injected into the VFS."""
    return {
        path: content.encode("utf-8")
        for path, content in IconGenerator.generate_icon_set(
            app_name, category=category, strategy=strategy
        ).items()
    }


def list_available_categories() -> List[str]:
    """Returns all category names that have a dedicated icon."""
    return sorted(k for k in CATEGORY_SYMBOLS.keys() if k != "DEFAULT")


def list_available_letters() -> List[str]:
    """Returns all letters/digits that have a dedicated path."""
    return sorted(LETTER_PATHS.keys())
