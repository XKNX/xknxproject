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
every communication object reference (ComObjectRef merged with its ComObject),
including those the project does not link to a group address. It is a second
pass over the project file, separate from `parse()`; texts follow the
`language` passed to `XKNXProj`.

The result has an `info` block (`language_code`, `xknxproject_version`) and the
definitions in `application_programs`, keyed by application program id - the
same id as `device["application"]` of `parse()`. An application program that
can not be read is skipped with a warning, including malformed XML and ZIP
member checksum or decompression errors. Errors in the project data or the
archive itself still abort the call.

Identifiers are relative to the application program id with module instance
parts removed (`MD-2_CH-1`, `MD-2_O-2-35_R-65`). `instance_definition_id()`
maps the identifiers of `parse()` to them: it removes the device address
(`1.1.1/`), the application id prefix of ETS 4 projects and the module
instance parts. Channel membership in a definition is structural: an object
belongs to every channel whose dynamic tree references it, including through
module instantiation; the `channel` of an instance from `parse()` is
authoritative for that instance.

For `test/resources/module-definition-test.knxproj` with `language="De"`:

```python
from xknxproject import XKNXProj

knxproj = XKNXProj("test/resources/module-definition-test.knxproj", language="De")
result = knxproj.parse_application_programs()
result["info"]["language_code"]  # "de-DE"
program = result["application_programs"]["M-0083_A-013A-32-DCC1"]
program["identity"]["application_version"]  # 50
program["channels"]["MD-2_CH-1"]["object_ids"]  # ["MD-2_O-2-35_R-65", ...]
```

The helpers in `xknxproject.util` connect the project output to these
definitions:

* `instance_definition_id()` turns the identifier of a channel or communication
  object instance from `parse()` into the key of the definition (`channels` or
  `objects`).
* `object_channel_id()` returns the channel an object definition belongs to. For
  an object listed by several channels, a channel of the module that defines
  the object is preferred. Prefer the `channel` of an instance from `parse()`
  when you have one.
* `canonical_application_id()` returns the same id for rebranded (OEM) copies of
  one application program; `application_id_original_manufacturer()` reads the
  original manufacturer from the `-Oxxxx` suffix of an application id.
* `linked_object_definitions()` returns the definition ids the devices of a
  project link to group addresses, by application program id. It derives ids
  from the project without checking the definitions. Programs or objects may
  be absent from the definition result, so check both lookups:

```python
from xknxproject.util import (
    canonical_application_id,
    linked_object_definitions,
    object_channel_id,
)

project = knxproj.parse()
programs = knxproj.parse_application_programs()["application_programs"]
for application_id, object_ids in linked_object_definitions(project).items():
    definition = programs.get(application_id)
    if definition is None:
        continue
    canonical_id = canonical_application_id(
        application_id, definition["identity"]["original_manufacturer_id"]
    )
    for object_id in sorted(object_ids):
        object_definition = definition["objects"].get(object_id)
        if object_definition is None:
            continue
        channel_id = object_channel_id(definition, object_definition)
        print(canonical_id, object_id, channel_id)
```

For a single instance, `instance_definition_id(instance_id, application_id, "O")`
returns the key in `definition["objects"]`; use `"CH"` for the key in
`definition["channels"]`.

The type definition is in `xknxproject/models/application_program.py`. The
stubs in `test/resources/stubs/application_programs/` hold complete example
output for selected programs and a digest (identity, counts and checksum) for
every program of the test projects.
