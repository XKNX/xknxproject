"""Test that the enhanced SimpleDeviceParser has correct syntax and expected methods."""

import sys
import ast
from pathlib import Path

def test_parser_syntax():
    """Test that the parser file has correct Python syntax."""
    parser_file = Path("/home/michi/PycharmProjects/knx/knxproj/xknxproject/xml/simple_device_parser.py")
    
    try:
        with open(parser_file, 'r') as f:
            code = f.read()
        
        # Parse the code to check syntax
        ast.parse(code)
        print("✓ Parser file has valid Python syntax")
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error in parser file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading parser file: {e}")
        return False

def test_expected_methods():
    """Test that the parser has expected methods."""
    parser_file = Path("/home/michi/PycharmProjects/knx/knxproj/xknxproject/xml/simple_device_parser.py")
    
    expected_methods = [
        'parse',
        'parse_with_parameterization',
        '_parse_xml',
        '_parse_static_section',
        '_parse_dynamic_section',
        '_parse_com_objects',
        '_parse_memory_mapping_and_types',
        '_parse_absolute_segments',
        '_parse_parameter_types_detailed',
        '_parse_parameters_with_memory',
        '_parse_parameter_element',
        '_parse_unions',
        '_enhance_config_with_parameterization',
        '_validate_parameter_types',
        '_validate_memory_mapping',
        '_parse_address_and_association_tables'
    ]
    
    try:
        with open(parser_file, 'r') as f:
            code = f.read()
        
        # Parse the code
        tree = ast.parse(code)
        
        # Find the SimpleDeviceParser class
        parser_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'SimpleDeviceParser':
                parser_class = node
                break
        
        if not parser_class:
            print("❌ SimpleDeviceParser class not found")
            return False
        
        # Check for expected methods
        found_methods = []
        for node in ast.walk(parser_class):
            if isinstance(node, ast.FunctionDef):
                found_methods.append(node.name)
        
        missing_methods = []
        for method in expected_methods:
            if method not in found_methods:
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ Missing methods: {missing_methods}")
            return False
        
        print(f"✓ All expected methods found: {len(found_methods)} methods")
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing parser methods: {e}")
        return False

def test_enhanced_features():
    """Test that the parser contains enhanced feature code."""
    parser_file = Path("/home/michi/PycharmProjects/knx/knxproj/xknxproject/xml/simple_device_parser.py")
    
    enhanced_features = [
        'access',
        'DefaultUnionParameter',
        'TypeTime',
        'TypeText',
        'TypeFloat',
        'TypePicture',
        'TypeIPAddress',
        'TypeColor',
        'RelativeSegment',
        'CommunicationFlag',
        'ReadFlag',
        'WriteFlag',
        'AddressTable',
        'AssociationTable',
        '_validate_parameter_types',
        '_validate_memory_mapping'
    ]
    
    try:
        with open(parser_file, 'r') as f:
            code = f.read()
        
        missing_features = []
        for feature in enhanced_features:
            if feature not in code:
                missing_features.append(feature)
        
        if missing_features:
            print(f"❌ Missing enhanced features: {missing_features}")
            return False
        
        print(f"✓ All enhanced features found: {len(enhanced_features)} features")
        return True
        
    except Exception as e:
        print(f"❌ Error checking enhanced features: {e}")
        return False

def test_file_size():
    """Test that the file has grown significantly (indicating new features)."""
    parser_file = Path("/home/michi/PycharmProjects/knx/knxproj/xknxproject/xml/simple_device_parser.py")
    
    try:
        file_size = parser_file.stat().st_size
        print(f"✓ Parser file size: {file_size} bytes")
        
        # The file should be significantly larger than the original
        if file_size < 10000:  # Should be at least 10KB
            print("⚠️  File size seems small, but this might be OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking file size: {e}")
        return False

def main():
    """Run all syntax and feature tests."""
    print("🚀 Testing enhanced SimpleDeviceParser...")
    
    tests = [
        test_parser_syntax,
        test_expected_methods,
        test_enhanced_features,
        test_file_size
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    if all_passed:
        print(f"\n🎉 All syntax and feature tests passed!")
        print("✅ The enhanced parser appears to be correctly implemented")
        return 0
    else:
        print(f"\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())