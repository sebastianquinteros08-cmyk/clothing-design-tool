import pytest

from indumentaria.dsl.examples import build_peacoat
from indumentaria.dsl.garment import Coat


@pytest.fixture
def peacoat() -> Coat:
    return build_peacoat()
