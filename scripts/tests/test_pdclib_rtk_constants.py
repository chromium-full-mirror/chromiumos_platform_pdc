# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=import-modules-only,import-error

"""Test pdclib.rtk_constants"""

from pdclib.rtk_constants import RtkChipType
from pdclib.rtk_constants import RtkI2cBusVoltage
import pytest


def test_rtki2cbusvoltage_parse_from_config():
    # RTS545XP and RTS545XP-VB encode I2C voltages differently. Check each.

    assert (
        RtkI2cBusVoltage.parse_from_config(0, RtkChipType.RTS545X)
        == RtkI2cBusVoltage.LEVEL_1V8
    )
    assert (
        RtkI2cBusVoltage.parse_from_config(1, RtkChipType.RTS545X)
        == RtkI2cBusVoltage.LEVEL_3V3
    )

    assert (
        RtkI2cBusVoltage.parse_from_config(0, RtkChipType.RTS545X_VB)
        == RtkI2cBusVoltage.LEVEL_3V3
    )
    assert (
        RtkI2cBusVoltage.parse_from_config(1, RtkChipType.RTS545X_VB)
        == RtkI2cBusVoltage.LEVEL_1V8
    )

    with pytest.raises(ValueError):
        RtkI2cBusVoltage.parse_from_config(0, RtkChipType.UNKNOWN)

    with pytest.raises(KeyError):
        RtkI2cBusVoltage.parse_from_config(-1, RtkChipType.RTS545X)
