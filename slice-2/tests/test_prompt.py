from editor.render.fabrics import get_fabric
from editor.render.prompt import build_render_prompt

from indumentaria.dsl.examples import build_peacoat


def test_prompt_carries_dsl_semantics():
    p = build_render_prompt(build_peacoat(), get_fabric("lana_melton"), "navy")
    low = p.lower()
    assert "notch lapel" in low
    assert "double breasted" in low
    assert "4 buttons total in 2 vertical columns" in low
    assert "welt" in low
    assert "set in sleeves" in low
    assert "wide dropped fit" in low
    assert "long length" in low
    assert "navy" in low
    assert "wool" in low  # composición de la tela
    assert "laid flat" in low
    assert "white background" in low
    assert "no human body" in low


def test_prompt_is_single_string():
    p = build_render_prompt(build_peacoat(), get_fabric("denim"), "indigo")
    assert isinstance(p, str) and p.endswith(".")
