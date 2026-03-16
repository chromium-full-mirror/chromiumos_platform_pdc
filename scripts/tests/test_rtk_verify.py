# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=import-modules-only,import-error,redefined-outer-name

"""Test the rtk_verify.py script"""

import subprocess

import pdclib.common
import pytest
from tests.common import get_repo_base_path
from tests.common import get_test_file_path


@pytest.fixture
def rtk_verify_path():
    return get_repo_base_path() / "scripts" / "rtk_verify.py"


@pytest.fixture(autouse=True)
def check_pdclib_private():
    """Test importing pdclib_private. Skip test if unavailable"""
    try:
        pdclib.common.add_pdclib_private()
        import pdclib_private as _
    except (RuntimeError, ImportError):
        pytest.skip("No pdclib_private module. Requires internal checkout.")


def test_no_path(rtk_verify_path):
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.check_call([rtk_verify_path])


def test_bad_path(rtk_verify_path):
    with pytest.raises(subprocess.CalledProcessError):
        subprocess.check_call(
            [rtk_verify_path, get_test_file_path("non_existent.bin")]
        )


def test_bad_crc32(rtk_verify_path):
    with pytest.raises(subprocess.CalledProcessError):
        bad_crc_bin = (
            "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3__bad_crc.bin"
        )
        subprocess.check_call(
            [
                rtk_verify_path,
                get_test_file_path(bad_crc_bin),
                "--scheme",
                "fw",
            ]
        )


def test_bad_signature(rtk_verify_path):
    with pytest.raises(subprocess.CalledProcessError):
        test_bin = "ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin"
        subprocess.check_call(
            [
                rtk_verify_path,
                get_test_file_path(test_bin),
                "--scheme",
                "full",  # Wrong scheme for this image. Will fail check.
            ]
        )


@pytest.mark.parametrize(
    ("test_image_path", "scheme"),
    [
        ("ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin", "fw"),
        ("ocelotrvp-GOOG0H00-realtek-rts545x-firmware-0.44.3.bin", None),
        ("rts5453_v16.3.3_old_signing.bin", "full"),
    ],
)
def test_success(test_image_path, scheme, rtk_verify_path):
    cmd = [
        rtk_verify_path,
        get_test_file_path(test_image_path),
    ]

    if scheme:
        cmd.extend(["--scheme", scheme])

    subprocess.check_call(cmd)
