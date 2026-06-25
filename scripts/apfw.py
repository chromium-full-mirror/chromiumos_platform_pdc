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
import shutil
import sys

from pdclib import apfw_image


def cmd_swap_ap_image(cbfstool: apfw_image.CbfsTool, args) -> int:
    """Swap a PDC FW image in the AP image / CBFS"""

    fw_slot = args.fw_slot.removesuffix(".bin").removesuffix(".hash")
    new_fw_path = args.new_fw_path

    if not new_fw_path.exists():
        logging.error("New FW binary %s does not exist", new_fw_path)
        return 1

    work_ap_fw_path = args.ap_fw_path
    if args.output:
        shutil.copy(args.ap_fw_path, args.output)
        work_ap_fw_path = args.output

    for region in ("FW_MAIN_A", "FW_MAIN_B"):
        logging.info("Swapping PDC FW for region %s", region)
        apfw_image.swap_pdc_fw_image(
            work_ap_fw_path,
            cbfstool,
            region,
            fw_slot,
            new_fw_path,
            args.hash_file,
        )

    logging.info(
        "Successfully swapped FW slot '%s' with %s in %s",
        fw_slot,
        new_fw_path,
        work_ap_fw_path,
    )

    return 0


def cmd_read_ap_image(cbfstool: apfw_image.CbfsTool, args) -> int:
    """Use cbfstool to read what's in the AP image / CBFS"""

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

    # Parent parser for common arguments
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "ap_fw_path", help="Path to AP FW image", type=Path
    )
    parent_parser.add_argument(
        "-c",
        "--cbfstool_path",
        help="Path to cbfstool executable. If not provided, "
        "script will search $PATH and chroot.",
        type=Path,
    )
    parent_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose log messages",
    )
    parent_parser.add_argument(
        "-r",
        "--region",
        default="FW_MAIN_A",
        choices=("FW_MAIN_A", "FW_MAIN_B"),
        help="Manually specify a CBFS region to search/modify",
    )

    # Main parser
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 'list' subcommand
    list_parser = subparsers.add_parser(
        "list", parents=[parent_parser], help="List PDC FW images in AP FW"
    )
    list_parser.add_argument(
        "-j", "--json", action="store_true", help="Output data in JSON format"
    )

    # 'swap' subcommand
    swap_parser = subparsers.add_parser(
        "swap", parents=[parent_parser], help="Swap a PDC FW image in AP FW"
    )
    swap_parser.add_argument(
        "fw_slot",
        help="Base filename of the firmware within CBFS to swap (not including "
        ".bin or .hash). Use the `list` subcommand to see bundled PDC FWs.",
    )
    swap_parser.add_argument(
        "new_fw_path",
        type=Path,
        help="Path to the new PDC FW binary",
    )
    swap_parser.add_argument(
        "--hash-file",
        type=Path,
        help="Optional path to new hash file for swap. "
        "If not provided, it will be generated from the new FW binary.",
    )
    swap_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output path for the modified AP FW image. "
        "If not provided, the input image will be modified in-place.",
    )

    cli_args = parser.parse_args(argv)

    if cli_args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(level=log_level, format="%(levelname)-8s: %(message)s")

    # Common checks
    try:
        cbfstool = apfw_image.CbfsTool(cli_args.cbfstool_path)
    except FileNotFoundError:
        logging.error(
            "Cannot find `cbfstool`. Please install it in your $PATH or "
            "provide a path to the executable with -c/--cbfstool_path"
        )
        return 1

    if not cli_args.ap_fw_path.exists():
        logging.error("AP image binary %s does not exist", cli_args.ap_fw_path)
        return 1

    if cli_args.subcommand == "swap":
        return cmd_swap_ap_image(cbfstool, cli_args)
    elif cli_args.subcommand == "list":
        return cmd_read_ap_image(cbfstool, cli_args)
    else:
        # Should not be reached if required=True in add_subparsers
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
