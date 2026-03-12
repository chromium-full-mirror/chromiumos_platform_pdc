# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=import-modules-only,import-error

"""Test the files in firmware/realtek"""

from pathlib import Path
import re

import pdclib.common
from pdclib.rtk_constants import RtkChipType
from pdclib.rtk_utils import RtkFwBinary
from pdclib.rtk_utils import RtkFwVersion
import pytest
from tests.common import get_repo_base_path


def get_rtk_fw_dir() -> Path:
    """Gets the path to platform/pdc/firmware/realtek"""
    return get_repo_base_path() / "firmware" / "realtek"


FOR_ALL_RTK_FW = pytest.mark.parametrize(
    ("filepath", "chip_type"),
    [
        # RTS545xP (non-VB) firmware dir
        *[
            pytest.param(p.resolve(), RtkChipType.RTS545X, id=p.name)
            for p in (get_rtk_fw_dir() / "rts5453").iterdir()
        ],
        # RTS545xP-VB firmware dir
        *[
            pytest.param(p.resolve(), RtkChipType.RTS545X_VB, id=p.name)
            for p in (get_rtk_fw_dir() / "rts5453vb").iterdir()
        ],
    ],
)


@FOR_ALL_RTK_FW
def test_rtk_base_firmware(filepath: Path, chip_type: RtkChipType):
    """Run basic integrity and config checks against each base FW file"""

    # Check naming scheme
    try:
        matches = re.search(
            r"^([a-z0-9]+)_v(\d+)\.(\d+)\.(\d+)\.bin$", filepath.name
        )

        assert matches

        chip_type_name = {
            RtkChipType.RTS545X_VB: "rts5453vb",
            RtkChipType.RTS545X: "rts5453",
        }

        # Ensure filename uses the correct chip name
        assert (
            matches.group(1) == chip_type_name[chip_type]
        ), "Chip name in filename incorrect"

        filename_ver = RtkFwVersion(
            int(matches.group(2)), int(matches.group(3)), int(matches.group(4))
        )

    except (IndexError, AssertionError) as e:
        # Regex didn't fully match
        raise AssertionError(f"Filename {filepath} is malformed") from e

    fw = RtkFwBinary(filepath)

    assert (
        fw.get_fw_version() == filename_ver
    ), "Filename version does not match actual version"
    assert (
        fw.get_chip_type() == chip_type
    ), "Expected chip type does not match actual binary"
    assert fw.verify_crc32(), "File has invalid CRC32 checksum"


@pytest.fixture(scope="session")
def rtk_signing():
    """Helper fixture for importing the optional pdclib_private module

    If this module is not available (e.g. public checkout), these tests will be
    skipped.
    """
    try:
        pdclib.common.add_pdclib_private()
        import pdclib_private.rtk_signing

        return pdclib_private.rtk_signing
    except (RuntimeError, ImportError):
        pytest.skip("No pdclib_private module. Requires internal checkout.")


@pytest.fixture(scope="session")
def signing_scheme_override_list() -> set:
    base_dir = get_repo_base_path()
    override_list = (
        get_repo_base_path()
        / "scripts"
        / "tests"
        / "rtk_signing_scheme_override.txt"
    )
    allowlist = set()

    with open(override_list, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or line.strip() == "":
                continue
            p = base_dir / line.strip()
            if not p.exists():
                pytest.fail(
                    f"'{override_list}' references a non-existent file '{p}'"
                )
            allowlist.add(p.resolve())

    return allowlist


@FOR_ALL_RTK_FW
# pylint: disable=unused-argument,redefined-outer-name
def test_rtk_base_firmware_signature(
    filepath: Path,
    chip_type: RtkChipType,
    rtk_signing,
    signing_scheme_override_list,
):
    scheme = (
        rtk_signing.RtkSigningScheme.SIGNING_FULL
        if filepath in signing_scheme_override_list
        else rtk_signing.RtkSigningScheme.SIGNING_FW_ONLY
    )
    rtk_signing.check_signature(filepath.read_bytes(), scheme)
