"""
Dristik AI Google SERP Pixel Width Calculator
Calculates exact pixel widths of title tags and meta descriptions in Google SERP font metrics
(Arial 18px for desktop titles, Arial 13px for meta descriptions).
Industry Standard: Screaming Frog / Ahrefs SERP Truncation Model.
"""
from typing import Tuple

# Arial 18px character width lookup table (approximate character widths in pixels)
# Desktop Google Title font: Arial, sans-serif, ~18-20px
_ARIAL_18PX_WIDTHS = {
    ' ': 5, '!': 6, '"': 7, '#': 11, '$': 10, '%': 16, '&': 12, "'": 4,
    '(': 6, ')': 6, '*': 7, '+': 11, ',': 5, '-': 6, '.': 5, '/': 5,
    '0': 10, '1': 10, '2': 10, '3': 10, '4': 10, '5': 10, '6': 10, '7': 10,
    '8': 10, '9': 10, ':': 5, ';': 5, '<': 11, '=': 11, '>': 11, '?': 10,
    '@': 18, 'A': 12, 'B': 12, 'C': 13, 'D': 13, 'E': 12, 'F': 11, 'G': 14,
    'H': 13, 'I': 5, 'J': 9, 'K': 12, 'L': 10, 'M': 15, 'N': 13, 'O': 14,
    'P': 12, 'Q': 14, 'R': 13, 'S': 12, 'T': 11, 'U': 13, 'V': 12, 'W': 17,
    'X': 12, 'Y': 12, 'Z': 11, '[': 5, '\\': 5, ']': 5, '^': 9, '_': 10,
    '`': 6, 'a': 10, 'b': 10, 'c': 9, 'd': 10, 'e': 10, 'f': 5, 'g': 10,
    'h': 10, 'i': 4, 'j': 4, 'k': 9, 'l': 4, 'm': 15, 'n': 10, 'o': 10,
    'p': 10, 'q': 10, 'r': 6, 's': 9, 't': 5, 'u': 10, 'v': 9, 'w': 13,
    'x': 9, 'y': 9, 'z': 9, '{': 6, '|': 5, '}': 6, '~': 11,
}

# Arial 13px character width lookup table (approximate character widths in pixels)
# Desktop Google Snippet font: Arial, sans-serif, ~13-14px
_ARIAL_13PX_WIDTHS = {
    ' ': 4, '!': 4, '"': 5, '#': 8, '$': 7, '%': 12, '&': 9, "'": 3,
    '(': 4, ')': 4, '*': 5, '+': 8, ',': 4, '-': 4, '.': 4, '/': 4,
    '0': 7, '1': 7, '2': 7, '3': 7, '4': 7, '5': 7, '6': 7, '7': 7,
    '8': 7, '9': 7, ':': 4, ';': 4, '<': 8, '=': 8, '>': 8, '?': 7,
    '@': 13, 'A': 9, 'B': 9, 'C': 9, 'D': 9, 'E': 9, 'F': 8, 'G': 10,
    'H': 9, 'I': 4, 'J': 6, 'K': 9, 'L': 7, 'M': 11, 'N': 9, 'O': 10,
    'P': 9, 'Q': 10, 'R': 9, 'S': 9, 'T': 8, 'U': 9, 'V': 9, 'W': 12,
    'X': 9, 'Y': 9, 'Z': 8, '[': 4, '\\': 4, ']': 4, '^': 6, '_': 7,
    '`': 4, 'a': 7, 'b': 7, 'c': 7, 'd': 7, 'e': 7, 'f': 4, 'g': 7,
    'h': 7, 'i': 3, 'j': 3, 'k': 7, 'l': 3, 'm': 11, 'n': 7, 'o': 7,
    'p': 7, 'q': 7, 'r': 4, 's': 7, 't': 4, 'u': 7, 'v': 7, 'w': 9,
    'x': 7, 'y': 7, 'z': 7, '{': 4, '|': 4, '}': 4, '~': 8,
}

# Standard Google SERP truncation bounds in pixels
GOOGLE_TITLE_MAX_PX = 580
GOOGLE_TITLE_MIN_PX = 200
GOOGLE_META_MAX_PX = 960
GOOGLE_META_MIN_PX = 350


def calculate_title_pixel_width(text: str) -> int:
    """Calculate exact pixel width of title text using Arial 18px font metric."""
    if not text:
        return 0
    total = 0
    for char in text:
        total += _ARIAL_18PX_WIDTHS.get(char, 10)
    return total


def calculate_meta_pixel_width(text: str) -> int:
    """Calculate exact pixel width of description text using Arial 13px font metric."""
    if not text:
        return 0
    total = 0
    for char in text:
        total += _ARIAL_13PX_WIDTHS.get(char, 7)
    return total


def evaluate_title_pixel_status(text: str) -> Tuple[int, str]:
    """Returns (pixel_width, 'missing' or 'measured'). Width is not a compliance grade."""
    if not text or not text.strip():
        return 0, "missing"
    return calculate_title_pixel_width(text.strip()), "measured"


def evaluate_meta_pixel_status(text: str) -> Tuple[int, str]:
    """Returns (pixel_width, 'missing' or 'measured'). Width is not a compliance grade."""
    if not text or not text.strip():
        return 0, "missing"
    return calculate_meta_pixel_width(text.strip()), "measured"
