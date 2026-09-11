from origin_agent.graph_text import origin_text


def test_scientific_unicode_is_portable_and_preserves_other_text():
    assert origin_text("K₂CrO₄ / mol dm⁻³; Fe³⁺") == r"K\-(2)CrO\-(4) / mol dm\+(-3); Fe\+(3+)"
    assert origin_text("¹³C, ₁₂₃ and ⁰⁻²") == r"\+(13)C, \-(123) and \+(0-2)"
    text = r"化学 Δλ / nm; R\+(2); line 1" + "\nline 2"
    assert origin_text(text) == text
    formatted = origin_text("K₂CrO₄ / mol dm⁻³")
    assert origin_text(formatted) == formatted
