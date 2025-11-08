#!/usr/bin/env vpython3
# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Perform a Realtek PDC FW update

Sideload new firmware by streaming it over the EC console interface from a host
machine running this script.
"""

import logging
from pathlib import Path

from pdclib import console_fwup_common
import pdclib.console_fwup_rtk
import pdclib.console_fwup_tps


PDC_FWUP_DRIVERS = {
    "rtk": pdclib.console_fwup_rtk.rtk_update,
    "tps": pdclib.console_fwup_tps.tps_update,
}


def main(
    pdc_driver: str,
    servod_host: str,
    servod_port: int,
    pdc_fw_path: Path,
    chip: console_fwup_common.ChipSpec,
) -> int:
    """Process a PDC FW update"""
    try:
        return PDC_FWUP_DRIVERS[pdc_driver](
            servod_host, servod_port, pdc_fw_path, chip
        )
    except KeyError:
        raise Exception(f"Unsupported pdc driver: {pdc_driver}")


if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pdc_driver",
        default="rtk",
        choices=PDC_FWUP_DRIVERS.keys(),
        help="Type of PDC targetted",
    )
    parser.add_argument("pdc_fw_image", type=Path, help="Path to PDC FW binary")
    parser.add_argument(
        "--host", type=str, default="localhost", help="Servod hostname"
    )
    parser.add_argument("--port", type=int, default=9999, help="Servod port")

    pdc_selection_arg_group = parser.add_mutually_exclusive_group()

    pdc_selection_arg_group.add_argument(
        "--usbc_port",
        "-c",
        type=int,
        default=0,
        help="USB-C port number on DUT to target. "
        "Mutually exclusive with -i/--i2c_target.",
    )
    pdc_selection_arg_group.add_argument(
        "--i2c_target",
        "-i",
        type=str,
        help="Specify a raw I2C bus and address for update. "
        "Mutually exclusive with -c/--usbc_port. "
        "Format: <bus name>:<addr> (Example: I2C_PORT_PD:0x66)",
    )

    args = parser.parse_args()

    if args.i2c_target:
        try:
            bus, addr = args.i2c_target.split(":")
        except ValueError as e:
            raise RuntimeError(
                "Invalid I2C target. Must be in the form '<bus name>:<addr>'"
            ) from e

        chip_spec = console_fwup_common.ChipSpecRawI2C(
            i2c_bus=bus, i2c_addr=addr
        )
    else:
        chip_spec = console_fwup_common.ChipSpecPortNum(
            port_number=args.usbc_port
        )

    sys.exit(
        main(
            args.pdc_driver, args.host, args.port, args.pdc_fw_image, chip_spec
        )
    )
