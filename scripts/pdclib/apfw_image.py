# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Examine an AP FW image and extract PDC FW images"""

import enum
import hashlib
import logging
from pathlib import Path
import subprocess
import tempfile
from typing import List

from pdclib import rtk_utils
from pdclib import ti_utils


class ApFwConstants(enum.IntEnum):
    """Constants used in AP FW / CBFS binaries"""

    HASH_FILE_RTK_LEN = 3
    HASH_FILE_TI_LEN = 11
    HASH_FILE_TI_PROJNAME_OFFSET = 3
    HASH_FILE_TI_PROJNAME_LEN = 8


class CbfsTool:
    """Calls external cbfstool executable to unpack CBFS contents"""

    def __init__(self, cbfstool_path: Path | None = None):
        self.l = logging.getLogger("cbfstool")

        self.cbfstool_path = self._locate_cbfstool(cbfstool_path)
        logging.debug("Using cbfstool at '%s'", self.cbfstool_path)

    def _locate_cbfstool(self, user_provided_path: Path | None) -> Path:
        """Locate the path to cbfstool

        If user_provided_path is not None, test that path and use it. If it
        fails, raise an exception and give up.

        Otherwise, search for cbfstool in $PATH and then attempt to "borrow"
        it from the chroot.

        Should no working cbfstool be found, raise a FileNotFoundError.
        """

        if user_provided_path:
            # User provided an exact path to use
            self._check_cbfstool(user_provided_path)
            return user_provided_path

        # Search for the cbfstool binary
        search_paths = (
            Path("cbfstool"),  # Look in $PATH
            Path.home()
            / "chromiumos"
            / "chroot"
            / "usr"
            / "bin"
            / "cbfstool",  # Steal it from the chroot
        )

        for p in search_paths:
            try:
                self._check_cbfstool(p)
                return p
            except FileNotFoundError:
                continue

        raise FileNotFoundError("Cannot find cbfstool")

    def _check_cbfstool(self, path: Path) -> None:
        """Attempt to execute cbfstool at the provided `path`

        :param path: A hypothetical path to `cbfstool` to test

        Raises an exception if cbfstool cannot be executed.
        """
        self.l.debug("Checking for cbfstool at '%s'", path)

        try:
            # Check that we can call cbfstool
            subprocess.check_call(
                [path, "-h"],
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            # `cbfstool -h` exits with return code 1. Ignore this.
            pass
        except:
            self.l.debug("Cannot call cbfstool at '%s'", path)
            raise

        self.l.debug("Found cbfstool at '%s'", path)

    def list_contents(self, ap_fw_path: Path, region: str) -> List[dict]:
        """List the files in a given CBFS region

        :param ap_fw_path: Path to the AP FW image
        :param region: The CBFS region to list files from (see `cbfstool
                       layout`)
        :returns: A list of dictionaries, one for each file.
        """
        if not ap_fw_path.exists():
            raise FileNotFoundError(str(ap_fw_path))

        cbfs_contents = subprocess.check_output(
            [self.cbfstool_path, ap_fw_path, "print", "-r", region, "-k"],
        ).decode("ascii")

        files = []

        self.l.debug("Contents of '%s':", ap_fw_path)
        for i, row in enumerate(cbfs_contents.split("\n")):
            if i == 0 or not row.strip():
                continue

            name, offset, typ, metadata_size, data_size, total_size = row.split(
                "\t"
            )

            files.append(
                {
                    "name": name,
                    "metadata_size": int(metadata_size, 0),
                    "data_size": int(data_size, 0),
                    "total_size": int(total_size, 0),
                    "offset": int(offset, 0),
                    "type": typ,
                }
            )

            self.l.debug(" - '%s', %s, %d bytes", name, typ, int(data_size, 0))

        return files

    def extract(
        self, ap_fw_path: Path, region: str, cbfs_filename: Path, outpath: Path
    ):
        """Extract a file from CBFS

        :param ap_fw_path: Path to the AP FW image
        :param region: The CBFS region to extract the file from
        :param cbfs_filename: The filename within CBFS to extract
        :param outpath: A path to write the extracted file
        """
        if not ap_fw_path.exists():
            raise FileNotFoundError(str(ap_fw_path))

        subprocess.check_output(
            [
                self.cbfstool_path,
                ap_fw_path,
                "extract",
                "-r",
                region,
                "-n",
                cbfs_filename,
                "-f",
                outpath,
            ],
            stderr=subprocess.DEVNULL,
        )

    def read(self, ap_fw_path: Path, region: str, outpath: Path):
        """Read a raw region from CBFS

        :param ap_fw_path: Path to the AP FW image
        :param region: The CBFS region to read out
        :param outpath: A path to write the extracted data
        """
        if not ap_fw_path.exists():
            raise FileNotFoundError(str(ap_fw_path))

        subprocess.check_output(
            [
                self.cbfstool_path,
                ap_fw_path,
                "read",
                "-r",
                region,
                "-f",
                outpath,
            ],
            stderr=subprocess.DEVNULL,
        )

    def create(self, ap_fw_path: Path, regions: list[str], fmap: Path):
        """Create new CBFS filesystem(s)"""
        subprocess.check_output(
            [
                self.cbfstool_path,
                ap_fw_path,
                "create",
                "-M",
                str(fmap),
                "-r",
                ",".join(regions),
            ]
        )

    def add_file(
        self,
        ap_fw_path: Path,
        region: str,
        outside_path: Path,
        cbfs_filename: str,
        typ: str = "raw",
    ):
        """Insert (add) a file to CBFS"""

        if not ap_fw_path.exists():
            raise FileNotFoundError(str(ap_fw_path))

        if not outside_path.exists():
            raise FileNotFoundError(str(outside_path))

        subprocess.check_output(
            [
                self.cbfstool_path,
                ap_fw_path,
                "add",
                "-r",
                region,
                "-f",
                str(outside_path),
                "-n",
                cbfs_filename,
                "-t",
                typ,
            ],
        )

    def write(self, ap_fw_path: Path, region: str, outside_path: Path):
        """Insert raw data into a region"""

        if not ap_fw_path.exists():
            raise FileNotFoundError(str(ap_fw_path))

        if not outside_path.exists():
            raise FileNotFoundError(str(outside_path))

        subprocess.check_output(
            [
                self.cbfstool_path,
                ap_fw_path,
                "write",
                "-r",
                region,
                "-f",
                str(outside_path),
            ],
        )


def parse_firmware_and_hashfile(fw_path: Path, hash_path: Path | None) -> dict:
    """Extract data for this FW binary and hash file

    Inspect a provided PDC FW binary (TI or RTK) and Depthcharge updater hash
    file. Hash file path may be None or non-existent. If so, the "hash_file" key
    in the returned dict will read None.

    Returns a dictionary containing:
        {
            "name": Base file name with .bin/.hash stripped off
            "fw_binary": (major, minor, config, project name string)-tuple
            "hash_file": {
                "ver": (major, minor, config)-tuple describing version in hash
                       file
                "config_name": Project name string (only applicable on for TI)
            }
            "fw_binary_hash": Hex string SHA1 of firmware binary file
        }
    """

    detected_fw = {
        "name": fw_path.stem,
        "fw_binary": None,
        "hash_file": None,
        "fw_binary_hash": None,
    }

    if hash_path and hash_path.exists():
        # Inspect hash file if found.
        with open(hash_path, "rb") as f:
            contents = f.read()

        if len(contents) == ApFwConstants.HASH_FILE_RTK_LEN:
            # RTK hash files have just FW version bytes
            detected_fw["hash_file"] = {
                "ver": (contents[0], contents[1], contents[2]),
                "config_name": None,
            }
        elif len(contents) == ApFwConstants.HASH_FILE_TI_LEN:
            # TI hash files have FW version and project name string
            detected_fw["hash_file"] = {
                "ver": (contents[0], contents[1], contents[2]),
                "config_name": ti_utils.format_ti_config_string(
                    contents[
                        # pylint: disable=line-too-long
                        ApFwConstants.HASH_FILE_TI_PROJNAME_OFFSET : ApFwConstants.HASH_FILE_TI_PROJNAME_OFFSET
                        + ApFwConstants.HASH_FILE_TI_PROJNAME_LEN
                    ]
                ),
            }
        else:
            logging.error(
                "Invalid size for hash file %s (%d bytes)",
                hash_path,
                len(contents),
            )
            # Continue (detected_fw[file]["hash_file"] will remain None)

    # Report the SHA1 hash of the FW
    with open(fw_path, "rb") as f:
        detected_fw["fw_binary_hash"] = hashlib.file_digest(
            f, "sha1"
        ).hexdigest()

    # Open firmware files and retrieve program name and version
    # Save as a tuple: (major, minor, patch, "project_name")
    if fw_path.name.startswith("tps6699"):
        detected_fw["fw_binary"] = ti_utils.read_base_fw_ver_and_proj_name(
            fw_path
        )
    elif fw_path.name.startswith("rts54"):
        fw = rtk_utils.RtkFwBinary(fw_path)

        detected_fw["fw_binary"] = (
            *fw.get_fw_version().as_tuple(),
            fw.get_project_name(),
        )

    return detected_fw


def print_fw_and_hash_info_row(firmware_info: dict):
    """Print FW and hash file info

    Accepts a dict returned by parse_firmware_and_hashfile() and prints this
    data to stdout in a human-readable table format.
    """

    hash_text = "%d.%d.%d (%s)" % (
        *firmware_info["hash_file"]["ver"],
        firmware_info["hash_file"].get("config_name", "N/A"),
    )
    fw_ver_text = "%d.%d.%d (%s)" % (*firmware_info["fw_binary"],)
    print(
        f"{firmware_info['name']:<25}Hash File: {hash_text:<19} "
        f"SHA1: {firmware_info['fw_binary_hash']:<42} "
        f"Embedded: {fw_ver_text}"
    )


def get_ec_ap_fw_versions(apfw_image: Path, cbfstool: CbfsTool) -> dict:
    """Extract RO, RW_A, RW_B AP FW version and RW_A, RW_B EC versions"""

    IMAGES = (
        {"title": "AP RO", "region": "RO_FRID", "file": None},
        {"title": "AP RW_A", "region": "RW_FWID_A", "file": None},
        {"title": "AP RW_B", "region": "RW_FWID_B", "file": None},
        {"title": "EC RW_A", "region": "FW_MAIN_A", "file": "ecrw.version"},
        {"title": "EC RW_B", "region": "FW_MAIN_B", "file": "ecrw.version"},
    )

    fw_data = {}

    with tempfile.TemporaryDirectory() as tempdir:
        tempdir = Path(tempdir)

        for img in IMAGES:
            try:
                if img["file"] is None:
                    # Raw region in CBFS. Use `cbfstool read`.
                    extracted_filename = tempdir / f"{img['region']}.bin"

                    cbfstool.read(apfw_image, img["region"], extracted_filename)
                else:
                    # Region has a CBFS filesystem. Use `cbfstool extract`.
                    extracted_filename = (
                        tempdir / f"{img['region']}_{img['file']}.bin"
                    )

                    cbfstool.extract(
                        apfw_image,
                        img["region"],
                        img["file"],
                        extracted_filename,
                    )
            except subprocess.CalledProcessError:
                fw_data[img["title"]] = None
                continue

            # Read version string from file
            fw_data[img["title"]] = (
                extracted_filename.read_bytes().strip(b"\x00").decode("ascii")
            )

    return fw_data


def search_pdc_fw_images(
    apfw_image: Path, cbfstool: CbfsTool, cbfs_region: str = "FW_MAIN_A"
) -> List[dict]:
    """Search the embedded CBFS payload in an AP FW image for PDC FW images

    :param apfw_image: Path to AP FW binary image
    :param cbfstool: CbfsTool instance to run cbfstool operations with
    :return: A list of dictionaries describing each detected PDC FW image
    """

    def filter_pdc_fw(s: str) -> bool:
        return (
            s.startswith("rts54") or s.startswith("tps6699")
        ) and s.endswith(".bin")

    # Find PDC FWs in image
    detected_fw = {
        Path(f["name"]).stem: {
            "fw_binary": None,
            "hash_file": None,
            "fw_binary_hash": None,
        }
        for f in cbfstool.list_contents(apfw_image, cbfs_region)
        if filter_pdc_fw(f["name"])
    }

    with tempfile.TemporaryDirectory() as tempdir:
        tempdir = Path(tempdir)
        all_fw = {}

        # Extract all files we care about:
        for file in detected_fw:
            file_bin = f"{file}.bin"
            file_hash = f"{file}.hash"

            # PDC FW binary
            try:
                cbfstool.extract(
                    apfw_image,
                    cbfs_region,
                    file_bin,
                    tempdir / file_bin,
                )
            except subprocess.CalledProcessError as e:
                raise FileNotFoundError(
                    f"Cannot find FW binary payload '{file_bin}' in CBFS"
                ) from e

            # Associated hash file
            try:
                cbfstool.extract(
                    apfw_image,
                    cbfs_region,
                    file_hash,
                    tempdir / file_hash,
                )
            except subprocess.CalledProcessError:
                logging.warning("File %s not present", file_hash)
                # Continue without examining the hash file

            all_fw[file] = parse_firmware_and_hashfile(
                tempdir / file_bin, tempdir / file_hash
            )

        return all_fw
