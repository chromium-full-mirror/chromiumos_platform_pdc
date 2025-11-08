#!/usr/bin/env vpython3
# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Script for searching Realtek PDC bugs for firmware images

Run outside the chroot and requires that go/bugged is installed on your system.
"""

import csv
import io
import subprocess
import sys


# Saved search ID:
# "(hotlistid:5431907 or componentid:1463948) attachmentcount>=1"
rtk_saved_search_id = "7070627"


def main():
    """Generate a list of issues with attachments matching .bin or .docx"""

    cmd = [
        "bugged",
        "saved-search",
        rtk_saved_search_id,
        "--columns",
        "issue",
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)

    issues_string = result.stdout.decode("utf-8")

    issue_file = io.StringIO(issues_string)
    reader = csv.DictReader(issue_file)
    issues = list(reader)

    print(f"Processing {len(issues)} issues")

    # Find attachments on each issue
    for issue in issues:
        bug = issue["issue"]
        cmd = [
            "bugged",
            "list-attachments",
            bug,
            "--colsep",
            ",",
            "--columns",
            "url,content-type,filename,comment-number",
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)

        attachments_string = result.stdout.decode("utf-8")

        attachments_file = io.StringIO(attachments_string)
        reader = csv.DictReader(attachments_file)
        attachments = list(reader)

        # First check for binary files
        for attachment in attachments:
            if (
                "octet-stream" in attachment["content-type"]
                and ".bin" in attachment["filename"]
            ):
                if not "attachments" in issue:
                    issue["attachments"] = []

                issue["attachments"].append(attachment)

        # 2nd pass for office document files so the output is segregated
        for attachment in attachments:
            if "officedocument" in attachment["content-type"]:
                if not "attachments" in issue:
                    issue["attachments"] = []

                issue["attachments"].append(attachment)

    for issue in issues:
        if "attachments" in issue:
            bug = issue["issue"]
            print(f"https://b.corp.google.com/issues/{bug}:")
            for attachment in issue["attachments"]:
                num = attachment["comment-number"]
                filename = attachment["filename"]
                print(f"    http://b/{bug}#comment{num}: {filename}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
