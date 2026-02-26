# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=import-modules-only,import-error

"""Test apfw_image.py"""

from pathlib import Path

from pdclib.apfw_image import CbfsTool
from pdclib.apfw_image import search_pdc_fw_images
from tests.common import cbfs_test_images  # pylint: disable=unused-import


# pylint: disable=redefined-outer-name
def test_search_pdc_fw_images(cbfs_test_images: Path):
    cbfstool = CbfsTool()

    images = search_pdc_fw_images(cbfs_test_images / "cbfs.bin", cbfstool)

    assert len(images) == 2

    assert "rts5453_v0.45.4" in images
    assert images["rts5453_v0.45.4"]["fw_binary"] == (0, 45, 4, "GOOG0000")
    assert images["rts5453_v0.45.4"]["hash_file"]["ver"] == (0, 45, 4)
    # RTK hash files do not include the config name
    assert images["rts5453_v0.45.4"]["hash_file"]["config_name"] is None

    assert "tps6699x-GOOG0J30_00132002_TFU" in images
    assert images["tps6699x-GOOG0J30_00132002_TFU"]["fw_binary"] == (
        0x13,
        0x20,
        0x02,
        "GOOG0J30",
    )
    assert images["tps6699x-GOOG0J30_00132002_TFU"]["hash_file"]["ver"] == (
        0x13,
        0x20,
        0x02,
    )
    assert (
        images["tps6699x-GOOG0J30_00132002_TFU"]["hash_file"]["config_name"]
        == "GOOG0J30"
    )
