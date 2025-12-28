"""Tests for KNX device configuration parsers."""

import pytest
from pathlib import Path
from xknxproject.xml.simple_device_parser import SimpleDeviceParser


# Test device files
# NOTE: These files are proprietary and not included in the repository.
# They can be obtained from: https://www.mdt-group.com/for-professionals/downloads/ets-product-data.html
# Tests will skip if files are not available
TEST_DEVICE_FILES = {
    "energy_meter": Path("test/resources/device_files/MDT_KP_EZ_01_Energy_Meter_V11.knxprod"),
    "universal_actuator": Path("test/resources/device_files/MDT_KP_AKU_03_Universal_Actuator_V41a.knxprod"),
    "scn_da64": Path("test/resources/device_files/SCN-DA64x-04_MDT_KP_V40a.knxprod"),
}

# Primary test file (check if available)
PRIMARY_DEVICE_FILE = TEST_DEVICE_FILES["energy_meter"] if TEST_DEVICE_FILES["energy_meter"].exists() else None


@pytest.mark.skipif(PRIMARY_DEVICE_FILE is None, reason="Primary device file not available")
class TestSimpleDeviceParser:
    """Test the simple device configuration parser with real device file."""

    def test_parse_device_file(self):
        """Test parsing a complete device configuration file."""
        parser = SimpleDeviceParser(PRIMARY_DEVICE_FILE)
        config = parser.parse()
        
        # Basic assertions
        assert config is not None
        assert isinstance(config.name, str)
        assert len(config.name) > 0
        
        # Check that we get expected data structures
        assert isinstance(config.parameter_types, dict)
        assert isinstance(config.parameters, dict)
        assert isinstance(config.parameter_blocks, dict)
        assert isinstance(config.channels, dict)
        assert isinstance(config.com_objects, dict)

    def test_device_name(self):
        """Test that device name is extracted correctly."""
        parser = SimpleDeviceParser(PRIMARY_DEVICE_FILE)
        config = parser.parse()
        
        assert config.name == "Energy Meter 3-channel, 20A"

    def test_parameter_types(self):
        """Test that parameter types are extracted."""
        parser = SimpleDeviceParser(PRIMARY_DEVICE_FILE)
        config = parser.parse()
        
        # Should have many parameter types
        assert len(config.parameter_types) > 30
        
        # Check structure of a parameter type
        first_pt_id = next(iter(config.parameter_types.keys()))
        first_pt = config.parameter_types[first_pt_id]
        assert 'id' in first_pt
        assert 'name' in first_pt

    def test_parameters(self):
        """Test that parameters are extracted."""
        parser = SimpleDeviceParser(PRIMARY_DEVICE_FILE)
        config = parser.parse()
        
        # Should have many parameters
        assert len(config.parameters) > 100
        
        # Check structure of a parameter
        first_p_id = next(iter(config.parameters.keys()))
        first_p = config.parameters[first_p_id]
        assert 'name' in first_p
        assert 'type' in first_p
        assert 'value' in first_p

    def test_parameter_blocks(self):
        """Test that parameter blocks are extracted correctly."""
        parser = SimpleDeviceParser(PRIMARY_DEVICE_FILE)
        config = parser.parse()
        
        # Should have parameter blocks
        assert len(config.parameter_blocks) >= 7
        
        # Test specific expected parameter blocks
        expected_blocks = [
            "M-0083_A-0112-11-0C0A_MD-1_PB-1",
            "M-0083_A-0112-11-0C0A_MD-1_PB-2",
            "M-0083_A-0112-11-0C0A_MD-2_PB-1",
        ]
        
        for pb_id in expected_blocks:
            assert pb_id in config.parameter_blocks
            pb = config.parameter_blocks[pb_id]
            assert 'name' in pb
            assert 'id' in pb
            assert pb['id'] == pb_id

    def test_channels(self):
        """Test that channels are extracted correctly."""
        parser = SimpleDeviceParser(PRIMARY_DEVICE_FILE)
        config = parser.parse()
        
        # Should have channels
        assert len(config.channels) >= 2
        
        # Test specific expected channels
        expected_channels = [
            "M-0083_A-0112-11-0C0A_CH-1",
            "M-0083_A-0112-11-0C0A_CH-2",
        ]
        
        for ch_id in expected_channels:
            assert ch_id in config.channels
            channel = config.channels[ch_id]
            assert 'name' in channel
            assert 'text' in channel
            assert 'parameter_blocks' in channel
            assert isinstance(channel['parameter_blocks'], list)

    def test_communication_objects(self):
        """Test that communication objects are extracted."""
        parser = SimpleDeviceParser(PRIMARY_DEVICE_FILE)
        config = parser.parse()
        
        # Communication objects should be parsed
        assert isinstance(config.com_objects, dict)





@pytest.mark.skipif(PRIMARY_DEVICE_FILE is None, reason="Primary device file not available")
class TestMultipleDeviceFiles:
    """Test device parser with multiple different KNX devices."""

    @pytest.mark.parametrize("device_name,device_file", [
        ("energy_meter", TEST_DEVICE_FILES["energy_meter"]),
        ("universal_actuator", TEST_DEVICE_FILES["universal_actuator"]),
        ("scn_da64", TEST_DEVICE_FILES["scn_da64"]),
    ])
    def test_parse_multiple_devices(self, device_name, device_file):
        """Test that parser works with different device types."""
        if not device_file.exists():
            pytest.skip(f"Device file {device_name} not available")
            
        parser = SimpleDeviceParser(device_file)
        config = parser.parse()
        
        # All devices should parse successfully
        assert config is not None
        assert isinstance(config.name, str)
        assert len(config.name) > 0
        
        # All devices should have basic structure
        assert isinstance(config.parameter_types, dict)
        assert isinstance(config.parameters, dict)
        assert isinstance(config.parameter_blocks, dict)
        assert isinstance(config.channels, dict)
        
        # Log device info for debugging
        print(f"✓ {device_name}: {config.name}")
        print(f"  - Parameters: {len(config.parameters)}")
        print(f"  - Parameter Blocks: {len(config.parameter_blocks)}")
        print(f"  - Channels: {len(config.channels)}")


class TestDeviceParserErrorHandling:
    """Test error handling for device parsers."""

    def test_nonexistent_file(self):
        """Test handling of nonexistent file."""
        nonexistent_file = Path("/tmp/nonexistent.knxprod")
        
        with pytest.raises((FileNotFoundError, ValueError)):
            parser = SimpleDeviceParser(nonexistent_file)
            parser.parse()

    def test_invalid_file_path(self):
        """Test handling of invalid file path."""
        with pytest.raises(TypeError):
            SimpleDeviceParser(None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])