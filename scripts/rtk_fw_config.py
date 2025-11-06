#!/usr/bin/env vpython3
# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Display or patch configuration data with a Reaktek PDC FW binary

Dump vital configuration items from a Realtek PDC FW binary and optionally
apply a new 4 KiB configuration block to a Realtek PDC FW binary.
"""

import argparse
from pathlib import Path
import sys
from typing import Iterable

from pdclib import pdo
from pdclib import rtk_utils


def print_config(fw: rtk_utils.RtkFwBinary):
    """Parse a firmware binary, printing out key configuration values

    Args:
        fw: RtkFwBinary class containing the full Realtek firmware binary
    """

    def format_i2c_addrs(addrs: Iterable[int]) -> str:
        return ", ".join([hex(i) for i in addrs])

    def format_svid(svid: int) -> str:
        COMMON_SVIDS = {
            0xFF01: "DP (ff01)",
            0x8087: "TBT (8087)",
        }

        return COMMON_SVIDS.get(svid, hex(svid))

    rtk_configs = {
        "Project name": fw.get_project_name(),
        "Version": fw.get_fw_version(),
        "USB VID:PID": fw.get_vid_pid(),
        "Port config": fw.get_port_used().name,
        "Debug Accy GPIO": fw.get_debug_accy_gpio_polarity().name,
        "PMC I2C Base addrs": format_i2c_addrs(fw.get_pmc_i2c_addrs()),
        "Retimer I2C addrs": format_i2c_addrs(fw.get_retimer_i2c_addrs()),
        "BBR I2C addrs": format_i2c_addrs(fw.get_bbr_i2c_addrs()),
        "SMBus I2C voltage": fw.get_i2c_voltage_smbus().name,
        "Retimer I2C voltage": fw.get_i2c_voltage_retimer().name,
        "PMC I2C voltage": fw.get_i2c_voltage_pmc().name,
        "SVIDs Port A": ", ".join(
            (format_svid(svid) for svid in fw.get_svids("A"))
        ),
        "SVIDs Port B": ", ".join(
            (format_svid(svid) for svid in fw.get_svids("B"))
        ),
        "CRC32": hex(fw.get_file_crc32()),
    }

    for name, value in rtk_configs.items():
        print(f"{name.ljust(20)}: {value}")

    print()
    print("Sink PDOs Port A:")
    for p in fw.get_pdos(pdo.PDORole.SINK, "A"):
        print(p)

    print("Sink PDOs Port B:")
    for p in fw.get_pdos(pdo.PDORole.SINK, "B"):
        print(p)

    print()
    print("Source PDOs Port A:")
    for p in fw.get_pdos(pdo.PDORole.SOURCE, "A"):
        print(p)

    print("Source PDOs Port B:")
    for p in fw.get_pdos(pdo.PDORole.SOURCE, "B"):
        print(p)


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
    print_config(fw)
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
    print_config(fw)

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
