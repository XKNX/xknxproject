"""Simple parser for KNX device configuration files.

This parser provides a lightweight alternative to the full ApplicationProgramLoader
for extracting device configuration information directly from .knxprod files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from zipfile import ZipFile
from typing import Any
from xml.etree import ElementTree

from xknxproject.zip.extractor import extract

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