# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=import-modules-only,import-error

"""Test apfw_image.py"""

from pathlib import Path
import shutil

from pdclib.apfw_image import CbfsTool
from pdclib.apfw_image import search_pdc_fw_images
from tests.common import cbfs_test_images  # pylint: disable=unused-import


# pylint: disable=redefined-outer-name
def test_search_pdc_fw_images(cbfs_test_images: Path):
    cbfstool = CbfsTool()

    images = search_pdc_fw_images(cbfs_test_images / "cbfs.bin", cbfstool)

    assert len(images) == 2

    assert "rts5453_GOOG0000" in images
    assert images["rts5453_GOOG0000"]["fw_binary"] == (0, 45, 4, "GOOG0000")
    assert images["rts5453_GOOG0000"]["hash_file"]["ver"] == (0, 45, 4)
    # RTK hash files do not include the config name
    assert images["rts5453_GOOG0000"]["hash_file"]["config_name"] is None

    assert "tps6699x_GOOG0J00" in images
    assert images["tps6699x_GOOG0J00"]["fw_binary"] == (
        0x13,
        0x20,
        0x02,
        "GOOG0J30",
    )
    assert images["tps6699x_GOOG0J00"]["hash_file"]["ver"] == (
        0x13,
        0x20,
        0x02,
    )
    assert images["tps6699x_GOOG0J00"]["hash_file"]["config_name"] == "GOOG0J30"


def test_cbfstool_compact(cbfs_test_images: Path, tmp_path: Path):
    """Test compacting a CBFS region"""
    cbfs_bin = cbfs_test_images / "cbfs.bin"
    temp_cbfs = tmp_path / "cbfs_compact.bin"
    shutil.copy(cbfs_bin, temp_cbfs)

    cbfstool = CbfsTool()

    # Verify we can list files before
    images_before = search_pdc_fw_images(temp_cbfs, cbfstool)
    assert len(images_before) > 0

    # Compact FW_MAIN_A
    cbfstool.compact(temp_cbfs, "FW_MAIN_A")

    # Verify we can still list files and they are same
    images_after = search_pdc_fw_images(temp_cbfs, cbfstool)
    assert images_before == images_after
