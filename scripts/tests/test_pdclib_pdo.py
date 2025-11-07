# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=import-modules-only,import-error

"""Test pdclib.pdo"""

from pdclib.pdo import PDO
from pdclib.pdo import PDOAugmented
from pdclib.pdo import PDOBattery
from pdclib.pdo import PDOConstants
from pdclib.pdo import PDOFixed
from pdclib.pdo import PDOFixedFRSCurrent
from pdclib.pdo import PDOFixedPeakCurrent
from pdclib.pdo import PDORole
from pdclib.pdo import PDOType
from pdclib.pdo import PDOVariable
import pytest


def test_pdo_types():
    assert PDOType.FIX == 0
    assert PDOType.BAT == 1
    assert PDOType.VAR == 2
    assert PDOType.AUG == 3


def test_fixed_source_pdo_power_fields():
    raw_pdo = (
        PDOType.FIX << PDOConstants.PDO_TYPE_OFFSET
        | int(3000 / PDOConstants.PDO_CURRENT_UNITS_MA)
        << PDOConstants.PDO_FIXED_CURRENT_OFFSET
        | int(15000 / PDOConstants.PDO_VOLT_UNITS_MV)
        << PDOConstants.PDO_FIXED_VOLT_OFFSET
        | PDOFixedPeakCurrent.PEAK_150
        << PDOConstants.PDO_FIXED_PEAK_CURRENT_OFFSET
    )

    p = PDO.parse_pdo(
        raw_pdo,
        PDORole.SOURCE,
    )

    assert p.pdo_type == PDOType.FIX
    assert isinstance(p, PDOFixed)
    assert p.pdo == raw_pdo

    assert p.millivolts == 15000
    assert p.milliamps == 3000
    assert p.peak_current == PDOFixedPeakCurrent.PEAK_150
    assert p.watts == 45


def test_fixed_source_pdo_illegal_fields():
    # Only available in sink PDOs
    p = PDO.parse_pdo(
        PDOType.FIX << PDOConstants.PDO_TYPE_OFFSET, PDORole.SOURCE
    )

    with pytest.raises(ValueError):
        assert p.frs_current


@pytest.mark.parametrize(
    ("bitmask", "condition"),
    [
        pytest.param(
            PDOConstants.PDO_FIXED_EPR_CAPABLE,
            lambda p: p.epr_supported,
            id="PDOConstants.PDO_FIXED_EPR_CAPABLE",
        ),
        pytest.param(
            PDOConstants.PDO_FIXED_UNCHUNKED_EXT_MSG_CAPABLE,
            lambda p: p.unchunked_ext_msg_supported,
            id="PDOConstants.PDO_FIXED_UNCHUNKED_EXT_MSG_CAPABLE",
        ),
        pytest.param(
            PDOConstants.PDO_FIXED_DUAL_ROLE_DATA,
            lambda p: p.dualrole_data,
            id="PDOConstants.PDO_FIXED_DUAL_ROLE_DATA",
        ),
        pytest.param(
            PDOConstants.PDO_FIXED_COMM_CAPABLE,
            lambda p: p.comm_capable,
            id="PDOConstants.PDO_FIXED_COMM_CAPABLE",
        ),
        pytest.param(
            PDOConstants.PDO_FIXED_UNCONSTRAINED_POWER,
            lambda p: p.unconstrained_power,
            id="PDOConstants.PDO_FIXED_UNCONSTRAINED_POWER",
        ),
        pytest.param(
            PDOConstants.PDO_FIXED_SUSPEND_CAPABLE,
            lambda p: p.suspend_capable,
            id="PDOConstants.PDO_FIXED_SUSPEND_CAPABLE",
        ),
        pytest.param(
            PDOConstants.PDO_FIXED_DUALROLE_POWER,
            lambda p: p.dualrole_power,
            id="PDOConstants.PDO_FIXED_DUALROLE_POWER",
        ),
    ],
)
def test_fixed_source_pdo_bitfield(bitmask, condition):
    # Set the bit and see if it decodes properly.
    p = PDO.parse_pdo(
        PDOType.FIX << PDOConstants.PDO_TYPE_OFFSET | bitmask, PDORole.SOURCE
    )
    assert condition(p)

    # Do not set the bit and ensure the condition is False.
    p = PDO.parse_pdo(
        PDOType.FIX << PDOConstants.PDO_TYPE_OFFSET, PDORole.SOURCE
    )
    assert not condition(p)


def test_fixed_sink_pdo_power_fields():
    raw_pdo = (
        PDOType.FIX << PDOConstants.PDO_TYPE_OFFSET
        | int(3000 / PDOConstants.PDO_CURRENT_UNITS_MA)
        << PDOConstants.PDO_FIXED_CURRENT_OFFSET
        | int(15000 / PDOConstants.PDO_VOLT_UNITS_MV)
        << PDOConstants.PDO_FIXED_VOLT_OFFSET
        | PDOFixedFRSCurrent.FRS_V5_3A0
        << PDOConstants.PDO_FIXED_FRS_CURRENT_OFFSET
    )

    p = PDO.parse_pdo(
        raw_pdo,
        PDORole.SINK,
    )

    assert p.pdo_type == PDOType.FIX
    assert isinstance(p, PDOFixed)
    assert p.pdo == raw_pdo

    assert p.millivolts == 15000
    assert p.milliamps == 3000
    assert p.frs_current == PDOFixedFRSCurrent.FRS_V5_3A0
    assert p.watts == 45


