#!/usr/bin/env vpython3
# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Display or patch configuration data with a Reaktek PDC FW binary

Dump vital configuration items from a Realtek PDC FW binary and optionally
apply a new configuration block to a Realtek PDC FW binary.
"""

import argparse
from pathlib import Path
import sys

from pdclib import rtk_utils


def cmd_show(args) -> int:
    """Display the config info from a full FW binary or config fragment"""

    binary = rtk_utils.fw_or_config_from_file(args.image)

    rtk_utils.print_config(binary)

    return 0


def cmd_extract(args) -> int:
    """Take the config section of the given full FW binary and save to file"""

    fw = rtk_utils.RtkFwBinary(args.image)

    rtk_utils.print_config(fw)
    fw.export_config_section(args.out)

    print()
    print(f"Wrote config section to {args.out}")

    return 0


def cmd_merge(args) -> int:
    """Take a full FW binary, replace its config section, and save to file"""

    fw = rtk_utils.RtkFwBinary(args.image)

    # This can be a config fragment or a full FW binary.
    new_config = rtk_utils.fw_or_config_from_file(args.config)

    print(f"Current config for '{args.image}':")
    rtk_utils.print_config(fw)

    fw.set_config(new_config)
    fw.set_file_crc32()

    print()
    print(f"Modified config for `{args.out}`")
    rtk_utils.print_config(fw)

    fw.export_fw_binary(args.out)

    print()
    print(f"Wrote new FW image to to {args.out}")

    return 0


def main(argv: list[str] | None) -> int:
    """Main entry point for argument parsing"""

    parser = argparse.ArgumentParser()
    subcommands = parser.add_subparsers(required=True)

    #
    # ./rtk_fw_config.py show
    #
    parser_show = subcommands.add_parser(
        "show", help="Print config info and exit"
    )
    parser_show.add_argument(
        "-i",
        "--image",
        type=Path,
        required=True,
        help="Full FW binary or config fragment",
    )
    parser_show.set_defaults(func=cmd_show)

    #
    # ./rtk_fw_config.py extract
    #
    parser_extract = subcommands.add_parser(
        "extract",
        help="Extract config fragment from a full "
        "FW binary and output it to a file",
    )
    parser_extract.add_argument(
        "-i",
        "--image",
        type=Path,
        help="Full FW binary to extract from",
        required=True,
    )
    parser_extract.add_argument(
        "-o",
        "--out",
        type=Path,
        help="Path to write config fragment to",
        required=True,
    )
    parser_extract.set_defaults(func=cmd_extract)

    #
    # ./rtk_fw_config.py merge
    #
    parser_merge = subcommands.add_parser(
        "merge",
        help="Apply a config to an existing full FW "
        "image, and output the a FW image.",
    )
    parser_merge.add_argument(
        "-i",
        "--image",
        type=Path,
        help="Full FW binary to use as base. Will not be modified",
        required=True,
    )
    parser_merge.add_argument(
        "-c",
        "--config",
        type=Path,
        help="Path to config fragment or full image to apply",
        required=True,
    )
    parser_merge.add_argument(
        "-o",
        "--out",
        type=Path,
        help="Path to write merged full FW binary",
        required=True,
    )
    parser_merge.set_defaults(func=cmd_merge)

    args = parser.parse_args(argv)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
