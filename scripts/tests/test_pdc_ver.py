# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=import-modules-only,import-error,redefined-outer-name

"""Test the pdc_ver.py script"""

import pdc_ver
import pytest
from tests.common import get_test_file_path


def test_no_args():
    """Test running without arguments fails (argparse will exit).

    Since argparse.parse_args() calls sys.exit() on error, we expect SystemExit.
    """
    with pytest.raises(SystemExit):
        pdc_ver.main([])


def test_non_existent_file(capsys):
    """Test running with non-existent file fails."""
    exit_code = pdc_ver.main([str(get_test_file_path("non_existent.bin"))])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "does not exist" in captured.err


def test_bad_size_file(capsys):
    """Test running with unrecognized file type fails."""
    exit_code = pdc_ver.main([str(get_test_file_path("bad_size.bin"))])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Could not autodetect image type" in captured.err


def test_ti_image_a(capsys):
    """Test running with TI image, type A"""
    exit_code = pdc_ver.main(
        [str(get_test_file_path("tps6699x-GOOG0J30_00132002_TFU.bin"))]
    )
    assert exit_code == 0
    captured = capsys.readouterr()

    assert "Image Type   : TI" in captured.out
    assert "Version      : 19.32.2" in captured.out
    assert "Project Name : GOOG0J30" in captured.out


def test_ti_image_b(capsys):
    """Test running with TI image, type B"""
    exit_code = pdc_ver.main(
        [str(get_test_file_path("tps6699xb-GOOG0b00_00160001_TFU.bin"))]
    )
    assert exit_code == 0
    captured = capsys.readouterr()

    assert "Image Type   : TI" in captured.out
    assert "Version      : 22.0.1" in captured.out
    assert "Project Name : GOOG0b00" in captured.out


def test_rtk_fw_image(capsys):
    """Test running with a RTK FW image."""
    exit_code = pdc_ver.main(
        [
            str(
                get_test_file_path(
                    "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
                )
            )
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()

    assert "Image Type   : Realtek (Full FW)" in captured.out
    assert "Version      : 0.44.3" in captured.out
    assert "Project Name : GOOG0H00" in captured.out


def test_rtk_fw_image_bad_crc32():
    """Test running with a RTK FW image with a bad CRC32"""
    with pytest.raises(RuntimeError) as excinfo:
        pdc_ver.main(
            [
                str(
                    get_test_file_path(
                        "ocelotrvp-GOOG0H00-realtek-rts545x-"
                        "firmware-0.44.3__bad_crc.bin"
                    )
                )
            ]
        )

        cause = excinfo.value.__cause__
        assert isinstance(cause, ValueError)
        assert "CRC32 invalid." in str(cause)


def test_rtk_cfg_image(capsys):
    """Test running with a RTK Config fragment."""
    exit_code = pdc_ver.main(
        [str(get_test_file_path("ocelotrvp-GOOG0H00-config.bin"))]
    )
    assert exit_code == 0
    captured = capsys.readouterr()

    assert "Image Type   : Realtek (Config Fragment)" in captured.out
    assert "Version      : x.x.3" in captured.out
    assert "Project Name : GOOG0H00" in captured.out
