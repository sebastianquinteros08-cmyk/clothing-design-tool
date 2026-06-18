from indumentaria.dsl.assets import Annotation, FlatRef, PatternRef


def test_flatref_front_only():
    fr = FlatRef(front="slice-1/work/x/flat.svg")
    assert fr.back is None
    assert fr.annotations == []


def test_flatref_with_annotation_links_pom():
    fr = FlatRef(
        front="a.svg",
        back="b.svg",
        annotations=[Annotation(marker_id="m1", pom_code="A", x=10.0, y=20.0)],
    )
    assert fr.annotations[0].pom_code == "A"
    assert fr.back == "b.svg"


def test_patternref_pointer_only():
    pr = PatternRef(note="contramuestra")
    assert pr.path is None
