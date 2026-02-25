# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=import-modules-only,import-error

"""Test user script rtk_fw_config.py"""

from pathlib import Path
import tempfile

import pdclib.rtk_utils
import pytest
import rtk_fw_config
from tests.common import get_test_file_path


def test__bad_args():
    """Invalid CLI arg counts"""

    with pytest.raises(SystemExit):
        rtk_fw_config.main([])

    with pytest.raises(SystemExit):
        rtk_fw_config.main(None)


#
# rtk_fw_config show
#


def test_show_config__bad_args():
    """Invalid CLI arg counts"""

    with pytest.raises(SystemExit):
        rtk_fw_config.main(["show"])

    with pytest.raises(SystemExit):
        rtk_fw_config.main(["show", "-i"])


def test_show_config__missing_file():
    """Input image file does not exist"""

    with pytest.raises(FileNotFoundError):
        rtk_fw_config.main(
            ["show", "-i", str(get_test_file_path("non-existent"))]
        )


@pytest.mark.parametrize(
    "filepath",
    [
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
def test_show_config__success(filepath: Path):
    """Successfully process a full FW binary"""

    assert 0 == rtk_fw_config.main(
        [
            "show",
            "-i",
            str(filepath),
        ]
    )


#
# rtk_fw_config extract
#


def test_extract_config__bad_args():
    """Invalid CLI arg counts"""

    with pytest.raises(SystemExit):
        rtk_fw_config.main(["extract"])

    with pytest.raises(SystemExit):
        rtk_fw_config.main(["extract", "-i"])

    with pytest.raises(SystemExit):
        rtk_fw_config.main(["extract", "-i", "file"])

    with pytest.raises(SystemExit):
        rtk_fw_config.main(["extract", "-i", "file", "-o"])


def test_extract_config__missing_file():
    """Input image file does not exist"""

    with (
        pytest.raises(FileNotFoundError),
        tempfile.TemporaryDirectory() as tmpdir,
    ):
        rtk_fw_config.main(
            [
                "extract",
                "-i",
                str(get_test_file_path("non-existent")),
                "-o",
                str(Path(tmpdir) / "output_config.bin"),
            ]
        )


def test_extract_config__success():
    """Successful path. Verify the extracted config file matches original"""

    with tempfile.TemporaryDirectory() as tmpdir:
        input_fw_path = get_test_file_path(
            "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
        )
        output_config_path = Path(tmpdir) / "output_config.bin"

        rtk_fw_config.main(
            [
                "extract",
                "-i",
                str(input_fw_path),
                "-o",
                str(output_config_path),
            ]
        )

        input_fw = pdclib.rtk_utils.RtkFwBinary(input_fw_path)
        output_config = pdclib.rtk_utils.RtkConfigFragment(output_config_path)

        assert input_fw.get_config_hash() == output_config.get_config_hash()


#
# rtk_fw_config merge
#


def test_merge_config__bad_args():
    """Invalid CLI arg counts"""

    with pytest.raises(SystemExit):
        rtk_fw_config.main(["merge"])

    with pytest.raises(SystemExit):
        rtk_fw_config.main(["merge", "-i"])

    with pytest.raises(SystemExit):
        rtk_fw_config.main(["merge", "-i", "file"])

    with pytest.raises(SystemExit):
        rtk_fw_config.main(["merge", "-i", "file", "-c", "file"])

    with pytest.raises(SystemExit):
        rtk_fw_config.main(["merge", "-i", "file", "-c", "file", "-o"])


def test_merge_config__missing_file():
    """Input image file or input config file does not exist"""

    with (
        pytest.raises(FileNotFoundError),
        tempfile.TemporaryDirectory() as tmpdir,
    ):
        rtk_fw_config.main(
            [
                "merge",
                "-i",
                str(get_test_file_path("non-existent")),
                "-c",
                str(get_test_file_path("non-existent")),
                "-o",
                str(Path(tmpdir) / "output_config.bin"),
            ]
        )

    with (
        pytest.raises(FileNotFoundError),
        tempfile.TemporaryDirectory() as tmpdir,
    ):
        rtk_fw_config.main(
            [
                "merge",
                "-i",
                str(get_test_file_path("rts5453_v0.45.4.bin")),
                "-c",
                str(get_test_file_path("non-existent")),
                "-o",
                str(Path(tmpdir) / "output_config.bin"),
            ]
        )


def test_merge_config__success():
    """Successful path. New image has correct base FW and config section"""

    with tempfile.TemporaryDirectory() as tmpdir:
        input_base_fw_path = get_test_file_path("rts5453_v0.45.4.bin")
        input_config_path = get_test_file_path(
            "ocelotrvp-GOOG0H00-config_v4.bin"
        )
        output_path = Path(tmpdir) / "output_fw.bin"

        rtk_fw_config.main(
            [
                "merge",
                "-i",
                str(input_base_fw_path),
                "-c",
                str(input_config_path),
                "-o",
                str(output_path),
            ]
        )

        input_base_fw = pdclib.rtk_utils.RtkFwBinary(input_base_fw_path)
        input_config = pdclib.rtk_utils.RtkConfigFragment(input_config_path)
        output_fw = pdclib.rtk_utils.RtkFwBinary(output_path)

        # Compare config sections, ignoring preserved sections
        assert output_fw.compare_configs(input_config)

        # Compare base FW
        assert (
            output_fw.get_base_firmware_hash()
            == input_base_fw.get_base_firmware_hash()
        )

        # Ensure the CRC32 was updated upon export
        assert output_fw.verify_crc32()
