# Creating PDC Firmware Images

## Overview
PDC firmware images are comprised of 2 main parts:
1. Base firmware file
1. Configuration fragment file

These two files are combined using vendor specific tooling and processes to
create a PDC firmware file appropriate for flashing onto the PDC on an actual
laptop.

### Base Firmware File
The base firmware file is provided by the PDC vendor. The base firmware supports
one or more PDC chip types, but typically will not function correctly without a
configuration fragment applied.

### Configuration Fragment File
The configuration fragment file contains all the board level settings and power
delivery policy settings for a specific project variant.

This includes parameters:
* I2C address information for the EC to PDC and PDC to PMC I2C buses.
* Retimer information
* PD policy settings, such as default sink an source capabilities.

For additional details, refer to the [PDC Configuration Fragment
Files](./pdc_configuration_fragment_files.md).

### PDC Firmware Firmware Image File
The PDC Firmware Files file is a complete firmware image, combining a base
firmware file and a single PDC configuration fragment.

## TI Firmware Images
TI base firmware files are extracted using the TPS6699X Application
Customization Tool found on TI's Developer Zone portal.

TI refers to the configuration fragment files as `App Config` files, and are are
stored as JSON files, with the name suffix `*-appconfig.josn`.

Use the TPS6699X Application Customization Tool to upload the `App Config` and
apply to the corresponding base firmware file.

## Realtek Firmware Images
Base firmware files for Realtek are checked into the platform/pdc repository
under the [`firmware/realtek`](../firmware/realtek) directory.

Configuration fragment files are stored as binary files.

Follow the instructions provided in [Realtek Firmware Configuration
Tool](./rtk_fw_config.md) to create a full Realtek firmware image.
