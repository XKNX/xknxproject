# (X)KNX Project

[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=f8b424)](https://github.com/pre-commit/pre-commit)
[![Discord](https://img.shields.io/discord/338619021215924227?color=7289da&label=Discord&logo=discord&logoColor=7289da)](https://discord.gg/bkZe9m4zvw)
[![codecov](https://codecov.io/gh/XKNX/xknxproject/branch/main/graph/badge.svg?token=LgPvZpKK3k)](https://codecov.io/gh/XKNX/xknxproject)

Extracts KNX projects and parses the underlying XML.

This project aims to provide a library that can be used to extract and parse KNX project files and read out useful information including
the group addresses, devices and their descriptions and possibly more.

Note: The specified KNX project file will be extracted to /tmp during the process. Once parsing is done all files will be deleted from /tmp again.

## Documentation

Currently, xknxproject supports extracting (password protected) ETS5 and ETS6 files and can obtain the following information from your project:

* Areas, Lines, Devices and their individual address
* CommunicationObjectInstance references for their devices (GA assignments)
* Group Addresses and their DPT type if set

Installation:

    pip install xknxproject

Usage:

    from xknxproject import KNXProj


    def main():
        """Extract and parse a KNX project file."""
        knxproj: KNXProj = KNXProj("path/to/your/file.knxproj", "optional_password")
        areas, group_addresses = knxproj.parse()
