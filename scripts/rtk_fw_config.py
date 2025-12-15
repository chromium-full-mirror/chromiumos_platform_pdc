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


def main(
    pdc_fw_bin: Path,
    config_file: Path,
    output_file: Path,
    output_config_file: Path,
) -> int:
    """Display or update a Realtek PDC firmware file

    Args:
        pdc_fw_bin: Realtek PDC firmware binary input filename.
        config_file: Optional - configuration binary input filename
        output_file: Optional - output filename that contains pdc_fw_bin patched
                    with config_file
        output_config_file: Optional - if present, the configuration from the
                    input firmware binary is extracted and written to this file.
    """
    fw = rtk_utils.RtkFwBinary(pdc_fw_bin)

    # Print current values
    print(f"Current config for '{pdc_fw_bin}':")
    rtk_utils.print_config(fw)
    print()

    if output_config_file is not None:
        config = fw.get_config()
        print(f"Saving config to `{output_config_file}'")
        with open(output_config_file, "wb") as cfg_file:
            cfg_file.write(config)
        return 0

    if config_file is None:
        return 0

    with open(config_file, "rb") as fw_conf_file:
        fw_conf = fw_conf_file.read()
        fw_conf = bytearray(fw_conf)

    # Patch new configuration into the firmware binary
    fw.set_config(fw_conf)

    # Patch in the new CRC
    fw.set_file_crc32()

    print(f"Modified config for `{output_file}`")
    rtk_utils.print_config(fw)

    fw.export_fw_binary(output_file)

    return 0


if __name__ == "__main__":
    # need to handle script arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "pdc_fw_bin", type=Path, help="Realtek PD firmware binary input"
    )
    parser.add_argument(
        "--config_file",
        type=Path,
        default=None,
        help="Binary configuration file input",
    )
    parser.add_argument(
        "--output_file",
        type=Path,
        default=None,
        help="PD firmware binary output, required if using --config_file",
    )
    parser.add_argument(
        "--output_config_file",
        type=str,
        default=None,
        help=(
            "Extract the configuration from the input file. "
            "If present --config_file option ignored"
        ),
    )

    args = parser.parse_args()

    if args.config_file and not args.output_file:
        parser.error("--output_file is required when --config_file is used")

    sys.exit(
        main(
            args.pdc_fw_bin,
            args.config_file,
            args.output_file,
            args.output_config_file,
        )
    )
