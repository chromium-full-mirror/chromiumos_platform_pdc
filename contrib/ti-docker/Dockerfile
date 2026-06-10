# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

FROM ubuntu:noble-20260509.1

ARG TI_GCR
ARG TI_TOMCAT

RUN DEBIAN_FRONTEND=noninteractive \
    apt update && \
    apt install -y \
        unzip \
        nodejs \
        rsync \
        npm

COPY ${TI_GCR} /TI/gcruntime-installer.run
COPY ${TI_TOMCAT} /TI/tomcat-installer.zip
WORKDIR /TI

# Standardized install location of the GCR (GUI composer runtime) package.
# The installer tacks a version number on the gcruntime directory name like
# `gcruntime.v14`. Strip this version with `mv` below and use this as the
# path so it is consistent.
ENV GCR_DIR="/root/guicomposer/runtime/gcruntime/Tomcat_I/commandLine"

# Install Tomcat utility
RUN unzip -p tomcat-installer.zip > tomcat.run && \
    chmod +x tomcat.run && \
    ./tomcat.run \
         --choice local_gcr \
         --local_gcr /TI/gcruntime-installer.run \
         --mode unattended && \
    mv \
        /root/guicomposer/runtime/gcruntime.*/ \
        /root/guicomposer/runtime/gcruntime/ && \
    cd ${GCR_DIR} && \
    tr -d '\r' <linuxTFUExport.sh> linux_TFU_Script.sh

# Run once to install the required node modules. Temporarily make
# executeScript.js a no-op so only the install steps runs. (hacky)
RUN cd ${GCR_DIR} && \
    mv executeScript.js _executeScript.js && \
    touch executeScript.js && \
    /bin/bash ./linux_TFU_Script.sh && \
    mv _executeScript.js executeScript.js

WORKDIR ${GCR_DIR}
ENTRYPOINT ["node", "executeScript.js"]
