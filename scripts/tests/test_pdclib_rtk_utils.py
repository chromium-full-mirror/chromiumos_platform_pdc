# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=import-modules-only,import-error

"""Test pdclib.rtk_utils"""

from pathlib import Path
from typing import Union

from pdclib.common import UsbVidPid
from pdclib.rtk_constants import RtkDebugAccyGpioPolarity
from pdclib.rtk_constants import RtkI2cBusVoltage
from pdclib.rtk_constants import RtkPortUsed
from pdclib.rtk_utils import RtkFileSizeError
from pdclib.rtk_utils import RtkFwBinary
from pdclib.rtk_utils import RtkFwVersion
import pytest


def get_test_file_path(filename: Union[Path | str]) -> Path:
    """Return an absolute path to the given file in the test_files/ dir"""
    return Path(__file__).parent.resolve() / "test_files" / filename


def test_rtkfwversion():
    v = RtkFwVersion(10, 20, 30)

    assert str(v) == "10.20.30"


def test_rtkfwbinary_file_bad_length():
    with pytest.raises(RtkFileSizeError):
        RtkFwBinary(get_test_file_path("bad_size.bin"))


def test_rtkfwbinary_crc_validate():
    fw = RtkFwBinary(
        get_test_file_path(
            "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
        )
    )

    assert fw.verify_crc32()


def test_rtkfwbinary_crc_update():
    # This FW has a faulty CRC32
    fw = RtkFwBinary(
        get_test_file_path(
            "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3__bad_crc.bin"
        )
    )

    assert not fw.verify_crc32()

    # Correct the CRC32
    fw.set_file_crc32()

    assert fw.verify_crc32()


def test_rtkfwbinary_check_config():
    fw = RtkFwBinary(
        get_test_file_path(
            "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
        )
    )

    assert fw.get_project_name() == "GOOG0H00"
    assert fw.get_fw_version() == RtkFwVersion(0, 44, 3)
    assert fw.get_vid_pid() == UsbVidPid(0x18D1, 0x5075)
    assert fw.get_port_used() == RtkPortUsed.PORTA_ONLY
    assert (
        fw.get_debug_accy_gpio_polarity()
        == RtkDebugAccyGpioPolarity.ACTIVE_HIGH
    )

    assert fw.get_i2c_voltage_pmc() == RtkI2cBusVoltage.LEVEL_1V8
    assert fw.get_i2c_voltage_retimer() == RtkI2cBusVoltage.LEVEL_1V8
    assert fw.get_i2c_voltage_smbus() == RtkI2cBusVoltage.LEVEL_3V3

    assert fw.get_pmc_i2c_addrs() == (0x68, 0x68)
    assert fw.get_bbr_i2c_addrs() == (0x56, 0x40)
