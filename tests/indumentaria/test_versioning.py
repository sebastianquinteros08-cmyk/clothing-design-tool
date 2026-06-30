from datetime import datetime

import pytest
from pydantic import ValidationError

from indumentaria.dsl.operations import CreateGarment, SetMeasurement
from indumentaria.dsl.versioning import GarmentVersion, apply, create_initial


def test_create_initial_is_version_one(peacoat):
    v1 = create_initial(CreateGarment(garment=peacoat))
    assert v1.version == 1
    assert v1.snapshot == peacoat
    assert v1.garment_id == peacoat.garment_id
    assert isinstance(v1.created_at, datetime)
    assert isinstance(v1, GarmentVersion)
    assert v1.op_type == "create_garment"
    assert v1.op_id


def test_apply_increments_version_and_updates_snapshot(peacoat):
    v1 = create_initial(CreateGarment(garment=peacoat))
    op = SetMeasurement(pom_code="A", base_measurement=110.0, tol_plus=1.0, tol_minus=1.0)
    v2 = apply(op, v1)
    assert v2.version == 2
    assert next(p for p in v2.snapshot.measurements.poms if p.code == "A").base_measurement == 110.0


def test_apply_leaves_prior_snapshot_intact(peacoat):
    v1 = create_initial(CreateGarment(garment=peacoat))
    apply(SetMeasurement(pom_code="A", base_measurement=110.0, tol_plus=1.0, tol_minus=1.0), v1)
    assert next(p for p in v1.snapshot.measurements.poms if p.code == "A").base_measurement == 104.0


def test_garment_version_is_frozen(peacoat):
    v1 = create_initial(CreateGarment(garment=peacoat))
    with pytest.raises(ValidationError):
        v1.version = 99
