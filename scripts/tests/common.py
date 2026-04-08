# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common utilities for test code"""

from pathlib import Path

import pdclib.apfw_image
import pytest


def get_test_file_path(filename: Path | str) -> Path:
    """Return an absolute path to the given file in the test_files/ dir"""
    return Path(__file__).parent.resolve() / "test_files" / filename


def get_repo_base_path() -> Path:
    """Return an absolute path to the base directory of the platform/pdc repo"""
    return Path(__file__).parent.parent.parent.resolve()


@pytest.fixture(scope="session")
def cbfs_test_images(tmp_path_factory):
    """Fixture that creates test CBFS images

    Dynamically generate some CBFS binaries and include PDC FW images for
    testing purposes. Once this fixture is pulled in, the CBFS images persist
    for the whole test session and are not regenerated for each test.

    Currently creates:
      - "cbfs.bin", with:
        - rts5453_v0.45.4.{bin|hash}
          RTK 0.45.4 FW, project name "GOOG0000"
        - tps6699x-GOOG0J30_00132002_TFU.{bin|hash}
          TI 19.32.02 FW, project name "GOOG0J30"
        - AP RO, AP RW_A, AP RW_B, EC RW_A, EC RW_B FWID version strings

    The fixture returns a Path object pointing to the directory containing the
    above CBFS files. E.g. (cbfs_test_images / "cbfs.bin")
    """

    # Temp directory used as scratch space to create the CBFS images. This dir
    # will persist for the duration of the test session and is passed into the
    # test function.
    basepath = tmp_path_factory.mktemp("cbfs_test")

    def hash_file(
        path: Path, major: int, minor: int, patch: int, projname: bytes = None
    ):
        """Helper to create a hash file"""
        with open(path, "wb") as f:
            f.write(bytes([major, minor, patch]))
            if projname:
                f.write(projname)

    try:
        cbfstool = pdclib.apfw_image.CbfsTool()
    except FileNotFoundError:
        pytest.skip("No cbfstool available")

    # This fmap file is pre-generated and checked into source control. It can
    # be recreated with:
    #     `fmaptool cbfs/apfw_pdc_test.fmd cbfs/apfw_pdc_test.fmap`
    fmap_path = get_test_file_path("cbfs/apfw_pdc_test.fmap")

    # Create test CBFS filesystems and embed a TI and RTK PDC FW image+hash
    # to both FW_MAIN_A and FW_MAIN_B (there are two RW FW slots)
    hash_file_rtk_path = basepath / "hash_0.45.4.bin"
    hash_file_ti_path = basepath / "hash_132002_GOOG0J30.bin"
    cbfs_path = basepath / "cbfs.bin"

    hash_file(hash_file_rtk_path, 0, 45, 4)
    hash_file(hash_file_ti_path, 0x13, 0x20, 0x02, b"GOOG0J30")

    cbfstool.create(
        cbfs_path, ["COREBOOT", "FW_MAIN_A", "FW_MAIN_B"], fmap_path
    )

    for region in ("FW_MAIN_A", "FW_MAIN_B"):
        # RTK image and hash file
        cbfstool.add_file(
            cbfs_path,
            region,
            get_test_file_path("rts5453_v0.45.4.bin"),
            "rts5453_v0.45.4.bin",
        )
        cbfstool.add_file(
            cbfs_path,
            region,
            hash_file_rtk_path,
            "rts5453_v0.45.4.hash",
        )

        # TI image and hash file
        cbfstool.add_file(
            cbfs_path,
            region,
            get_test_file_path("tps6699x-GOOG0J30_00132002_TFU.bin"),
            "tps6699x-GOOG0J30_00132002_TFU.bin",
        )
        cbfstool.add_file(
            cbfs_path,
            region,
            hash_file_ti_path,
            "tps6699x-GOOG0J30_00132002_TFU.hash",
        )

    #
    # Add FWID strings for AP and EC images
    #

    # Arbitrary, but match the size of the RO_FRID, RW_FWID_A, RW_FWID_B
    # regions in `test_files/cbfs/apfw_pdc_test.fmd`
    FWID_LEN = 0x100

    def create_fwid_file(contents: bytes) -> Path:
        """Create a scratch file and write the FWID bytes to it"""
        if b"/" in contents or b"\x00" in contents:
            raise ValueError("FWID cannot contain / or NUL")

        f = basepath / f"{contents.decode('ascii')}.bin"
        f.write_bytes(contents.ljust(FWID_LEN, b"\x00"))
        return f

    ec_fwid_a_file = create_fwid_file(b"EC_RW_A-12345.0.0")
    ec_fwid_b_file = create_fwid_file(b"EC_RW_B-12345.0.0")
    ap_ro_fwid_file = create_fwid_file(b"AP_RO-12345.0.0")
    ap_rw_fwid_a_file = create_fwid_file(b"AP_RW_A-12345.0.0")
    ap_rw_fwid_b_file = create_fwid_file(b"AP_RW_B-12345.0.0")

    # EC FWIDs are files in FW_MAIN_A and FW_MAIN_B
    cbfstool.add_file(cbfs_path, "FW_MAIN_A", ec_fwid_a_file, "ecrw.version")
    cbfstool.add_file(cbfs_path, "FW_MAIN_B", ec_fwid_b_file, "ecrw.version")

    # AP FWIDs are raw regions (non-CBFS)
    cbfstool.write(cbfs_path, "RO_FRID", ap_ro_fwid_file)
    cbfstool.write(cbfs_path, "RW_FWID_A", ap_rw_fwid_a_file)
    cbfstool.write(cbfs_path, "RW_FWID_B", ap_rw_fwid_b_file)

    return basepath
