#!/usr/bin/env python3
# # Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Run the pdc project tests.

This is meant to be called by the CI builders.
"""

import os
import pathlib
import site
import subprocess
import sys

from google.protobuf import json_format  # pylint: disable=import-error

from chromite.api.gen_sdk.chromite.api import firmware_pb2


# This script is only used in CI so it should be fine to assume the EC
# repository is going to be present as well.
PLATFORM_PDC_DIR = pathlib.Path(__file__).parent.resolve()
site.addsitedir(PLATFORM_PDC_DIR.parent / "ec")

import zephyr.scripts.firmware_builder_lib  # pylint: disable=import-error, wrong-import-position


DEFAULT_BUNDLE_METADATA_FILE = "/tmp/artifact_bundle_metadata"


def write_metadata(opts, info):
    """Write the metadata about the bundle."""
    bundle_metadata_file = (
        opts.metadata if opts.metadata else DEFAULT_BUNDLE_METADATA_FILE
    )
    with open(bundle_metadata_file, "w", encoding="utf-8") as file:
        file.write(json_format.MessageToJson(info))


def build(opts):  # pylint: disable=unused-argument
    """Builds full PDC firmware images"""
    # Not yet supported
    return 0


def bundle(opts):  # pylint: disable=unused-argument
    """Bundles PDC firmware images into an archive and uploads to GCS"""
    # Not yet supported
    info = firmware_pb2.FirmwareArtifactInfo()  # pylint: disable=no-member
    write_metadata(opts, info)
    return 0


def test(opts):
    """Runs all of the PDC repo unit tests"""
    metrics = firmware_pb2.FwTestMetricList()  # pylint: disable=no-member

    cmd = "scripts/run_tests.sh"

    try:
        subprocess.run(cmd, check=True, cwd=PLATFORM_PDC_DIR, env=os.environ)
    finally:
        with open(opts.metrics, "w", encoding="utf-8") as file:
            file.write(json_format.MessageToJson(metrics))  # type: ignore

    return 0


def main(argv):
    """Runs the pdc repo tests"""
    parser, _ = zephyr.scripts.firmware_builder_lib.create_arg_parser(
        build, bundle, test
    )
    opts = parser.parse_args(argv)

    if not hasattr(opts, "func"):
        print("Must select a valid sub command!")
        return -1

    # Run selected sub command function
    return opts.func(opts)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
