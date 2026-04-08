# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=import-modules-only,import-error

"""Test user script apfw.py"""

import json
from pathlib import Path

import apfw
import pytest
from tests.common import cbfs_test_images  # pylint: disable=unused-import


def test_bad_args():
    """Invalid CLI arg counts"""

    with pytest.raises(SystemExit):
        apfw.main([])

    with pytest.raises(SystemExit):
        apfw.main(None)


# pylint: disable=redefined-outer-name
def test_bad_file(cbfs_test_images: Path):
    assert 1 == apfw.main([str(cbfs_test_images / "non-existent.bin")])


def test_success_text(cbfs_test_images: Path, capsys):
    assert 0 == apfw.main([str(cbfs_test_images / "cbfs.bin")])

    captured = capsys.readouterr()
    lines = captured.out.splitlines()

    assert len(lines) == 8

    # FW versions
    assert lines[0] == "AP RO     : AP_RO-12345.0.0"
    assert lines[1] == "AP RW_A   : AP_RW_A-12345.0.0"
    assert lines[2] == "AP RW_B   : AP_RW_B-12345.0.0"
    assert lines[3] == "EC RW_A   : EC_RW_A-12345.0.0"
    assert lines[4] == "EC RW_B   : EC_RW_B-12345.0.0"

    # RTK line
    assert "rts5453_v0.45.4" in lines[6]
    assert "Hash File: 0.45.4 (None)" in lines[6]
    assert "SHA1: 93f390834c9cf6cd33bf872fd809cec7a315dd00" in lines[6]
    assert "Embedded: 0.45.4 (GOOG0000)" in lines[6]

    # TI line
    assert "tps6699x-GOOG0J30_00132002_TFU" in lines[7]
    assert "Hash File: 19.32.2 (GOOG0J30)" in lines[7]
    assert "SHA1: cd3ea8c879d83af093f42c4eb03e8ce7715d19b4" in lines[7]
    assert "Embedded: 19.32.2 (GOOG0J30)" in lines[7]


def test_success_json(cbfs_test_images: Path, capsys):
    assert 0 == apfw.main([str(cbfs_test_images / "cbfs.bin"), "-j"])

    expected_detected_fw_json = {
        "rts5453_v0.45.4": {
            "name": "rts5453_v0.45.4",
            "fw_binary": [0, 45, 4, "GOOG0000"],
            "hash_file": {"ver": [0, 45, 4], "config_name": None},
            "fw_binary_hash": "93f390834c9cf6cd33bf872fd809cec7a315dd00",
        },
        "tps6699x-GOOG0J30_00132002_TFU": {
            "name": "tps6699x-GOOG0J30_00132002_TFU",
            "fw_binary": [19, 32, 2, "GOOG0J30"],
            "hash_file": {"ver": [19, 32, 2], "config_name": "GOOG0J30"},
            "fw_binary_hash": "cd3ea8c879d83af093f42c4eb03e8ce7715d19b4",
        },
    }

    expected_ec_ap_fw_versions = {
        "AP RO": "AP_RO-12345.0.0",
        "AP RW_A": "AP_RW_A-12345.0.0",
        "AP RW_B": "AP_RW_B-12345.0.0",
        "EC RW_A": "EC_RW_A-12345.0.0",
        "EC RW_B": "EC_RW_B-12345.0.0",
    }

    output_json = json.loads(capsys.readouterr().out)

    assert output_json["detected_fw"] == expected_detected_fw_json
    assert output_json["ec_ap_fw"] == expected_ec_ap_fw_versions

    # This path changes due to temporary directories. Check only the file name.
    assert output_json["input_file"].endswith("cbfs.bin")
