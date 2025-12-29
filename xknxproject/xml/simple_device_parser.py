"""Simple parser for KNX device configuration files.

This parser provides a lightweight alternative to the full ApplicationProgramLoader
for extracting device configuration information directly from .knxprod files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from zipfile import ZipFile
from typing import Any, Dict, Tuple, Optional
from xml.etree import ElementTree

from xknxproject.zip.extractor import extract
from xknxproject.loader.hardware_parameterization_loader import HardwareParameterizationLoader

_LOGGER = logging.getLogger("xknxproject.log")


class SimpleDeviceConfig:
    """Simple container for device configuration data."""

    def __init__(self):
        self.name: str = ""
        self.parameter_types: dict[str, Any] = {}
        self.parameters: dict[str, Any] = {}
        self.parameter_blocks: dict[str, Any] = {}
        self.channels: dict[str, Any] = {}
        self.com_objects: dict[str, Any] = {}


class SimpleDeviceParser:
    """Simple parser for KNX device configuration files."""

    def __init__(self, device_file_path: str | Path):
        """Initialize simple device parser.
        
        Args:
            device_file_path: Path to the device configuration file (.knxprod)
        """
        self.device_file_path = Path(device_file_path)
        
    def parse(self) -> SimpleDeviceConfig:
        """Parse the device configuration file.
        
        Returns:
            SimpleDeviceConfig: Extracted device configuration
        """
        config = SimpleDeviceConfig()
        
        try:
            with ZipFile(self.device_file_path, mode="r") as zip_archive:
                return self._parse_xml(zip_archive, config)
        except Exception as e:
            _LOGGER.error("Failed to parse device configuration: %s", e)
            raise
            
    def _parse_xml(self, zip_archive: ZipFile, config: SimpleDeviceConfig) -> SimpleDeviceConfig:
        """Parse XML content from device file."""
        # Find application program XML files
        # Look for files that are likely application programs (not Catalog.xml, Hardware.xml)
        app_program_files = []
        for path in zip_archive.namelist():
            if (path.startswith('M-') and 
                path.endswith('.xml') and 
                not path.endswith('Catalog.xml') and 
                not path.endswith('Hardware.xml')):
                app_program_files.append(path)
        
        if not app_program_files:
            raise ValueError("No application program files found in device configuration")
        
        # Use the first application program file
        app_program_path = app_program_files[0]
        _LOGGER.info("Using application program file: %s", app_program_path)
        app_program_file = app_program_file = zip_archive.open(app_program_path)
        
        try:
            tree = ElementTree.parse(app_program_file)
            root = tree.getroot()
            ns = {'knx': root.tag.split('}')[0].strip('{')}
            
            # Extract application program name
            app_prog = root.find('knx:ManufacturerData/knx:Manufacturer/knx:ApplicationPrograms/knx:ApplicationProgram', ns)
            if app_prog is not None:
                config.name = app_prog.get('Name', 'Unknown')
                
                # Parse static section
                self._parse_static_section(app_prog, ns, config)
                
                # Parse dynamic section
                self._parse_dynamic_section(app_prog, ns, config)
                
                # Parse communication objects
                self._parse_com_objects(root, ns, config)
            
            return config
            
        finally:
            app_program_file.close()
            
    def _parse_static_section(self, app_prog: ElementTree.Element, ns: dict[str, str], config: SimpleDeviceConfig) -> None:
        """Parse static section (parameter types, parameters, etc.)."""
        static = app_prog.find('knx:Static', ns)
        if static is None:
            return
            
        # Parse parameter types
        param_types = static.find('knx:ParameterTypes', ns)
        if param_types is not None:
            for pt_elem in param_types.findall('knx:ParameterType', ns):
                pt_id = pt_elem.get('Id', '')
                pt_name = pt_elem.get('Name', pt_id)
                config.parameter_types[pt_id] = {
                    'name': pt_name,
                    'id': pt_id
                }
        
        # Parse parameters
        params = static.find('knx:Parameters', ns)
        if params is not None:
            for p_elem in params.findall('knx:Parameter', ns):
                p_id = p_elem.get('Id', '')
                p_name = p_elem.get('Name', p_id)
                p_type = p_elem.get('ParameterType', '')
                p_value = p_elem.get('Value', '')
                
                config.parameters[p_id] = {
                    'name': p_name,
                    'type': p_type,
                    'value': p_value
                }
        
        # Parse segments
        code = static.find('knx:Code', ns)
        if code is not None:
            segments = []
            for seg_elem in code.findall('knx:AbsoluteSegment', ns):
                seg_id = seg_elem.get('Id', '')
                address = seg_elem.get('Address', '')
                size = seg_elem.get('Size', '')
                segments.append({
                    'id': seg_id,
                    'address': address,
                    'size': size
                })
            config.segments = segments
            
    def _parse_dynamic_section(self, app_prog: ElementTree.Element, ns: dict[str, str], config: SimpleDeviceConfig) -> None:
        """Parse dynamic section (parameter blocks, channels, etc.)."""
        dynamic = app_prog.find('knx:Dynamic', ns)
        if dynamic is None:
            return
            
        # Parse parameter blocks from ModuleDefs (they're not in Dynamic section)
        self._parse_module_defs(app_prog, ns, config)
        
        # Parse channels
        for ch_elem in dynamic.findall('knx:Channel', ns):
            ch_id = ch_elem.get('Id', '')
            ch_name = ch_elem.get('Name', ch_id)
            ch_text = ch_elem.get('Text', '')
            
            # Get parameter block references
            pb_refs = []
            for pbref_elem in ch_elem.findall('knx:ParameterBlockRefRef', ns):
                pb_refs.append(pbref_elem.get('RefId', ''))
            
            config.channels[ch_id] = {
                'name': ch_name,
                'text': ch_text,
                'parameter_blocks': pb_refs
            }
        
    def _parse_module_defs(self, app_prog: ElementTree.Element, ns: dict[str, str], config: SimpleDeviceConfig) -> None:
        """Parse module definitions to extract parameter blocks."""
        module_defs = app_prog.find('knx:ModuleDefs', ns)
        if module_defs is None:
            return
            
        # Parse parameter blocks from each ModuleDef
        # Parameter blocks are located in Channel elements within ModuleDef > Dynamic
        for module_def in module_defs.findall('knx:ModuleDef', ns):
            module_dynamic = module_def.find('knx:Dynamic', ns)
            if module_dynamic is None:
                continue
                
            # Look for parameter blocks in channels
            for channel_elem in module_dynamic.findall('knx:Channel', ns):
                # Parameter blocks are directly in the Channel element
                for pb_elem in channel_elem.findall('knx:ParameterBlock', ns):
                    pb_id = pb_elem.get('Id', '')
                    pb_name = pb_elem.get('Name', pb_id)
                    pb_text = pb_elem.get('Text', '')
                    
                    config.parameter_blocks[pb_id] = {
                        'name': pb_name,
                        'text': pb_text,
                        'id': pb_id
                    }
        
    def _parse_com_objects(self, root: ElementTree.Element, ns: dict[str, str], config: SimpleDeviceConfig) -> None:
        """Parse communication objects from ComObjectTable."""
        # Look for ComObjectTable at root level
        comobj_table = root.find('knx:ComObjectTable', ns)
        if comobj_table is None:
            return
            
        for co_elem in comobj_table.findall('knx:ComObject', ns):
            co_id = co_elem.get('Id', '')
            co_name = co_elem.get('Name', '')
            co_number = co_elem.get('Number', '0')
            co_text = co_elem.get('Text', '')
            co_function = co_elem.get('FunctionText', '')
            co_size = co_elem.get('ObjectSize', '')
            co_dpt = co_elem.get('DatapointType', '')
            
            config.com_objects[co_id] = {
                'name': co_name,
                'number': co_number,
                'text': co_text,
                'function': co_function,
                'size': co_size,
                'dpt': co_dpt
            }

    def parse_with_parameterization(self) -> Tuple['SimpleDeviceConfig', Dict[str, Any]]:
        """Parse the device configuration file with full parameterization support.
        
        This method provides enhanced parsing that includes memory mapping information
        and detailed parameter type data needed for device parameterization.
        
        Returns:
            Tuple[SimpleDeviceConfig, Dict[str, Any]]: 
                - Enhanced SimpleDeviceConfig with memory mapping
                - Full hardware parameterization data (may be empty if parsing fails)
        """
        # First do basic parsing
        config = self.parse()
        
        # Then extract memory mapping and type details directly from the XML
        try:
            hw_data = self._parse_memory_mapping_and_types()
            
            # Enhance the simple config with memory mapping and type details
            self._enhance_config_with_parameterization(config, hw_data)
            
            return config, hw_data
            
        except Exception as e:
            _LOGGER.warning("Enhanced parameterization parsing failed, falling back to basic parsing: %s", e)
            return config, {}
            
    def _parse_memory_mapping_and_types(self) -> Dict[str, Any]:
        """Parse memory mapping and detailed type information directly from the device XML.
        
        This method handles the MDT-style XML format where memory mapping is in <Memory> elements
        and segments are defined as <AbsoluteSegment> elements.
        
        Returns:
            Dictionary containing parsed parameterization data
        """
        hw_data = {
            'parameters': {},
            'parameter_types': {},
            'segments': {},
            'unions': []
        }
        
        try:
            with ZipFile(self.device_file_path, mode="r") as zip_archive:
                # Find application program XML files (same logic as in basic parsing)
                app_program_files = []
                for path in zip_archive.namelist():
                    if (path.startswith('M-') and 
                        path.endswith('.xml') and 
                        not path.endswith('Catalog.xml') and 
                        not path.endswith('Hardware.xml')):
                        app_program_files.append(path)
                
                if not app_program_files:
                    _LOGGER.warning("No application program files found in device configuration")
                    return hw_data
                    
                # Use the first application program file
                app_program_path = app_program_files[0]
                _LOGGER.info("Parsing memory mapping from: %s", app_program_path)
                
                with zip_archive.open(app_program_path) as app_program_file:
                    tree = ElementTree.parse(app_program_file)
                    root = tree.getroot()
                    ns = {'knx': root.tag.split('}')[0].strip('{')}
                    
                    # Parse segments (AbsoluteSegment elements)
                    self._parse_absolute_segments(root, ns, hw_data)
                    
                    # Parse parameter types with detailed information
                    self._parse_parameter_types_detailed(root, ns, hw_data)
                    
                    # Parse parameters with memory mapping
                    self._parse_parameters_with_memory(root, ns, hw_data)
                    
                    # Parse unions
                    self._parse_unions(root, ns, hw_data)
                    
        except Exception as e:
            _LOGGER.error("Failed to parse memory mapping and types: %s", e)
            # Return empty data instead of raising exception
            return hw_data
            
        return hw_data
        
    def _parse_absolute_segments(self, root: ElementTree.Element, ns: dict[str, str], hw_data: Dict[str, Any]) -> None:
        """Parse AbsoluteSegment elements as memory segments."""
        code_elem = root.find('knx:ManufacturerData/knx:Manufacturer/knx:ApplicationPrograms/knx:ApplicationProgram/knx:Static/knx:Code', ns)
        if code_elem is None:
            return
            
        for seg_elem in code_elem.findall('knx:AbsoluteSegment', ns):
            seg_id = seg_elem.get('Id', '')
            address = seg_elem.get('Address', '')
            size = seg_elem.get('Size', '')
            memory_type = seg_elem.get('MemoryType', '')
            
            if seg_id and address and size:
                hw_data['segments'][seg_id] = {
                    'id': seg_id,
                    'address': int(address),
                    'size': int(size),
                    'memory_type': memory_type
                }
        
    def _parse_parameter_types_detailed(self, root: ElementTree.Element, ns: dict[str, str], hw_data: Dict[str, Any]) -> None:
        """Parse parameter types with detailed type information and enums."""
        param_types_elem = root.find('knx:ManufacturerData/knx:Manufacturer/knx:ApplicationPrograms/knx:ApplicationProgram/knx:Static/knx:ParameterTypes', ns)
        if param_types_elem is None:
            return
            
        for pt_elem in param_types_elem.findall('knx:ParameterType', ns):
            pt_id = pt_elem.get('Id', '')
            pt_name = pt_elem.get('Name', pt_id)
            
            if not pt_id:
                continue
                
            # Parse type restriction or type number
            type_restriction = pt_elem.find('knx:TypeRestriction', ns)
            type_number = pt_elem.find('knx:TypeNumber', ns)
            
            if type_restriction is not None:
                base_type = type_restriction.get('Base', '')
                size_in_bit = type_restriction.get('SizeInBit', '0')
                
                # Parse enumeration
                enum_dict = {}
                enumeration = type_restriction.find('knx:Enumeration', ns)
                if enumeration is not None:
                    for enum_item in enumeration.findall('knx:EnumerationValue', ns):
                        value = enum_item.get('Value', '')
                        text = enum_item.get('Text', '')
                        if value and text:
                            enum_dict[value] = text
                
                hw_data['parameter_types'][pt_id] = {
                    'id': pt_id,
                    'name': pt_name,
                    'type': base_type,
                    'size': int(size_in_bit) if size_in_bit.isdigit() else 0,
                    'enum': enum_dict
                }
            
            elif type_number is not None:
                base_type = type_number.get('Type', '')
                size_in_bit = type_number.get('SizeInBit', '0')
                min_inclusive = type_number.get('minInclusive', '')
                max_inclusive = type_number.get('maxInclusive', '')
                
                hw_data['parameter_types'][pt_id] = {
                    'id': pt_id,
                    'name': pt_name,
                    'type': base_type,
                    'size': int(size_in_bit) if size_in_bit.isdigit() else 0,
                    'enum': {},
                    'min_value': float(min_inclusive) if min_inclusive else None,
                    'max_value': float(max_inclusive) if max_inclusive else None
                }
        
    def _parse_parameters_with_memory(self, root: ElementTree.Element, ns: dict[str, str], hw_data: Dict[str, Any]) -> None:
        """Parse parameters with memory mapping information."""
        # Parse parameters from Static section
        params_elem = root.find('knx:ManufacturerData/knx:Manufacturer/knx:ApplicationPrograms/knx:ApplicationProgram/knx:Static/knx:Parameters', ns)
        if params_elem is not None:
            for p_elem in params_elem.findall('knx:Parameter', ns):
                self._parse_parameter_element(p_elem, ns, hw_data)
        
        # Parse parameters from Dynamic section (including unions)
        dynamic_elem = root.find('knx:ManufacturerData/knx:Manufacturer/knx:ApplicationPrograms/knx:ApplicationProgram/knx:Dynamic', ns)
        if dynamic_elem is not None:
            for param_elem in dynamic_elem.findall('.//knx:Parameter', ns):
                self._parse_parameter_element(param_elem, ns, hw_data)
        
    def _parse_parameter_element(self, p_elem: ElementTree.Element, ns: dict[str, str], hw_data: Dict[str, Any]) -> None:
        """Parse a single parameter element with memory mapping."""
        p_id = p_elem.get('Id', '')
        p_name = p_elem.get('Name', p_id)
        p_type = p_elem.get('ParameterType', '')
        p_value = p_elem.get('Value', '')
        
        if not p_id:
            return
            
        # Parse memory mapping from <Memory> element (MDT format)
        memory_elem = p_elem.find('knx:Memory', ns)
        segment_id = None
        offset = None
        offset_bit = None
        
        if memory_elem is not None:
            segment_id = memory_elem.get('CodeSegment')
            offset_str = memory_elem.get('Offset')
            offset_bit_str = memory_elem.get('BitOffset')
            
            if offset_str is not None:
                offset = int(offset_str)
            if offset_bit_str is not None:
                offset_bit = int(offset_bit_str)
        
        # Parse union information
        union_id = None
        union_default = False
        
        # Check if this parameter is inside a union
        union_elem = p_elem.find('..', ns)  # Parent element
        if union_elem is not None and union_elem.tag.endswith('Union'):
            union_id = union_elem.get('Id')
            union_default_str = p_elem.get('UnionDefault')
            union_default = union_default_str and union_default_str.lower() == 'true'
        
        hw_data['parameters'][p_id] = {
            'id': p_id,
            'name': p_name,
            'type_id': p_type,
            'value': p_value,
            'segment_id': segment_id,
            'offset': offset,
            'offset_bit': offset_bit,
            'union_id': union_id,
            'union_default': union_default
        }
        
    def _parse_unions(self, root: ElementTree.Element, ns: dict[str, str], hw_data: Dict[str, Any]) -> None:
        """Parse union elements."""
        # Look for unions in Dynamic section
        dynamic_elem = root.find('knx:ManufacturerData/knx:Manufacturer/knx:ApplicationPrograms/knx:ApplicationProgram/knx:Dynamic', ns)
        if dynamic_elem is None:
            return
            
        for union_elem in dynamic_elem.findall('.//knx:Union', ns):
            size_in_bit = union_elem.get('SizeInBit', '0')
            
            # Parse union memory mapping
            memory_elem = union_elem.find('knx:Memory', ns)
            segment_id = None
            offset = None
            offset_bit = None
            
            if memory_elem is not None:
                segment_id = memory_elem.get('CodeSegment')
                offset_str = memory_elem.get('Offset')
                offset_bit_str = memory_elem.get('BitOffset')
                
                if offset_str is not None:
                    offset = int(offset_str)
                if offset_bit_str is not None:
                    offset_bit = int(offset_bit_str)
            
            # Parse union parameters
            parameters = []
            for param_elem in union_elem.findall('knx:Parameter', ns):
                param_id = param_elem.get('Id', '')
                if param_id:
                    parameters.append(param_id)
            
            hw_data['unions'].append({
                'size_in_bit': int(size_in_bit) if size_in_bit.isdigit() else 0,
                'segment_id': segment_id,
                'offset': offset,
                'offset_bit': offset_bit,
                'parameters': parameters
            })
            
    def _enhance_config_with_parameterization(self, config: 'SimpleDeviceConfig', hw_data: Dict[str, Any]) -> None:
        """Enhance SimpleDeviceConfig with memory mapping and type details from hardware parameterization data."""
        
        # Enhance parameters with memory mapping
        for param_id, hw_param in hw_data.get('parameters', {}).items():
            if param_id in config.parameters:
                config.parameters[param_id].update({
                    'segment_id': hw_param.get('segment_id'),
                    'offset': hw_param.get('offset'),
                    'offset_bit': hw_param.get('offset_bit'),
                    'union_id': hw_param.get('union_id'),
                    'union_default': hw_param.get('union_default')
                })
        
        # Enhance parameter types with detailed type information
        for pt_id, hw_pt in hw_data.get('parameter_types', {}).items():
            if pt_id in config.parameter_types:
                config.parameter_types[pt_id].update({
                    'type': hw_pt.get('type'),
                    'size': hw_pt.get('size'),
                    'enum': hw_pt.get('enum'),
                    'min_value': hw_pt.get('min_value'),
                    'max_value': hw_pt.get('max_value')
                })
        
        # Add unions if not already present
        if 'unions' not in config.__dict__:
            config.unions = []
        config.unions.extend(hw_data.get('unions', []))