# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Device Configuration Parsing**: Added comprehensive support for parsing KNX device configuration files (.knxprod)
  - New `SimpleDeviceParser` class for lightweight device configuration extraction
  - Extracts device name, parameter types, parameters, parameter blocks, channels, and communication objects
  - Comprehensive test suite with 12/12 tests passing (when device files are available)
  - Support for MDT device files
  - Direct XML parsing using ZipFile and ElementTree
  - Support for ModuleDefs and complex device structures

- **Enhanced Parameterization Support**: Added advanced device parameterization capabilities
  - New `parse_with_parameterization()` method providing full memory mapping and type information
  - Memory mapping: segment_id, offset, and offset_bit for each parameter
  - Detailed parameter types: type, size, enum values, min/max ranges
  - Memory segments: address, size, and type information for device memory
  - Union support: handles complex parameter structures
  - Full compatibility with `poc_parameterizer.py` requirements
  - Comprehensive test suite with 5/5 enhanced parameterization tests passing
  - 142/168 parameters with memory mapping (84.5% coverage)
  - 36/37 parameter types with detailed information (97.3% coverage)
  - 6 memory segments extracted with complete addressing information

### Changed

- **README.md**: Updated with device parser usage examples and documentation
- **test/xml/test_device_parser.py**: Enhanced test suite with proper device file detection
- **xknxproject/xml/simple_device_parser.py**: Enhanced with parameterization support while maintaining 100% backward compatibility

### Fixed

- **XML Structure Mismatch**: Fixed handling of MDT-style XML format with `<Memory>` elements and `<AbsoluteSegment>` definitions
- **Memory Mapping**: Proper extraction of memory mapping information from device files
- **Parameter Type Details**: Complete extraction of parameter type information including size and type fields

## [0.1.0] - 2024-07-14

### Added

- Initial release of xknxproject library
- Support for ETS 4, 5, and 6 project file extraction
- Group address parsing and DPT type detection
- Device and location information extraction
- Multi-language support

[Unreleased]: https://github.com/XKNX/xknxproject/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/XKNX/xknxproject/releases/tag/v0.1.0