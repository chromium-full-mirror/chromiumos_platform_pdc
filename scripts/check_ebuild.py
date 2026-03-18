#!/usr/bin/env vpython3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Emerge a PDC FW ebuild and inspect its contents

This script must be run inside the chroot.
"""

import argparse
from pathlib import Path
import re
import subprocess
import sys

import pdclib.apfw_image


# A non-production Chrome OS board that we will use as a sandbox
BOARD_NAME = "simple-fake-board"

# Wildcard expressions that should match all PDC FW ebuilds
PDC_FW_EBUILD_PREFIXES = ("sys-firmware/realtek-*", "sys-firmware/ti-*")


def run_setup_board():
    """Run `setup_board --board $BOARD_NAME`"""
    subprocess.check_call(
        [
            "setup_board",
            "--board",
            BOARD_NAME,
            "--skip-chroot-upgrade",
            "--no-update-chroot",
            "--skip-toolchain-update",
            "--quiet",
        ],
        stderr=subprocess.PIPE,
    )


def emerge_packages(package_atoms: list[str]):
    """Emerge the specified package atoms"""
    subprocess.check_call(
        [
            f"emerge-{BOARD_NAME}",
            "--verbose",
            "-j",
            *package_atoms,
        ]
    )


def unmerge_old_firmware_packages():
    """Remove all PDC packages from the board build directory"""
    try:
        subprocess.check_call(
            [
                f"emerge-{BOARD_NAME}",
                "--rage-clean",
                *PDC_FW_EBUILD_PREFIXES,
            ]
        )
    except subprocess.CalledProcessError:
        # Exits with 1 if no matching packages are installed. This is OK.
        pass


def get_installed_pdc_fw_packages() -> list[str]:
    """Return a list of installed PDC FW packages"""
    outp = subprocess.check_output(
        [
            f"qlist-{BOARD_NAME}",
            "-Iv",  # List installed packages with version info
            *PDC_FW_EBUILD_PREFIXES,
        ],
        text=True,
    )

    return outp.splitlines()


def get_package_files(package: str) -> list[Path]:
    """Run equery to get the list of files installed by the package"""
    outp = subprocess.check_output(
        [
            f"equery-{BOARD_NAME}",
            "files",
            "--filter=obj",  # Ignore directories
            package,
        ],
        text=True,
    )

    # Paths are absolute but relative to the board's sysroot directory
    return [Path(l) for l in outp.splitlines()]


def print_green_header(title: str):
    print("\x1b[1m\x1b[32m")
    print(title)
    print("=" * len(title), "\x1b[0m")


def add_version_specifier(package_atom: str) -> str:
    """Add a '=' version specifier if a specific version/rev is passed"""
    if any(
        package_atom.startswith(vs) for vs in ("~", "=", ">=", ">", "<", "<=")
    ):
        # User already included their own version specifier
        return package_atom

    if re.search(r"(\d+)\.(\d+)\.(\d+)(-r\d+)?$", package_atom):
        # User did specify an exact version and possibly revision. Append a
        # '=' version specifier for convenience
        return f"={package_atom}"

    # Bare package name (no VS, no version/rev). Allow emerge to choose based
    # on available ebuilds.
    return package_atom


def cmd_inspect_package(package_atoms_list: list[str]) -> int:
    """Emerge the packages and inspect PDC FW contents"""

    print(
        "Setting up fake-simple-board. "
        "This may take a few moments the first time."
    )

    try:
        run_setup_board()
    except FileNotFoundError:
        raise RuntimeError(
            "Cannot call `setup_board`. "
            "This script must be run inside the chroot."
        )

    print("Board setup complete")

    print("Unmerging all existing PDC FW packages")
    unmerge_old_firmware_packages()
    print("Unmerge complete")

    package_atoms_list = [add_version_specifier(p) for p in package_atoms_list]

    print("Emerging packages:", ", ".join(package_atoms_list))
    try:
        emerge_packages(package_atoms_list)
    except subprocess.CalledProcessError:
        print(
            "An error occurred while emerging. A specified package may "
            "not exist locally. Try repo sync."
        )
        print()
        raise
    print("Emerge complete")

    packages = get_installed_pdc_fw_packages()

    print()
    print(f"Found installed packages ({len(packages)}):")
    for pkg in packages:
        print(f" - {pkg}")

    for pkg in packages:
        print_green_header(pkg)

        files = get_package_files(pkg)
        print("Found files:", ", ".join(str(f) for f in files))
        print()

        BASE_DIR = Path("/build") / BOARD_NAME
        for fw_file in (f for f in files if f.suffix == ".bin"):
            base_name = fw_file.stem
            # The output of equery has a leading "/" in the file paths,
            # despite not being absolute paths. This strips it.
            dir_within = fw_file.parent.relative_to("/")

            fw_file = BASE_DIR / dir_within / f"{base_name}.bin"
            hash_file = BASE_DIR / dir_within / f"{base_name}.hash"

            data = pdclib.apfw_image.parse_firmware_and_hashfile(
                fw_file, hash_file
            )
            pdclib.apfw_image.print_fw_and_hash_info_row(data)

    return 0


def main(argv: list[str] | None) -> int:
    """Main entry point for argument parsing"""

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=(
            "Emerge PDC firmware ebuilds and print info about the\n"
            "resulting installed PDC FW and hash file. Intended for\n"
            "testing PDC FW ebuild scripts to ensure the correct FW\n"
            "is retrieved from cloud storage and placed into the\n"
            "board's sysroot firmware directory."
        ),
    )
    parser.add_argument(
        "package_atoms",
        type=str,
        nargs="+",
        help=(
            "Package atom(s) to emerge and inspect. Multiple may be \n"
            "specified. These will be passed to `emerge`. Examples:\n\n"
            "# Grab latest version\n"
            "realtek-rts5453vb-GOOG0P00-firmware\n\n"
            '# Grab specific version ("=" automatically added),\n'
            "# with or without revision\n"
            "realtek-rts5453vb-GOOG0P00-firmware-0.54.1-r0\n"
            "ti-tps6699x-GOOG0J00-firmware-19.32.2\n\n"
            "# Use portage version specifiers\n"
            ">=realtek-rts5453vb-GOOG0P00-firmware-0.50"
        ),
    )

    opts = parser.parse_args(argv)

    return cmd_inspect_package(opts.package_atoms)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
