from typing import get_args

from editor.detect import schema

from indumentaria.dsl import vocab


def test_literals_are_subset_of_vocab():
    # Anti-drift: si vocab cambia, este test obliga a actualizar los Literals.
    assert set(get_args(schema.CollarSubtype)) <= vocab.COLLAR_SUBTYPES
    assert set(get_args(schema.ClosureSubtype)) <= vocab.CLOSURE_SUBTYPES
    assert set(get_args(schema.SleeveSubtype)) <= vocab.SLEEVE_SUBTYPES
    assert set(get_args(schema.SleeveFit)) <= vocab.SLEEVE_FITS
    assert set(get_args(schema.PocketSubtype)) <= vocab.POCKET_SUBTYPES
    assert set(get_args(schema.PocketPlacement)) <= vocab.POCKET_PLACEMENTS
    assert set(get_args(schema.HemSubtype)) <= vocab.HEM_SUBTYPES


def test_to_coat_maps_components():
    d = schema.DetectedGarment(
        name="Mi saco", silhouette="oversized_cropped",
        collar=schema.DetectedCollar(subtype="notch_lapel", lapel_width_cm=8.0),
        closure=schema.DetectedClosure(subtype="double_breasted", button_count=4, button_rows=2),
        sleeve=schema.DetectedSleeve(subtype="set_in", fit="wide_dropped", length="long"),
        pockets=schema.DetectedPocket(subtype="welt", placement="hip", count=2),
        hem=schema.DetectedHem(subtype="straight"),
    )
    coat = schema.to_coat(
        d, "g1", "/garment-assets/g1/flat.svg", "/garment-assets/g1/reference.png"
    )
    assert coat.garment_id == "g1"
    assert coat.name == "Mi saco"
    assert coat.flat.front == "/garment-assets/g1/flat.svg"
    assert coat.reference_image == "/garment-assets/g1/reference.png"
    kinds = {c.kind for c in coat.components}
    assert kinds == {"collar", "closure", "sleeve", "pocket", "hem"}
    assert coat.measurements.poms  # tiene medidas placeholder
    assert coat.silhouette == "oversized_cropped"


def test_to_coat_skips_absent_components():
    d = schema.DetectedGarment(name="Liso", silhouette="regular",
                               collar=schema.DetectedCollar(subtype="band"))
    coat = schema.to_coat(d, "g2", "/x/f.svg", "/x/r.png")
    assert {c.kind for c in coat.components} == {"collar"}
