"""Portable scientific scripts in Origin graph labels, without font-specific glyphs.

Origin rich text: https://docs.originlab.com/quick-help/insert-symbols-in-legend/
Only numeric script runs change; ordinary Unicode and explicit Origin markup survive.
"""

import re

_SCRIPTS = (
    (re.compile("[₀₁₂₃₄₅₆₇₈₉₊₋₌]+"), str.maketrans("₀₁₂₃₄₅₆₇₈₉₊₋₌", "0123456789+-="), "-"),
    (re.compile("[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼]+"), str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼", "0123456789+-="), "+"),
)


def origin_text(text: str) -> str:
    for pattern, translation, operator in _SCRIPTS:

        def convert(match, table=translation, op=operator):
            return "\\" + op + "(" + match.group().translate(table) + ")"

        text = pattern.sub(convert, text)
    return text
