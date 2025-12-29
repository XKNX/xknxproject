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
        except FileNotFoundError as e:
            _LOGGER.error("Device file not found: %s", e)
            config.name = "Unknown Device (File Not Found)"
            return config
        except Exception as e:
            _LOGGER.error("Failed to parse device configuration: %s", e)
            config.name = "Unknown Device (Parsing Failed)"
            return config
            
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
                p_access = p_elem.get('Access', 'Full')  # Default to Full access if not specified
                
                config.parameters[p_id] = {
                    'name': p_name,
                    'type': p_type,
                    'value': p_value,
                    'access': p_access
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
        """Parse communication objects from ComObjectTable with enhanced details."""
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
            
            # Parse COM object flags
            co_flags = {
                'communicate': co_elem.get('CommunicationFlag', '') == 'Enabled',
                'read': co_elem.get('ReadFlag', '') == 'Enabled',
                'write': co_elem.get('WriteFlag', '') == 'Enabled',
                'transmit': co_elem.get('TransmitFlag', '') == 'Enabled',
                'update': co_elem.get('UpdateFlag', '') == 'Enabled',
                'read_on_init': co_elem.get('ReadOnInitFlag', '') == 'Enabled'
            }
            
            # Parse memory mapping if available
            memory_elem = co_elem.find('knx:Memory', ns)
            co_memory = {}
            if memory_elem is not None:
                co_memory = {
                    'segment_id': memory_elem.get('CodeSegment', ''),
                    'offset': memory_elem.get('Offset', ''),
                    'bit_offset': memory_elem.get('BitOffset', '')
                }
            
            config.com_objects[co_id] = {
                'name': co_name,
                'number': co_number,
                'text': co_text,
                'function': co_function,
                'size': co_size,
                'dpt': co_dpt,
                'flags': co_flags,
                'memory': co_memory
            }
        
        # Parse AddressTable and AssociationTable
        self._parse_address_and_association_tables(root, ns, config)
    
    def _parse_address_and_association_tables(self, root: ElementTree.Element, ns: dict[str, str], config: SimpleDeviceConfig) -> None:
        """Parse AddressTable and AssociationTable information."""
        # Parse AddressTable
        address_table = root.find('knx:AddressTable', ns)
        if address_table is not None:
            config.address_table = {
                'segment_id': address_table.get('CodeSegment', ''),
                'offset': address_table.get('Offset', ''),
                'max_entries': address_table.get('MaxEntries', ''),
                'table_type': 'address'
            }
        
        # Parse AssociationTable
        association_table = root.find('knx:AssociationTable', ns)
        if association_table is not None:
            config.association_table = {
                'segment_id': association_table.get('CodeSegment', ''),
                'offset': association_table.get('Offset', ''),
                'max_entries': association_table.get('MaxEntries', ''),
                'table_type': 'association'
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
        try:
            config = self.parse()
        except Exception as e:
            _LOGGER.error("Basic parsing failed: %s", e)
            # Create a minimal config to continue
            config = SimpleDeviceConfig()
            config.name = "Unknown Device (Parsing Failed)"
        
        # Then extract memory mapping and type details directly from the XML
        try:
            hw_data = self._parse_memory_mapping_and_types()
            
            # Enhance the simple config with memory mapping and type details
            self._enhance_config_with_parameterization(config, hw_data)
            
            return config, hw_data
            
        except Exception as e:
            _LOGGER.warning("Enhanced parameterization parsing failed, continuing with basic parsing: %s", e)
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
                    'memory_type': memory_type,
                    'segment_type': 'absolute'
                }
        
        # Parse RelativeSegment elements
        for seg_elem in code_elem.findall('knx:RelativeSegment', ns):
            seg_id = seg_elem.get('Id', '')
            offset = seg_elem.get('Offset', '')
            size = seg_elem.get('Size', '')
            lsm_id = seg_elem.get('LoadStateMachine', '')
            
            if seg_id and offset and size:
                hw_data['segments'][seg_id] = {
                    'id': seg_id,
                    'offset': int(offset),
                    'size': int(size),
                    'lsm_id': lsm_id,
                    'segment_type': 'relative'
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
                
            # Parse type restriction or type number or other types
            type_restriction = pt_elem.find('knx:TypeRestriction', ns)
            type_number = pt_elem.find('knx:TypeNumber', ns)
            type_time = pt_elem.find('knx:TypeTime', ns)
            type_text = pt_elem.find('knx:TypeText', ns)
            type_float = pt_elem.find('knx:TypeFloat', ns)
            type_picture = pt_elem.find('knx:TypePicture', ns)
            type_ip_address = pt_elem.find('knx:TypeIPAddress', ns)
            type_color = pt_elem.find('knx:TypeColor', ns)
            type_none = pt_elem.find('knx:TypeNone', ns)
            
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
                ui_hint = type_number.get('UIHint', '')
                
                hw_data['parameter_types'][pt_id] = {
                    'id': pt_id,
                    'name': pt_name,
                    'type': base_type,
                    'size': int(size_in_bit) if size_in_bit.isdigit() else 0,
                    'enum': {},
                    'min_value': float(min_inclusive) if min_inclusive else None,
                    'max_value': float(max_inclusive) if max_inclusive else None,
                    'ui_hint': ui_hint
                }
            
            elif type_time is not None:
                size_in_bit = type_time.get('SizeInBit', '0')
                min_inclusive = type_time.get('minInclusive', '')
                max_inclusive = type_time.get('maxInclusive', '')
                unit = type_time.get('Unit', '')
                
                hw_data['parameter_types'][pt_id] = {
                    'id': pt_id,
                    'name': pt_name,
                    'type': 'Time',
                    'size': int(size_in_bit) if size_in_bit.isdigit() else 0,
                    'enum': {},
                    'min_value': min_inclusive,
                    'max_value': max_inclusive,
                    'unit': unit
                }
            
            elif type_text is not None:
                size_in_bit = type_text.get('SizeInBit', '0')
                
                hw_data['parameter_types'][pt_id] = {
                    'id': pt_id,
                    'name': pt_name,
                    'type': 'Text',
                    'size': int(size_in_bit) if size_in_bit.isdigit() else 0,
                    'enum': {}
                }
            
            elif type_float is not None:
                encoding = type_float.get('Encoding', '')
                min_inclusive = type_float.get('minInclusive', '')
                max_inclusive = type_float.get('maxInclusive', '')
                display_format = type_float.get('DisplayFormat', '')
                
                hw_data['parameter_types'][pt_id] = {
                    'id': pt_id,
                    'name': pt_name,
                    'type': 'Float',
                    'size': 32,  # Float is typically 32 bits
                    'enum': {},
                    'encoding': encoding,
                    'min_value': float(min_inclusive) if min_inclusive else None,
                    'max_value': float(max_inclusive) if max_inclusive else None,
                    'display_format': display_format
                }
            
            elif type_picture is not None:
                ref_id = type_picture.get('RefId', '')
                
                hw_data['parameter_types'][pt_id] = {
                    'id': pt_id,
                    'name': pt_name,
                    'type': 'Picture',
                    'size': 0,  # Size determined by referenced picture
                    'enum': {},
                    'ref_id': ref_id
                }
            
            elif type_ip_address is not None:
                address_type = type_ip_address.get('AddressType', '')
                
                hw_data['parameter_types'][pt_id] = {
                    'id': pt_id,
                    'name': pt_name,
                    'type': 'IPAddress',
                    'size': 32,  # IPv4 is 32 bits
                    'enum': {},
                    'address_type': address_type
                }
            
            elif type_color is not None:
                space = type_color.get('Space', '')
                
                hw_data['parameter_types'][pt_id] = {
                    'id': pt_id,
                    'name': pt_name,
                    'type': 'Color',
                    'size': 24,  # Typically 24 bits for RGB
                    'enum': {},
                    'color_space': space
                }
            
            elif type_none is not None:
                hw_data['parameter_types'][pt_id] = {
                    'id': pt_id,
                    'name': pt_name,
                    'type': 'None',
                    'size': 0,
                    'enum': {}
                }
            
            else:
                _LOGGER.warning(f"Unknown parameter type for {pt_id}")
                hw_data['parameter_types'][pt_id] = {
                    'id': pt_id,
                    'name': pt_name,
                    'type': 'Unknown',
                    'size': 0,
                    'enum': {}
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
            # Check both UnionDefault and DefaultUnionParameter attributes
            union_default_str = p_elem.get('UnionDefault')
            default_union_param_str = p_elem.get('DefaultUnionParameter')
            union_default = (union_default_str and union_default_str.lower() == 'true') or \
                           (default_union_param_str and default_union_param_str.lower() == 'true')
        
        # Parse access control
        p_access = p_elem.get('Access', 'Full')  # Default to Full access if not specified
        
        hw_data['parameters'][p_id] = {
            'id': p_id,
            'name': p_name,
            'type_id': p_type,
            'value': p_value,
            'segment_id': segment_id,
            'offset': offset,
            'offset_bit': offset_bit,
            'union_id': union_id,
            'union_default': union_default,
            'access': p_access
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
            
            # Parse union parameters and identify default parameter
            parameters = []
            default_param_id = None
            
            for param_elem in union_elem.findall('knx:Parameter', ns):
                param_id = param_elem.get('Id', '')
                if param_id:
                    parameters.append(param_id)
                    # Check if this is the default parameter for the union
                    default_param_attr = param_elem.get('DefaultUnionParameter', '')
                    if default_param_attr and default_param_attr.lower() in ('true', '1'):
                        default_param_id = param_id
            
            hw_data['unions'].append({
                'size_in_bit': int(size_in_bit) if size_in_bit.isdigit() else 0,
                'segment_id': segment_id,
                'offset': offset,
                'offset_bit': offset_bit,
                'parameters': parameters,
                'default_parameter': default_param_id
            })
            
    def _validate_memory_mapping(self, config: 'SimpleDeviceConfig', hw_data: Dict[str, Any]) -> None:
        """Validate memory mapping of parameters against segments."""
        segments = {}
        # Build segment information from config or hw_data
        if hasattr(config, 'segments') and config.segments:
            for seg in config.segments:
                segments[seg['id']] = {
                    'size': int(seg['size']) if seg['size'] else 0,
                    'address': int(seg['address']) if seg['address'] else 0
                }
        
        # Also check hw_data segments if available
        for seg_id, seg_info in hw_data.get('segments', {}).items():
            segments[seg_id] = {
                'size': seg_info.get('size', 0),
                'address': seg_info.get('address', 0)
            }
        
        # Validate parameter offsets against segment bounds
        for param_id, param in config.parameters.items():
            seg_id = param.get('segment_id')
            offset = param.get('offset')
            
            if seg_id and offset is not None and seg_id in segments:
                seg = segments[seg_id]
                param_size = 1  # Default size for parameters without explicit size
                
                # Try to get parameter size from type information
                param_type_id = param.get('type_id') or param.get('type', '')
                if param_type_id and param_type_id in config.parameter_types:
                    pt = config.parameter_types[param_type_id]
                    if 'size' in pt and pt['size'] > 0:
                        param_size = (pt['size'] + 7) // 8  # Convert bits to bytes
                
                # Check if offset is within segment bounds
                if offset < 0:
                    _LOGGER.warning(f"Parameter {param_id} has negative offset: {offset}")
                elif seg.get('segment_type') == 'absolute':
                    # For absolute segments, check against segment size
                    if offset + param_size > seg['size']:
                        _LOGGER.warning(f"Parameter {param_id} offset {offset} + size {param_size} exceeds absolute segment {seg_id} size {seg['size']}")
                elif seg.get('segment_type') == 'relative':
                    # For relative segments, we can't validate absolute bounds without base address
                    # But we can check if offset is reasonable
                    if offset < 0:
                        _LOGGER.warning(f"Parameter {param_id} has negative offset in relative segment {seg_id}: {offset}")
                    elif offset > 10000:  # Arbitrary large offset warning
                        _LOGGER.warning(f"Parameter {param_id} has very large offset in relative segment {seg_id}: {offset}")
        
        # Check for parameter overlaps within the same segment
        seg_params = {}
        for param_id, param in config.parameters.items():
            seg_id = param.get('segment_id')
            offset = param.get('offset')
            
            if seg_id and offset is not None:
                if seg_id not in seg_params:
                    seg_params[seg_id] = []
                seg_params[seg_id].append((param_id, offset, param.get('size', 1)))
        
        # Check for overlaps
        for seg_id, params in seg_params.items():
            # Sort by offset
            params.sort(key=lambda x: x[1])
            
            for i in range(len(params) - 1):
                param1_id, offset1, size1 = params[i]
                param2_id, offset2, size2 = params[i + 1]
                
                if offset1 + size1 > offset2:
                    _LOGGER.warning(f"Parameters {param1_id} and {param2_id} overlap in segment {seg_id}")

    def _validate_parameter_types(self, config: 'SimpleDeviceConfig', hw_data: Dict[str, Any]) -> None:
        """Validate parameter types and their usage."""
        # Validate that all parameters reference valid parameter types
        for param_id, param in config.parameters.items():
            param_type_id = param.get('type_id') or param.get('type', '')
            if param_type_id and param_type_id not in config.parameter_types:
                _LOGGER.warning(f"Parameter {param_id} references unknown parameter type: {param_type_id}")
        
        # Validate parameter type sizes and ranges
        for pt_id, pt in config.parameter_types.items():
            pt_type = pt.get('type', 'Unknown')
            
            if 'size' in pt and pt['size'] <= 0:
                # Allow size 0 for special types like None and Picture
                if pt_type not in ['None', 'Picture']:
                    _LOGGER.warning(f"Parameter type {pt_id} has invalid size: {pt['size']}")
            
            if 'min_value' in pt and 'max_value' in pt:
                if pt['min_value'] is not None and pt['max_value'] is not None:
                    if pt['min_value'] > pt['max_value']:
                        _LOGGER.warning(f"Parameter type {pt_id} has invalid range: min {pt['min_value']} > max {pt['max_value']}")
        
        # Validate enum values
        for pt_id, pt in config.parameter_types.items():
            if 'enum' in pt and pt['enum']:
                enum_size = len(pt['enum'])
                if 'size' in pt and pt['size'] > 0:
                    max_enum_values = 2 ** pt['size']
                    if enum_size > max_enum_values:
                        _LOGGER.warning(f"Parameter type {pt_id} has {enum_size} enum values but only {pt['size']} bits")
        
        # Validate specific parameter types
        for pt_id, pt in config.parameter_types.items():
            pt_type = pt.get('type', 'Unknown')
            
            if pt_type == 'Time' and 'unit' not in pt:
                _LOGGER.warning(f"Time parameter type {pt_id} missing unit information")
            
            elif pt_type == 'Float' and 'encoding' not in pt:
                _LOGGER.warning(f"Float parameter type {pt_id} missing encoding information")
            
            elif pt_type == 'Picture' and 'ref_id' not in pt:
                _LOGGER.warning(f"Picture parameter type {pt_id} missing reference ID")
            
            elif pt_type == 'IPAddress' and 'address_type' not in pt:
                _LOGGER.warning(f"IPAddress parameter type {pt_id} missing address type")
            
            elif pt_type == 'Color' and 'color_space' not in pt:
                _LOGGER.warning(f"Color parameter type {pt_id} missing color space")

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
                    'union_default': hw_param.get('union_default'),
                    'access': hw_param.get('access')  # Add access control from enhanced parsing
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
        
        # Validate parameter types and memory mapping after enhancement
        self._validate_parameter_types(config, hw_data)
        self._validate_memory_mapping(config, hw_data)