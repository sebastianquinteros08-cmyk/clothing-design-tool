from editor.render.fabrics import Fabric, get_fabric, load_fabrics


def test_load_fabrics_returns_presets():
    fabrics = load_fabrics()
    assert len(fabrics) >= 4
    assert all(isinstance(f, Fabric) for f in fabrics)
    ids = {f.id for f in fabrics}
    assert "lana_melton" in ids


def test_fabric_swatch_url_is_under_assets():
    f = get_fabric("lana_melton")
    assert f is not None
    assert f.swatch_url == "/assets/fabrics/lana_melton/swatch.png"
    assert f.composition  # no vacío


def test_get_fabric_unknown_returns_none():
    assert get_fabric("no_existe") is None
