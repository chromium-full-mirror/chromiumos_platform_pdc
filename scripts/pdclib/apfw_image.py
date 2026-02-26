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

    def add(
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

            if (tempdir / file_hash).exists():
                # Inspect hash file if found.
                with open(tempdir / file_hash, "rb") as f:
                    contents = f.read()

                if len(contents) == ApFwConstants.HASH_FILE_RTK_LEN:
                    # RTK hash files have just FW version bytes
                    detected_fw[file]["hash_file"] = {
                        "ver": (contents[0], contents[1], contents[2]),
                        "config_name": None,
                    }
                elif len(contents) == ApFwConstants.HASH_FILE_TI_LEN:
                    # TI hash files have FW version and project name string
                    detected_fw[file]["hash_file"] = {
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
                        file_hash,
                        len(contents),
                    )
                    # Continue (detected_fw[file]["hash_file"] will remain None)

            # Report the SHA1 hash of the FW
            with open(tempdir / file_bin, "rb") as f:
                detected_fw[file]["fw_binary_hash"] = hashlib.file_digest(
                    f, "sha1"
                ).hexdigest()

            # Open firmware files and retrieve program name and version
            # Save as a tuple: (major, minor, patch, "project_name")
            if file.startswith("tps6699"):
                detected_fw[file]["fw_binary"] = (
                    ti_utils.read_base_fw_ver_and_proj_name(tempdir / file_bin)
                )
            elif file.startswith("rts54"):
                fw = rtk_utils.RtkFwBinary(tempdir / file_bin)

                detected_fw[file]["fw_binary"] = (
                    *fw.get_fw_version().as_tuple(),
                    fw.get_project_name(),
                )

        return detected_fw
