from indumentaria.dsl import vocab
from indumentaria.dsl.vocab import (
    BOM_CATEGORIES,
    CLOSURE_SUBTYPES,
    COLLAR_SUBTYPES,
    is_custom,
)


def test_is_custom_false_for_known():
    assert is_custom("notch_lapel", COLLAR_SUBTYPES) is False


def test_is_custom_true_for_unknown():
    assert is_custom("klingon_collar", COLLAR_SUBTYPES) is True


def test_vocab_contents():
    assert "double_breasted" in CLOSURE_SUBTYPES
    assert "Tela" in BOM_CATEGORIES


def test_all_vocab_sets_present_and_non_empty():
    names = [
        "COLLAR_SUBTYPES",
        "CLOSURE_SUBTYPES",
        "SLEEVE_SUBTYPES",
        "SLEEVE_FITS",
        "POCKET_SUBTYPES",
        "POCKET_PLACEMENTS",
        "HEM_SUBTYPES",
        "BOM_CATEGORIES",
    ]
    for name in names:
        s = getattr(vocab, name)
        assert isinstance(s, frozenset) and len(s) > 0
