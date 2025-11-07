#!/bin/bash
# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# cd to the directory containing this script.
cd "$(dirname "$(realpath -e "${BASH_SOURCE[0]}")")" || exit

# Set the Python Path to `platform/pdc/scripts`
export PYTHONPATH="${PWD}"

# Invoke pytest using vpython3 if available, or fall back to python3.
# If not using vpython, the user must ensure that pytest is available.
PYTHON=python3
if which vpython3; then
  PYTHON="vpython3"
fi

${PYTHON?} -m pytest -v "$@"
