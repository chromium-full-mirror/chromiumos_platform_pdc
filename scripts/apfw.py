#!/usr/bin/env vpython3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Examine an AP FW image and list included PDC FW images

This script requires that the user has `cbfstool`. Its location can be
provided with the -c/--cbfstool_path CLI argument, or the script will search
the user's $PATH.
"""

import argparse
import json
import logging
from pathlib import Path
import sys

from pdclib import apfw_image


def cmd_read_ap_image(args) -> int:
    """Use cbfstool to read what's in the AP image / CBFS"""

    if not args.ap_fw_path.exists():
        logging.error("AP image binary %s does not exist", args.ap_fw_path)
        return 1

    try:
        cbfstool = apfw_image.CbfsTool(args.cbfstool_path)
    except FileNotFoundError:
        logging.error(
            "Cannot find `cbfstool`. Please install it in your $PATH or "
            "provide a path to the executable with -c/--cbfstool_path"
        )
        return 1

    detected_fw = apfw_image.search_pdc_fw_images(
        args.ap_fw_path, cbfstool, args.region
    )
    ec_ap_fw = apfw_image.get_ec_ap_fw_versions(args.ap_fw_path, cbfstool)

    if args.json:
        # JSON output
        print(
            json.dumps(
                {
                    "input_file": str(args.ap_fw_path.resolve()),
                    "ec_ap_fw": ec_ap_fw,
                    "detected_fw": detected_fw,
                }
            )
        )
    else:
        for fw_title, version in ec_ap_fw.items():
            print(f"{fw_title:<10}: {version}")
        print()

        # Human-readable text output, alphabetically ordered.
        for file in sorted(detected_fw.keys()):
            apfw_image.print_fw_and_hash_info_row(detected_fw[file])

    return 0


def main(argv: list[str] | None) -> int:
    """Main entry point for argument parsing"""

    parser = argparse.ArgumentParser()
    parser.add_argument("ap_fw_path", help="Path to AP FW image", type=Path)
    parser.add_argument(
        "-c",
        "--cbfstool_path",
        help="Path to cbfstool executable. If not provided, "
        "script will search $PATH and chroot.",
        type=Path,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose log messages",
    )
    parser.add_argument(
        "-r",
        "--region",
        default="FW_MAIN_A",
        choices=("FW_MAIN_A", "FW_MAIN_B"),
        help="Manually specify a CBFS region to search",
    )
    parser.add_argument(
        "-j", "--json", action="store_true", help="Output data in JSON format"
    )

    cli_args = parser.parse_args(argv)

    if cli_args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(level=log_level, format="%(levelname)-8s: %(message)s")

    return cmd_read_ap_image(cli_args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
