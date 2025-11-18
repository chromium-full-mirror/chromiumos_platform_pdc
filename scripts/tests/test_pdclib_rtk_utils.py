# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=import-modules-only,import-error

"""Test pdclib.rtk_utils"""

from pathlib import Path
from typing import Union

from pdclib.common import UsbVidPid
from pdclib.pdo import PDO
from pdclib.pdo import PDORole
from pdclib.rtk_constants import RtkChipType
from pdclib.rtk_constants import RtkDebugAccyGpioPolarity
from pdclib.rtk_constants import RtkI2cBusVoltage
from pdclib.rtk_constants import RtkPortUsed
from pdclib.rtk_utils import RtkConfigFragment
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


def test_rtkfwbinary_check_version():
    fw = RtkFwBinary(
        get_test_file_path(
            "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
        )
    )

    assert fw.get_fw_version() == RtkFwVersion(0, 44, 3)


def test_rtkfwbinary_check_base_fw_hash():
    fw = RtkFwBinary(
        get_test_file_path(
            "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
        )
    )

    assert (
        fw.get_base_firmware_hash()
        == "d209ee514901933893977dd6891eb892643db316"
    )


@pytest.mark.parametrize(
    "filepath",
    [
        # Each of these has the same config data. The first is a full FW bundle,
        # the second is a config fragment. `RtkConfigFragment.from_file()` is
        # able to parse both formats.
        pytest.param(
            get_test_file_path(
                "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
            ),
            id="FromFW",
        ),
        pytest.param(
            get_test_file_path("ocelotrvp-GOOG0H00-config.bin"),
            id="FromConfigFragment",
        ),
    ],
)
def test_rtkconfigfragment_from_file(filepath: Path):
    config = RtkConfigFragment.from_file(filepath)

    assert config.get_project_name() == "GOOG0H00"
    assert config.get_vid_pid() == UsbVidPid(0x18D1, 0x5075)
    assert config.get_port_used() == RtkPortUsed.PORTA_ONLY
    assert (
        config.get_debug_accy_gpio_polarity()
        == RtkDebugAccyGpioPolarity.ACTIVE_HIGH
    )

    assert config.get_i2c_voltage_pmc() == RtkI2cBusVoltage.LEVEL_1V8
    assert config.get_i2c_voltage_retimer() == RtkI2cBusVoltage.LEVEL_1V8
    assert config.get_i2c_voltage_smbus() == RtkI2cBusVoltage.LEVEL_3V3

    assert config.get_pmc_i2c_addrs() == (0x68, 0x68)
    assert config.get_bbr_i2c_addrs() == (0x56, 0x40)

    assert config.get_pdos(PDORole.SINK, "A") == [
        PDO.parse_pdo(0x2601912C, PDORole.SINK)
    ]
    assert config.get_pdos(PDORole.SINK, "B") == [
        PDO.parse_pdo(0x2601912C, PDORole.SINK)
    ]
    assert config.get_pdos(PDORole.SOURCE, "A") == [
        PDO.parse_pdo(0x00019096, PDORole.SOURCE)
    ]
    assert config.get_pdos(PDORole.SOURCE, "B") == [
        PDO.parse_pdo(0x37119096, PDORole.SOURCE)
    ]

    assert (
        config.get_config_hash() == "0b200289086f713fc175b32ff2f11fce6148c690"
    )


@pytest.mark.parametrize(
    "filepath,expected",
    [
        pytest.param(
            get_test_file_path(
                "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
            ),
            RtkChipType.RTS545X,
            id="RTS545X",
        ),
        pytest.param(
            get_test_file_path("RTS5453P-VB_Google_V0.44_20251001.bin"),
            RtkChipType.RTS545X_VB,
            id="RTS545X_VB",
        ),
    ],
)
def test_rtkfwbinary_get_chip_type(filepath: Path, expected: RtkChipType):
    fw = RtkFwBinary(filepath)

    assert fw.get_chip_type() == expected


@pytest.mark.parametrize(
    "filepath",
    [
        pytest.param(
            get_test_file_path(
                "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
            ),
            id="RTS545X",
        ),
        pytest.param(
            get_test_file_path("RTS5453P-VB_Google_V0.44_20251001.bin"),
            id="RTS545X_VB",
        ),
    ],
)
def test_rtkfwbinary_get_i2c_voltage_level(filepath: Path):
    fw = RtkFwBinary(filepath)

    # Both FWs have 3.3V SMbus levels but the different chip_types represent
    # the voltage levels differently. Ensure both types decode correctly.
    assert fw.get_i2c_voltage_smbus() == RtkI2cBusVoltage.LEVEL_3V3
