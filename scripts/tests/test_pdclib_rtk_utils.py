# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=import-modules-only,import-error

"""Test pdclib.rtk_utils"""

import os
from pathlib import Path
import tempfile

from pdclib.common import UsbVidPid
from pdclib.pdo import PDO
from pdclib.pdo import PDORole
from pdclib.rtk_constants import RtkChipType
from pdclib.rtk_constants import RtkConfigOffset
from pdclib.rtk_constants import RtkDebugAccyGpioPolarity
from pdclib.rtk_constants import RtkI2cBusVoltage
from pdclib.rtk_constants import RtkPortUsed
from pdclib.rtk_constants import RtkRetimerConfig
from pdclib.rtk_utils import fw_or_config_from_file
from pdclib.rtk_utils import print_config
from pdclib.rtk_utils import RtkConfigFragment
from pdclib.rtk_utils import RtkFileSizeError
from pdclib.rtk_utils import RtkFwBinary
from pdclib.rtk_utils import RtkFwVersion
import pytest
from tests.common import get_test_file_path


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


def test_rtkfwbinary_fragment_config_mismatch():
    fw = RtkFwBinary(
        get_test_file_path(
            "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
        )
    )

    fw_conf = RtkConfigFragment(
        get_test_file_path("ocelotrvp-GOOG0H00-config_v4.bin")
    )

    with pytest.raises(ValueError):
        fw.set_config(fw_conf)


def test_rtkfwbinary_bin_config_mismatch():
    fw = RtkFwBinary(
        get_test_file_path(
            "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
        )
    )

    fw_bin = RtkFwBinary(get_test_file_path("rts5453_v0.45.4.bin"))

    with pytest.raises(ValueError):
        fw.set_config(fw_bin)


def test_rtkfwbinary_set_config():
    fw = RtkFwBinary(get_test_file_path("rts5453_v0.45.4.bin"))

    fw_conf = RtkConfigFragment(
        get_test_file_path("ocelotrvp-GOOG0H00-config_v4.bin")
    )

    assert fw.get_project_name() != fw_conf.get_project_name()

    fw.set_config(fw_conf)

    assert fw.get_project_name() == fw_conf.get_project_name()


def test_rtkfwbinary_export_fw_binary():
    fw = RtkFwBinary(
        get_test_file_path(
            "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
        )
    )

    hash_fw = fw.get_base_firmware_hash()
    hash_config = fw.get_config_hash()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "out.bin"
        fw.export_fw_binary(output_file)

        assert output_file.exists()

        # Read the outputted firmware back in and check its hashes against the
        # original
        fw_out = RtkFwBinary(output_file)
        assert fw_out.get_base_firmware_hash() == hash_fw
        assert fw_out.get_config_hash() == hash_config


def test_rtkfwbinary_export_config_section():
    fw = RtkFwBinary(
        get_test_file_path(
            "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
        )
    )

    hash_config = fw.get_config_hash()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "out.bin"
        fw.export_config_section(output_file)

        assert output_file.exists()

        # Read the outputted config back in and check its hashes against the
        # original
        config_out = RtkConfigFragment(output_file)
        assert config_out.get_config_hash() == hash_config


def test_rtkfwbinary_export_fw_binary_malformed():
    fw = RtkFwBinary(
        get_test_file_path(
            "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
        )
    )

    # Add an extra unexpected byte
    fw.fw_bin.append(0x00)

    with pytest.raises(RtkFileSizeError):
        fw.export_fw_binary(Path(os.devnull))


@pytest.mark.parametrize(
    "filepath",
    [
        # Each of these has the same config data. The first is a full FW bundle,
        # the second is a config fragment.
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
def test_fw_or_config_from_file(filepath: Path):
    binary = fw_or_config_from_file(filepath)

    assert len(binary.get_config()) == RtkConfigOffset.CONFIG_RANGE_LENGTH

    assert binary.get_project_name() == "GOOG0H00"
    assert binary.get_vid_pid() == UsbVidPid(0x18D1, 0x5075)
    assert binary.get_port_used() == RtkPortUsed.PORTA_ONLY
    assert (
        binary.get_debug_accy_gpio_polarity()
        == RtkDebugAccyGpioPolarity.ACTIVE_HIGH
    )

    assert binary.get_config_version() == 3

    assert binary.get_i2c_voltage_pmc() == RtkI2cBusVoltage.LEVEL_1V8
    assert binary.get_i2c_voltage_retimer() == RtkI2cBusVoltage.LEVEL_1V8
    assert binary.get_i2c_voltage_smbus() == RtkI2cBusVoltage.LEVEL_3V3

    assert binary.get_pmc_i2c_addrs() == (0x68, 0x68)
    assert binary.get_bbr_i2c_addrs() == (0x56, 0x40)

    assert binary.get_pdos(PDORole.SINK, "A") == [
        PDO.parse_pdo(0x2601912C, PDORole.SINK)
    ]
    assert binary.get_pdos(PDORole.SINK, "B") == [
        PDO.parse_pdo(0x2601912C, PDORole.SINK)
    ]
    assert binary.get_pdos(PDORole.SOURCE, "A") == [
        PDO.parse_pdo(0x00019096, PDORole.SOURCE)
    ]
    assert binary.get_pdos(PDORole.SOURCE, "B") == [
        PDO.parse_pdo(0x37119096, PDORole.SOURCE)
    ]

    assert binary.get_src_max_pdp("A") == 15
    assert binary.get_src_max_pdp("B") == 15

    assert binary.get_svids("A") == [0x8087, 0xFF01]  # TBT, DP
    assert binary.get_svids("B") == [0xFF01]  # DP

    assert binary.get_port_sbumux_config("A") == RtkRetimerConfig.RETIMER_HBR
    assert binary.get_port_sbumux_config("B") == RtkRetimerConfig.RETIMER_TI

    assert (
        binary.get_config_hash() == "0b200289086f713fc175b32ff2f11fce6148c690"
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


@pytest.mark.parametrize(
    ("binary", "expected_text"),
    [
        pytest.param(
            RtkFwBinary(
                get_test_file_path(
                    "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
                )
            ),
            get_test_file_path(
                "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3_config.txt"
            ).read_text(),
            id="FromFW",
        ),
        pytest.param(
            RtkFwBinary(
                get_test_file_path(
                    "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3"
                    "__bad_crc.bin"
                )
            ),
            get_test_file_path(
                "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3"
                "__bad_crc_config.txt"
            ).read_text(),
            id="FromFW_BadCRC32",
        ),
        pytest.param(
            RtkConfigFragment(
                get_test_file_path("ocelotrvp-GOOG0H00-config.bin")
            ),
            get_test_file_path(
                "ocelotrvp-GOOG0H00-config_config.txt"
            ).read_text(),
            id="FromConfigFragment",
        ),
    ],
)
def test_print_config(binary, expected_text: str):
    output = []

    print_config(binary, output_func=output.append)

    assert "\n".join(output).strip() == expected_text.strip()
