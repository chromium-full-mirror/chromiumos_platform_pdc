# Usage

Googlers can follow go/installdocker to install Docker on gLinux.

## Build Container

Obtain the tool and GUI composer runtime from the
[dev.ti.com](https://dev.ti.com/gallery/view/USBPD/) website
(available to authorized Googlers only) and pass the paths of the
two downloaded files into the container build as arguments. They will
be automatically copied into the container at build time and
installed.

```bash
docker build \
    -t ti-cli-tool . \
    # Obtained from the TI website (proprietary software)
    # Note: these files must be under pdc/contrib/ti-docker for Docker
    #       to access them.
    --build-arg \
        TI_GCR=download/gcruntime-14.0.0-linux-x64-installer.run \
    --build-arg TI_TOMCAT=download/Tomcat_I_1.5.3_installer_linux.zip
```

Docker supports versioning the container images. You could create
multiple containers to cover different TI base firmwares, which are
bundled with, and tied to, the above Tomcat installers.

## Run Container

Once the container is built, it can be invoked as follows.

It is not necessary to rebuild the container each time.

```bash
docker run \
    # Mount the PDC repo directory
    -v ~/chromiumos/src/platform/pdc/:/pdc \
    ti-cli-tool:latest \
    # TI CLI args follow:
    #   -i is the input appconfig JSON
    #   -o is the TFU bundle output (creates a directory)
    #   -b (optional) path to the TFU base FW to modify. If not
    #      provided, the TFU base firmware bundled into the downloaded
    #      installer is used.
    -i /pdc/program/fatcat/moonstone/moonstone-GOOG0Q01-appconfig.json \
    -o /pdc/moonstone_out_tfu
```
