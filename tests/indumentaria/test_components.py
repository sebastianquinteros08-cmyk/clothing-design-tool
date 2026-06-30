import pytest
from pydantic import ValidationError

from indumentaria.dsl.components import Closure, Collar, Hem, Pocket, Sleeve


def test_known_subtype_not_custom():
    assert Collar(subtype="notch_lapel").subtype_is_custom is False


def test_unknown_subtype_is_accepted_and_flagged():
    c = Collar(subtype="klingon_collar")
    assert c.subtype == "klingon_collar"
    assert c.subtype_is_custom is True


def test_closure_fields():
    cl = Closure(subtype="double_breasted", button_count=4, button_rows=2)
    assert cl.button_count == 4
    assert cl.kind == "closure"
    assert cl.button_rows == 2


def test_negative_button_count_rejected():
    with pytest.raises(ValidationError):
        Closure(subtype="zip", button_count=-1)


def test_pocket_count_must_be_positive():
    with pytest.raises(ValidationError):
        Pocket(subtype="welt", placement="hip", count=0)


def test_sleeve_and_hem_defaults():
    s = Sleeve(subtype="set_in")
    assert s.fit == "regular" and s.length == "long"
    assert Hem(subtype="straight").kind == "hem"


def test_negative_button_rows_rejected():
    with pytest.raises(ValidationError):
        Closure(subtype="double_breasted", button_rows=-1)


def test_lapel_width_must_be_positive():
    with pytest.raises(ValidationError):
        Collar(subtype="notch_lapel", lapel_width_cm=0.0)


def test_component_id_is_unique_and_stable():
    from indumentaria.dsl.components import Collar

    a = Collar(subtype="notch_lapel")
    b = Collar(subtype="notch_lapel")
    assert a.component_id != b.component_id  # ids distintos por instancia
    # round-trip JSON preserva el id
    restored = Collar.model_validate_json(a.model_dump_json())
    assert restored.component_id == a.component_id


def test_component_id_can_be_set_explicitly():
    from indumentaria.dsl.components import Pocket

    p = Pocket(subtype="welt", component_id="fixed123")
    assert p.component_id == "fixed123"
