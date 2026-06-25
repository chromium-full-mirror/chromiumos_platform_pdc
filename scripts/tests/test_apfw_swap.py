# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=import-modules-only,import-error

"""Test swapping PDC FW in AP FW image"""

from pathlib import Path
import shutil

import apfw
from pdclib.apfw_image import CbfsTool
from pdclib.apfw_image import search_pdc_fw_images
import pytest
from tests.common import cbfs_test_images  # pylint: disable=unused-import
from tests.common import get_test_file_path


# pylint: disable=redefined-outer-name
@pytest.mark.parametrize(
    "fw_slot,orig_fw_info,new_fw_path,new_fw_info",
    [
        pytest.param(
            "rts5453_GOOG0000",
            {
                "fw_binary": (0, 45, 4, "GOOG0000"),
                "hash_file": {
                    "ver": (0, 45, 4),
                    "config_name": None,
                },
            },
            get_test_file_path("rts5453_v0.44.3.bin"),
            {
                "fw_binary": (0, 44, 3, "GOOG0000"),
                "hash_file": {
                    "ver": (0, 44, 3),
                    "config_name": None,
                },
            },
            id="RTK",
        ),
        pytest.param(
            "tps6699x_GOOG0J00",
            {
                "fw_binary": (19, 32, 2, "GOOG0J30"),
                "hash_file": {
                    "ver": (19, 32, 2),
                    "config_name": "GOOG0J30",
                },
            },
            get_test_file_path("tps6699x-GOOG0J30_00132008_TFU.bin"),
            {
                "fw_binary": (19, 32, 8, "GOOG0J30"),
                "hash_file": {
                    "ver": (19, 32, 8),
                    "config_name": "GOOG0J30",
                },
            },
            id="TI",
        ),
    ],
)
def test_swap_rtk_fw(
    cbfs_test_images: Path,
    tmp_path: Path,
    fw_slot: str,
    orig_fw_info: dict,
    new_fw_path: Path,
    new_fw_info: dict,
):
    """Test swapping RTK firmware in CBFS"""
    cbfs_bin = cbfs_test_images / "cbfs.bin"
    temp_cbfs = tmp_path / "cbfs_swapped.bin"
    shutil.copy(cbfs_bin, temp_cbfs)

    # Before swap, verify original FW in both regions
    cbfstool = CbfsTool()

    for region in ("FW_MAIN_A", "FW_MAIN_B"):
        images = search_pdc_fw_images(temp_cbfs, cbfstool, region)
        assert fw_slot in images
        assert images[fw_slot]["fw_binary"] == orig_fw_info["fw_binary"]
        assert images[fw_slot]["hash_file"] == orig_fw_info["hash_file"]

    # Run swap
    ret = apfw.main(
        [
            "swap",
            str(temp_cbfs),
            fw_slot,
            str(new_fw_path),
        ]
    )
    assert ret == 0

    # After swap, verify new firmware in both regions
    for region in ("FW_MAIN_A", "FW_MAIN_B"):
        images = search_pdc_fw_images(temp_cbfs, cbfstool, region)
        assert fw_slot in images
        assert images[fw_slot]["fw_binary"] == new_fw_info["fw_binary"]
        assert images[fw_slot]["hash_file"] == new_fw_info["hash_file"]


def test_swap_non_existent_target(cbfs_test_images: Path, tmp_path: Path):
    """Test swapping a target FW slot that does not exist in CBFS"""
    cbfs_bin = cbfs_test_images / "cbfs.bin"
    temp_cbfs = tmp_path / "cbfs_swapped.bin"
    shutil.copy(cbfs_bin, temp_cbfs)

    new_fw = get_test_file_path("rts5453_v0.44.3.bin")

    # 'nonexistent' should not match anything
    with pytest.raises(FileNotFoundError):
        apfw.main(
            [
                "swap",
                str(temp_cbfs),
                "nonexistent",
                str(new_fw),
            ]
        )
