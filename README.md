# (X)KNX Project

[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=f8b424)](https://github.com/pre-commit/pre-commit)
[![Discord](https://img.shields.io/discord/338619021215924227?color=7289da&label=Discord&logo=discord&logoColor=7289da)](https://discord.gg/bkZe9m4zvw)
[![codecov](https://codecov.io/gh/XKNX/xknxproject/branch/main/graph/badge.svg?token=LgPvZpKK3k)](https://codecov.io/gh/XKNX/xknxproject)

Extracts KNX projects and asynchronously parses the underlying XML.

This project aims to provide a library that can be used to extract and parse KNX project files and read out useful information including
the group addresses, devices and their descriptions and possibly more.

## Documentation

Currently, xknxproject supports extracting (password protected) ETS5 and ETS6 files and can obtain the following information from your project:

* Areas, Lines, Devices and their individual address
* CommunicationObjectInstance references for their devices (GA assignments)
* Group Addresses and their DPT type if set
* The application programs communication objects and their respective flags and the DPT Type

Caution: Loading a middle-sized project with this tool takes about 1.5 seconds. For bigger projects this might as well be >3s.

## Installation

In order to parse XML and to overcome the performance issues that parsing application programs with over 800k lines of XML has we use lxml.
lxml requires libxml2 to be installed in the underlying system. You can read more on their documentation on this topic.

    pip install xknxproject

## Usage

    import asyncio
    from xknxproject.models import KNXProject
    from xknxproject import KNXProj


    async def main():
        """Extract and parse a KNX project file."""
        knxproj: KNXProj = KNXProj("path/to/your/file.knxproj", "optional_password")
        project: KNXProject = await knxproj.parse()

    asyncio.run_until_complete(main())

The `KNXProject` is a typed dictionary and can be used just like a dictionary, or, exported as JSON.
You can find an example file (exported JSON) in our test suite under https://github.com/XKNX/xknxproject/tree/main/test/resources/stubs

The full type definition can be found here: https://github.com/XKNX/xknxproject/blob/main/xknxproject/models/knxproject.py

## TODOs / Ideas

- Parse location information (which device is in which room) - caution: not all devices may be mapped to a room
- Since parsing is rather expensive we could add a callback to inform the user (over the HA websocket) what the current steps are and what is being parsed. Might be cool for UX.
- Migrate remaining minidom logic to lxml
