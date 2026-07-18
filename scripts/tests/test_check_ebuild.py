# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test the cehck_ebuild.py script"""

import check_ebuild
import pytest


def test_check_package_consistency():
    # This function throws AssertionErrors for found errors and does nothing
    # on success.

    # Successful path - equal config name everywhere
    check_ebuild.check_package_consistency(
        "rts5453-GOOGXY00-1.2.3-r1",
        "rts5453_GOOGXY00",
        {
            "hash_file": {
                "ver": (1, 2, 3),
                "config_name": "GOOGXY00",
            },
            "fw_binary": (1, 2, 3, "GOOGXY00"),
        },
    )

    # Successful path - config name's ID and variant is equal but the package
    # payload has a different revision in the config name
    check_ebuild.check_package_consistency(
        "rts5453-GOOGXY00-1.2.3-r1",
        "rts5453_GOOGXY00",
        {
            "hash_file": {
                "ver": (1, 2, 3),
                "config_name": "GOOGXY10",
            },
            "fw_binary": (1, 2, 3, "GOOGXY10"),
        },
    )

    # Successful path - same as above, but the hash file's config name is not
    # specified. This is allowed since RTK hash files do not require the config
    # name.
    check_ebuild.check_package_consistency(
        "rts5453-GOOGXY00-1.2.3-r1",
        "rts5453_GOOGXY00",
        {
            "hash_file": {
                "ver": (1, 2, 3),
                "config_name": None,
            },
            "fw_binary": (1, 2, 3, "GOOGXY10"),
        },
    )

    #
    # Failure paths
    #

    # Hash file version does not match package title
    with pytest.raises(AssertionError, match="Hash file version"):
        check_ebuild.check_package_consistency(
            "rts5453-GOOGXY00-1.2.3-r1",
            "rts5453_GOOGXY00",
            {
                "hash_file": {
                    "ver": (1, 2, 9),
                    "config_name": "GOOGXY00",
                },
                "fw_binary": (1, 2, 3, "GOOGXY00"),
            },
        )

    # FW binary version does not match package title
    with pytest.raises(AssertionError, match="FW binary version"):
        check_ebuild.check_package_consistency(
            "rts5453-GOOGXY00-1.2.3-r1",
            "rts5453_GOOGXY00",
            {
                "hash_file": {
                    "ver": (1, 2, 3),
                    "config_name": "GOOGXY00",
                },
                "fw_binary": (1, 2, 9, "GOOGXY00"),
            },
        )

    # Hash file config name does not match package title
    with pytest.raises(AssertionError, match="Hash file has a config name"):
        check_ebuild.check_package_consistency(
            "rts5453-GOOGXY00-1.2.3-r1",
            "rts5453_GOOGXY00",
            {
                "hash_file": {
                    "ver": (1, 2, 3),
                    "config_name": "GOOGXY01",
                },
                "fw_binary": (1, 2, 3, "GOOGXY00"),
            },
        )

    # FW binary config name does not match package title
    with pytest.raises(AssertionError, match="FW binary config name"):
        check_ebuild.check_package_consistency(
            "rts5453-GOOGXY00-1.2.3-r1",
            "rts5453_GOOGXY00",
            {
                "hash_file": {
                    "ver": (1, 2, 3),
                    "config_name": None,
                },
                "fw_binary": (1, 2, 3, "GOOGXY01"),
            },
        )

    # Package title should use '0' as the config name revision, even if a
    # different config revision is inside.
    with pytest.raises(AssertionError, match="Config name in package title"):
        check_ebuild.check_package_consistency(
            "rts5453-GOOGXY10-1.2.3-r1",
            "rts5453_GOOGXY00",
            {
                "hash_file": {
                    "ver": (1, 2, 3),
                    "config_name": "GOOGXY00",
                },
                "fw_binary": (1, 2, 3, "GOOGXY00"),
            },
        )

    # The config name in the package title should appear in the CBFS filenames.
    with pytest.raises(AssertionError, match="CBFS file name"):
        check_ebuild.check_package_consistency(
            "rts5453-GOOGXY00-1.2.3-r1",
            "rts5453_GOOGXY01",
            {
                "hash_file": {
                    "ver": (1, 2, 3),
                    "config_name": "GOOGXY00",
                },
                "fw_binary": (1, 2, 3, "GOOGXY00"),
            },
        )

    # The embedded FW binary config name and hash file config name must be
    # exact matches
    with pytest.raises(
        AssertionError, match="Hash file config name and FW binary config"
    ):
        check_ebuild.check_package_consistency(
            "rts5453-GOOGXY00-1.2.3-r1",
            "rts5453_GOOGXY00",
            {
                "hash_file": {
                    "ver": (1, 2, 3),
                    "config_name": "GOOGXY10",
                },
                "fw_binary": (1, 2, 3, "GOOGXY20"),
            },
        )