def test_fixed_sink_pdo_illegal_fields():
    # These fields are only available in source PDOs
    p = PDO.parse_pdo(PDOType.FIX << PDOConstants.PDO_TYPE_OFFSET, PDORole.SINK)

    with pytest.raises(ValueError):
        assert p.epr_supported

    with pytest.raises(ValueError):
        assert p.unchunked_ext_msg_supported

    with pytest.raises(ValueError):
        assert p.peak_current


@pytest.mark.parametrize(
    ("bitmask", "condition"),
    [
        pytest.param(
            PDOConstants.PDO_FIXED_DUAL_ROLE_DATA,
            lambda p: p.dualrole_data,
            id="PDOConstants.PDO_FIXED_DUAL_ROLE_DATA",
        ),
        pytest.param(
            PDOConstants.PDO_FIXED_COMM_CAPABLE,
            lambda p: p.comm_capable,
            id="PDOConstants.PDO_FIXED_COMM_CAPABLE",
        ),
        pytest.param(
            PDOConstants.PDO_FIXED_UNCONSTRAINED_POWER,
            lambda p: p.unconstrained_power,
            id="PDOConstants.PDO_FIXED_UNCONSTRAINED_POWER",
        ),
        pytest.param(
            PDOConstants.PDO_FIXED_SUSPEND_CAPABLE,
            lambda p: p.suspend_capable,
            id="PDOConstants.PDO_FIXED_SUSPEND_CAPABLE",
        ),
        pytest.param(
            PDOConstants.PDO_FIXED_DUALROLE_POWER,
            lambda p: p.dualrole_power,
            id="PDOConstants.PDO_FIXED_DUALROLE_POWER",
        ),
    ],
)
def test_fixed_sink_pdo_bitfield(bitmask, condition):
    # Set the bit and see if it decodes properly.
    p = PDO.parse_pdo(
        PDOType.FIX << PDOConstants.PDO_TYPE_OFFSET | bitmask, PDORole.SOURCE
    )
    assert condition(p)

    # Do not set the bit and ensure the condition is False.
    p = PDO.parse_pdo(
        PDOType.FIX << PDOConstants.PDO_TYPE_OFFSET | 0, PDORole.SOURCE
    )
    assert not condition(p)


def test_bat_pdo():
    raw_pdo = (
        PDOType.BAT << PDOConstants.PDO_TYPE_OFFSET
        | int(5000 / PDOConstants.PDO_VOLT_UNITS_MV)
        << PDOConstants.PDO_BAT_MIN_VOLTAGE_OFFSET
        | int(20000 / PDOConstants.PDO_VOLT_UNITS_MV)
        << PDOConstants.PDO_BAT_MAX_VOLTAGE_OFFSET
        | int(45000 / PDOConstants.PDO_POWER_UNITS_MW)
        << PDOConstants.PDO_BAT_POWER_OFFSET
    )

    p = PDO.parse_pdo(raw_pdo, PDORole.SINK)

    assert p.pdo_type == PDOType.BAT
    assert isinstance(p, PDOBattery)
    assert p.pdo == raw_pdo

    assert p.millivolts_max == 20000
    assert p.millivolts_min == 5000
    assert p.milliwatts == 45000


def test_var_pdo():
    raw_pdo = (
        PDOType.VAR << PDOConstants.PDO_TYPE_OFFSET
        | int(5000 / PDOConstants.PDO_VOLT_UNITS_MV)
        << PDOConstants.PDO_VAR_MIN_VOLTAGE_OFFSET
        | int(20000 / PDOConstants.PDO_VOLT_UNITS_MV)
        << PDOConstants.PDO_VAR_MAX_VOLTAGE_OFFSET
        | int(3000 / PDOConstants.PDO_CURRENT_UNITS_MA)
        << PDOConstants.PDO_VAR_CURRENT_OFFSET
    )

    p = PDO.parse_pdo(raw_pdo, PDORole.SINK)

    assert p.pdo_type == PDOType.VAR
    assert isinstance(p, PDOVariable)
    assert p.pdo == raw_pdo

    assert p.millivolts_max == 20000
    assert p.millivolts_min == 5000
    assert p.milliamps == 3000


def test_aug_pdo():
    raw_pdo = PDOType.AUG << PDOConstants.PDO_TYPE_OFFSET
    p = PDO.parse_pdo(raw_pdo, PDORole.SINK)

    assert p.pdo_type == PDOType.AUG
    assert isinstance(p, PDOAugmented)
    assert p.pdo == raw_pdo
