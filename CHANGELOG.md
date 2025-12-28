# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Device Configuration Parsing**: Added support for parsing KNX device configuration files (.knxprod)
  - New `SimpleDeviceParser` class for lightweight device configuration extraction
  - Extracts device name, parameter types, parameters, parameter blocks, channels, and communication objects
  - Comprehensive test suite with 12/12 tests passing (when device files are available)
  - Support for MDT
  - Direct XML parsing using ZipFile and ElementTree
  - Support for ModuleDefs and complex device structures

### Changed

- **README.md**: Updated with device parser usage examples and documentation
- **test/xml/test_device_parser.py**: Enhanced test suite with proper device file detection

## [0.1.0] - 2024-07-14

### Added

- Initial release of xknxproject library
- Support for ETS 4, 5, and 6 project file extraction
- Group address parsing and DPT type detection
- Device and location information extraction
- Multi-language support

[Unreleased]: https://github.com/XKNX/xknxproject/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/XKNX/xknxproject/releases/tag/v0.1.0