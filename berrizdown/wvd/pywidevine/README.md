# pywidevinex

## Features

- 🚀 Seamless Installation via [pip](#installation)
- 🛡️ Robust Security with message signature verification
- 🙈 Privacy Mode with Service Certificates
- 🌐 Servable CDM API Server and Client with Authentication
- 📦 Custom provision serialization format (WVD v2)
- 🧰 Create, parse, or convert PSSH headers with ease
- 🗃️ User-friendly YAML configuration
- ❤️ Forever FOSS!

## Installation

```shell
$ pip install pywidevinex
```

> **Note**
If pip gives you a warning about a path not being in your PATH environment variable then promptly add that path then
close all open command prompt/terminal windows, or `pywidevinex` CLI won't work as it will not be found.

Voilà 🎉 — You now have the `pywidevinex` package installed!  
You can now import pywidevinex in scripts ([see below](#usage)).  
A command-line interface is also available, try `pywidevinex --help`.

## Usage

The following is a minimal example of using pywidevinex in a script to get a License for Bitmovin's
Art of Motion Demo.

```py
from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH

import requests

# prepare pssh
pssh = PSSH("AAAAW3Bzc2gAAAAA7e+LqXnWSs6jyCfc1R0h7QAAADsIARIQ62dqu8s0Xpa7z2FmMPGj2hoNd2lkZXZpbmVfdGVzdCIQZmtqM2xqYVNkZmFsa3IzaioCSEQyAA==")

# load device
device = Device.load("C:/Path/To/A/Provision.wvd")

# load cdm
cdm = Cdm.from_device(device)

# open cdm session
session_id = cdm.open()

# get license challenge
challenge = cdm.get_license_challenge(session_id, pssh)

# send license challenge (assuming a generic license server SDK with no API front)
licence = requests.post("https://...", data=challenge)
licence.raise_for_status()

# parse license challenge
cdm.parse_license(session_id, licence.content)

# print keys
for key in cdm.get_keys(session_id):
    print(f"[{key.type}] {key.kid.hex}:{key.key.hex()}")

# close session, disposes of session data
cdm.close(session_id)
```

> **Note**
> There are various features not shown in this specific example like:
>
> - Privacy Mode
> - Setting Service Certificates
> - Remote CDMs and Serving
> - Choosing a License Type to request
> - Creating WVD files
> - and much more!
>
> Take a look at the methods available in the [Cdm class](/pywidevine/cdm.py) and their doc-strings for
> further information. For more examples see the [CLI functions](/pywidevine/main.py) which uses a lot
> of previously mentioned features.

## Disclaimer

1. This project requires a valid Google-provisioned Private Key and Client Identification blob which are not
   provided by this project.
2. Public test provisions are available and provided by Google to use for testing projects such as this one.
3. License Servers have the ability to block requests from any provision, and are likely already blocking test
   provisions on production endpoints.
4. This project does not condone piracy or any action against the terms of the DRM systems.
5. All efforts in this project have been the result of Reverse-Engineering, Publicly available research, and Trial
   & Error.

## Licensing

This software is licensed under the terms of [GNU General Public License, Version 3.0](LICENSE).  
You can find a copy of the license in the LICENSE file in the root folder.

- Widevine Icon &copy; Google.
- Props to the awesome community for their shared research and insight into the Widevine Protocol and Key Derivation.

* * *

© rlaphoenix 2022-2023 \
DevLARLEY 2025-2025
