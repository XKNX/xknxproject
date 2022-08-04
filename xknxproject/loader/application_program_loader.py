"""Application Program Loader."""
from typing import Any
from zipfile import Path

from lxml import etree

from xknxproject.models import ComObject, DeviceInstance
from xknxproject.util import parse_dpt_types


class ApplicationProgramLoader:
    """Load the application program from KNX XML."""

    def __init__(self, devices: list[DeviceInstance]):
        """Initialize the ApplicationProgramLoader."""
        self.devices = devices

    def load(self, project_root_path: Path) -> list[Any]:
        """Load Hardware mappings and assign to devices."""
        application_programs = self._get_optimized_application_program_struct(
            project_root_path
        )
        for application_program_file_path, devices in application_programs.items():
            com_object_mapping: dict[str, dict[str, str]] = {}
            com_objects: dict[str, ComObject] = {}
            with application_program_file_path.open(mode="rb") as application_xml:
                for _, elem in etree.iterparse(application_xml):
                    if elem.tag.endswith("ComObject"):
                        com_objects[elem.get("Id", "")] = ComObject(
                            identifier=elem.get("Id"),
                            name=elem.get("Name"),
                            text=elem.get("Text"),
                            object_size=elem.get("ObjectSize"),
                            read_flag=elem.get("ReadFlag", False) == "Enabled",
                            write_flag=elem.get("WriteFlag", False) == "Enabled",
                            communication_flag=elem.get("CommunicationFlag", False)
                            == "Enabled",
                            transmit_flag=elem.get("TransmitFlag", False) == "Enabled",
                            update_flag=elem.get("UpdateFlag", False) == "Enabled",
                            read_on_init_flag=elem.get("ReadOnInitFlag", False)
                            == "Enabled",
                            datapoint_type=parse_dpt_types(
                                elem.get("DatapointType", "").split(" ")
                            ),
                        )
                    if elem.tag.endswith("ComObjectRef"):
                        com_object_mapping[elem.get("Id")] = {
                            "RefId": elem.get("RefId"),
                            "FunctionText": elem.get("FunctionText", None),
                            "DPTType": elem.get("DatapointType", None),
                            "Text": elem.get("Text", None),
                        }
                    elem.clear()

                for device in devices:
                    device.add_com_object_id(com_object_mapping)
                    device.add_com_objects(com_objects)

        return []

    def _get_optimized_application_program_struct(
        self,
        project_root_path: Path,
    ) -> dict[Path, list[DeviceInstance]]:
        """Do not load the same application program multiple times."""
        _result: dict[str, list[DeviceInstance]] = {}
        for device in self.devices:
            if device.application_program_ref != "":
                # zipfile.Path hashes are not equal, therefore we use str to create the struct
                xml_file_name = device.application_program_xml()
                _result.setdefault(xml_file_name, []).append(device)

        return {
            (project_root_path / xml_file): devices
            for xml_file, devices in _result.items()
        }
