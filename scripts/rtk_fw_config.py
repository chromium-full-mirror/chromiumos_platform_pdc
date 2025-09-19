# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Display or patch configuration data with a Reaktek PDC FW binary

Dump vital configuration items from a Realtek PDC FW binary and optionally
apply a new 4 KiB configuration block to a Realtek PDC FW binary.
"""

import argparse
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
    pdc_fw_bin: str,
    config_file: str,
    output_file: str,
) -> int:
    """Display or update a Realtek PDC firmware file

    Args:
        pdc_fw_bin: Realtek PDC firmware binary input filename.
        config_file: Optional - configuration binary input filename
        output_file: Optional - output filename that contains pdc_fw_bin patched
                    with config_file
    """
    fw = rtk_utils.RtkFwBinary(pdc_fw_bin)

    # Print current values
    print(f"Current config for '{pdc_fw_bin}':")
    print_config(fw)
    print()

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

    with open(output_file, "wb") as fw_pkg_file:
        fw_pkg_file.write(fw.fw_bin)

    return 0


if __name__ == "__main__":
    # need to handle script arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "pdc_fw_bin", type=str, help="Realtek PD firmware binary input"
    )
    parser.add_argument(
        "--config_file",
        type=str,
        default=None,
        help="Binary configuration file input",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default=None,
        help="PD firmware binary output, required if using --config_file",
    )

    args = parser.parse_args()

    if args.config_file and not args.output_file:
        parser.error("--output_file is required when --config_file is used")

    sys.exit(main(args.pdc_fw_bin, args.config_file, args.output_file))
