# (X)KNX Project

[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=f8b424)](https://github.com/pre-commit/pre-commit)
[![Discord](https://img.shields.io/discord/338619021215924227?color=7289da&label=Discord&logo=discord&logoColor=7289da)](https://discord.gg/bkZe9m4zvw)
[![codecov](https://codecov.io/gh/XKNX/xknxproject/branch/main/graph/badge.svg?token=LgPvZpKK3k)](https://codecov.io/gh/XKNX/xknxproject)

Extracts KNX projects and parses the underlying XML.

This project aims to provide a library that can be used to extract and parse KNX project files and read out useful information including the group addresses, devices, their descriptions and possibly more.

## Documentation

Currently, xknxproject supports extracting (password protected) ETS 4, 5 and 6 projects and can obtain the following information:

* Areas, Lines, Devices and their individual address and channels
* CommunicationObjectInstance references for their devices (GA assignments)
* Group Addresses and their DPT type if set
* The application programs communication objects, their respective flags and the DPT Type
* Location information of devices (in which rooms they are)
* Functions assigned to rooms

Caution: Loading a middle-sized project with this tool takes about 1.5 seconds. For bigger projects this might as well be >3s.

Not all supported languages are included in project / application data. If the configured language is not found, the default language will be used - which is manufacturer / product dependent.

## Installation

`pip install xknxproject`

## Usage

```python
"""Extract and parse a KNX project file."""

from xknxproject.models import KNXProject
from xknxproject import XKNXProj


knxproj: XKNXProj = XKNXProj(
    path="path/to/your/file.knxproj",
    password="password",  # optional
    language="de-DE",  # optional
)
project: KNXProject = knxproj.parse()
```

The resulting `KNXProject` is a typed dictionary and can be used just like a dictionary, or can be exported as JSON.
You can find an example file (exported JSON) in our test suite under https://github.com/XKNX/xknxproject/tree/main/test/resources/stubs

The full type definition can be found here: https://github.com/XKNX/xknxproject/blob/main/xknxproject/models/knxproject.py

### Application program definitions

`parse_application_programs()` returns the full definition of every application
program used by a device of the project: all channel and module definitions and
all communication objects, including those the project does not link to a group
address. Identifiers are relative to the application program id with module
instance parts removed (`MD-2_CH-1`, `MD-2_O-2-35_R-65`), so they match the
instance identifiers of the project output after stripping the module instance.
Channel membership in a definition is structural: an object belongs to every
channel whose dynamic tree references it, including through module
instantiation; the `channel` of an instance from `parse()` is authoritative for
that instance.

```python
programs = knxproj.parse_application_programs()
program = programs["M-0083_A-013A-32-DCC1"]
program["identity"]["application_version"]  # 50
program["channels"]["MD-2_CH-1"]["object_ids"]  # ["MD-2_O-2-35_R-65", ...]
```

The helpers in `xknxproject.util` connect the project output to these definitions:

* `instance_definition_id()` turns the identifier of a channel or communication object instance from `parse()` into the key of the definition (`channels` or `objects`).
* `object_channel_id()` returns the channel an object definition belongs to. For an object listed by several channels, a channel of the module that defines the object is preferred.
* `canonical_application_id()` returns the same id for rebranded (OEM) copies of one application program.
* `linked_object_definitions()` returns the object definitions the devices of a project link to group addresses, by application program id.

```python
from xknxproject.util import (
    canonical_application_id,
    instance_definition_id,
    linked_object_definitions,
    object_channel_id,
)

project = knxproj.parse()
programs = knxproj.parse_application_programs()
for application_id, object_ids in linked_object_definitions(project).items():
    definition = programs[application_id]
    canonical_id = canonical_application_id(
        application_id, definition["identity"]["original_manufacturer_id"]
    )
    for object_id in object_ids:
        channel_id = object_channel_id(definition, definition["objects"][object_id])
```

For a single instance, `instance_definition_id(instance_id, application_id, "O")` returns the key in `definition["objects"]`; use `"CH"` for the key in `definition["channels"]`.

The type definition is in `xknxproject/models/application_program.py`; example
output is in `test/resources/stubs/application_programs/`.
