import pytest
from pydantic import ValidationError

from indumentaria.dsl.materials import BOM, BOMRow


def test_required_fields_only():
    row = BOMRow(category="Tela", description="100% lana")
    assert row.gsm is None and row.pantone_code is None


def test_missing_description_rejected():
    with pytest.raises(ValidationError):
        BOMRow(category="Tela")


def test_known_category_not_custom():
    assert BOMRow(category="Tela", description="lana").category_is_custom is False


def test_custom_category_flagged():
    assert BOMRow(category="Cordonería", description="x").category_is_custom is True


def test_bom_holds_rows():
    bom = BOM(rows=[BOMRow(category="Avío", description="botón", quantity=6)])
    assert bom.rows[0].quantity == 6
