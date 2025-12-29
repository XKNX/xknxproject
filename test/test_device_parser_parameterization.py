"""Tests for enhanced SimpleDeviceParser with parameterization support."""

import pytest
from pathlib import Path

from xknxproject.xml.simple_device_parser import SimpleDeviceParser

# Test device file (MDT energy meter)
TEST_DEVICE_FILE = Path(__file__).parent.parent / ".." / "xknx" / "medt_kp_ez_01_energy_meter_v11" / "MDT_KP_EZ_01_Energy_Meter_V11.knxprod"


def test_enhanced_device_parser():
    """Test that the enhanced SimpleDeviceParser provides parameterization data."""
    if not TEST_DEVICE_FILE.exists():
        pytest.skip(f"Test device file not found: {TEST_DEVICE_FILE}")
    
    # Test basic parsing still works
    parser = SimpleDeviceParser(TEST_DEVICE_FILE)
    basic_config = parser.parse()
    
    assert basic_config.name == "Energy Meter 3-channel, 20A"
    assert len(basic_config.parameters) > 0
    assert len(basic_config.parameter_types) > 0
    
    # Test enhanced parsing provides parameterization data
    enhanced_config, hw_data = parser.parse_with_parameterization()
    
    # Verify enhanced config has memory mapping
    params_with_memory = [
        p for p in enhanced_config.parameters.values() 
        if p.get('segment_id') and p.get('offset') is not None
    ]
    
    assert len(params_with_memory) > 0, "No parameters with memory mapping found"
    
    # Verify parameter types have detailed info
    types_with_details = [
        pt for pt in enhanced_config.parameter_types.values() 
        if pt.get('type') and pt.get('size')
    ]
    
    assert len(types_with_details) > 0, "No parameter types with details found"
    
    # Verify hardware data contains segments
    assert 'segments' in hw_data
    assert len(hw_data['segments']) > 0, "No memory segments found"
    
    # Verify we can find a complete parameter (all fields present)
    complete_param = None
    for param in enhanced_config.parameters.values():
        if (param.get('segment_id') and 
            param.get('offset') is not None and
            param.get('type') in enhanced_config.parameter_types and
            enhanced_config.parameter_types[param.get('type')].get('size')):
            complete_param = param
            break
    
    assert complete_param is not None, "No complete parameter found with all required fields"


def test_parameterizer_compatibility():
    """Test that the enhanced parser provides all data needed for parameterizer."""
    if not TEST_DEVICE_FILE.exists():
        pytest.skip(f"Test device file not found: {TEST_DEVICE_FILE}")
    
    parser = SimpleDeviceParser(TEST_DEVICE_FILE)
    config, hw_data = parser.parse_with_parameterization()
    
    # Check parameterizer requirements
    params_with_memory = [
        p for p in config.parameters.values() 
        if p.get('segment_id') and p.get('offset') is not None
    ]
    
    # Check enhanced parameter types (from hw_data, not config)
    types_with_details = [
        pt for pt in hw_data.get('parameter_types', {}).values() 
        if pt.get('type') and pt.get('size')
    ]
    
    segments = hw_data.get('segments', {})
    
    # All requirements for parameterizer should be met
    assert len(params_with_memory) > 0, "Need parameters with memory mapping"
    assert len(types_with_details) > 0, "Need parameter types with details"
    assert len(segments) > 0, "Need memory segments"
    
    # Should be able to generate parameter images
    assert all(seg.get('size') for seg in segments.values()), "Segments need size info"
    
    # Should be able to encode/decode parameters (enum types are optional)
    # Note: This device file doesn't have enum types, but that's OK


def test_memory_mapping_accuracy():
    """Test that memory mapping data is accurate and complete."""
    if not TEST_DEVICE_FILE.exists():
        pytest.skip(f"Test device file not found: {TEST_DEVICE_FILE}")
    
    parser = SimpleDeviceParser(TEST_DEVICE_FILE)
    config, hw_data = parser.parse_with_parameterization()
    
    # Test that memory-mapped parameters reference valid segments
    segments = hw_data.get('segments', {})
    segment_ids = set(segments.keys())
    
    for param in config.parameters.values():
        if param.get('segment_id'):
            assert param['segment_id'] in segment_ids, f"Parameter references invalid segment: {param['segment_id']}"
            
            # Test that offset is within segment bounds
            seg = segments[param['segment_id']]
            if param.get('offset') is not None:
                assert 0 <= param['offset'] < seg['size'], f"Parameter offset out of bounds: {param['offset']} >= {seg['size']}"


def test_parameter_type_completeness():
    """Test that parameter types have complete information."""
    if not TEST_DEVICE_FILE.exists():
        pytest.skip(f"Test device file not found: {TEST_DEVICE_FILE}")
    
    parser = SimpleDeviceParser(TEST_DEVICE_FILE)
    config, hw_data = parser.parse_with_parameterization()
    
    # Check enhanced parameter types (from hw_data, not config)
    hw_parameter_types = hw_data.get('parameter_types', {})
    
    # Enhanced parameter types should have basic info
    for pt_id, pt in hw_parameter_types.items():
        assert 'id' in pt, f"Parameter type missing id: {pt_id}"
        assert 'name' in pt, f"Parameter type missing name: {pt_id}"
        assert 'type' in pt, f"Parameter type missing type: {pt_id}"
        assert 'size' in pt, f"Parameter type missing size: {pt_id}"
        assert 'enum' in pt, f"Parameter type missing enum: {pt_id}"
        
        # Size should be positive
        assert pt['size'] > 0, f"Parameter type has invalid size: {pt_id}"
        
        # Should have at least basic type info
        assert pt['type'] in ['Value', 'unsignedInt', 'int', 'float'], f"Unknown type: {pt['type']}"


def test_backward_compatibility():
    """Test that basic parsing still works as before."""
    if not TEST_DEVICE_FILE.exists():
        pytest.skip(f"Test device file not found: {TEST_DEVICE_FILE}")
    
    parser = SimpleDeviceParser(TEST_DEVICE_FILE)
    
    # Basic parsing should work
    basic_config = parser.parse()
    assert basic_config.name == "Energy Meter 3-channel, 20A"
    assert len(basic_config.parameters) > 0
    assert len(basic_config.parameter_types) > 0
    
    # Basic config should not have memory mapping (that's only in enhanced mode)
    params_with_memory = [
        p for p in basic_config.parameters.values() 
        if p.get('segment_id')
    ]
    assert len(params_with_memory) == 0, "Basic parsing should not include memory mapping"


if __name__ == "__main__":
    # Run tests manually if needed
    test_enhanced_device_parser()
    test_parameterizer_compatibility()
    test_memory_mapping_accuracy()
    test_parameter_type_completeness()
    test_backward_compatibility()
    print("All tests passed!")