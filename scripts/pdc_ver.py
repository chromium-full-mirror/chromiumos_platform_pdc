#!/usr/bin/env vpython3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tool to report PDC firmware version and project name."""

import argparse
from pathlib import Path
import sys

# pylint: disable=import-modules-only
from pdclib import rtk_utils
from pdclib import ti_utils
from pdclib.ti_constants import TiHeader


TI_HEADERS = (
    TiHeader.TFU_BUNDLE_TYPE_A,
    TiHeader.TFU_BUNDLE_TYPE_B,
    TiHeader.APPCONFIG_SECTION,
)


def detect_type(path: Path) -> str:
    """Detect the type of PDC firmware image."""

    # Check headers for TI
    with open(path, "rb") as f:
        header = f.read(4)
    if header in TI_HEADERS:
        return "TI"

    # Check size for RTK
    size = path.stat().st_size
    if size == rtk_utils.RtkFwOffset.TOTAL_SIZE:
        return "RTK_FW"
    if size == rtk_utils.RtkFwOffset.CONFIG_RANGE_LENGTH:
        return "RTK_CFG"

    return "UNKNOWN"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report PDC FW version and project name"
    )
    parser.add_argument("image", type=Path, help="Path to PDC FW image")
    args = parser.parse_args(argv)

    if not args.image.exists():
        print(f"Error: File {args.image} does not exist", file=sys.stderr)
        return 1

    img_type = detect_type(args.image)

    if img_type == "TI":
        try:
            major, minor, patch, proj = ti_utils.read_base_fw_ver_and_proj_name(
                args.image
            )
            ver_str = f"{major}.{minor}.{patch}" if major is not None else "N/A"
            proj_str = proj if proj is not None else "N/A"
            print("Image Type   : TI")
            print(f"Version      : {ver_str}")
            print(f"Project Name : {proj_str}")
        except Exception as e:  # pylint: disable=broad-except
            raise RuntimeError(f"Error parsing TI image {args.image}") from e

    elif img_type == "RTK_FW":
        try:
            fw = rtk_utils.RtkFwBinary(args.image)
            print("Image Type   : Realtek (Full FW)")
            print(f"Version      : {fw.get_fw_version()}")
            print(f"Project Name : {fw.get_project_name()}")
            if not fw.verify_crc32():
                raise ValueError(
                    f"CRC32 invalid. Expected 0x{fw.get_file_crc32():08x}, "
                    f"but calculated 0x{fw.calc_crc32():08x}"
                )
        except Exception as e:  # pylint: disable=broad-except
            raise RuntimeError(f"Error parsing RTK image {args.image}") from e

    elif img_type == "RTK_CFG":
        try:
            cfg = rtk_utils.RtkConfigFragment(args.image)
            print("Image Type   : Realtek (Config Fragment)")
            print(f"Version      : x.x.{cfg.get_config_version()}")
            print(f"Project Name : {cfg.get_project_name()}")
        except Exception as e:  # pylint: disable=broad-except
            raise RuntimeError(
                f"Error parsing RTK config fragment {args.image}"
            ) from e

    else:
        print(
            f"Error: Could not autodetect image type for {args.image}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
