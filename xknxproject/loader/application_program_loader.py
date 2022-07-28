"""Application Program Loader."""
from typing import Any
from zipfile import Path

from lxml import etree

from xknxproject.models import ComObject, DeviceInstance

from ..util import parse_dpt_types
from .loader import XMLLoader


class ApplicationProgramLoader(XMLLoader):
    """Load the application program from KNX XML."""

    def __init__(self, devices: list[DeviceInstance]):
        """Initialize the ApplicationProgramLoader."""
        self.devices = devices

    def load(self, project_root_path: Path) -> list[Any]:
        """Load Hardware mappings and assign to devices."""
        application_programs: dict[
            str, list[DeviceInstance]
        ] = self._get_optimized_application_program_struct()
        for application_program_file, devices in application_programs.items():
            com_object_mapping: dict[str, dict[str, str]] = {}
            com_objects: dict[str, ComObject] = {}
            with (project_root_path / application_program_file).open(
                mode="rb"
            ) as application_xml:
                for elem in etree.parse(application_xml).iter():
                    if elem.tag.endswith("ComObject"):
                        com_objects[elem.attrib.get("Id", "")] = ComObject(
                            identifier=elem.attrib.get("Id"),
                            name=elem.attrib.get("Name"),
                            text=elem.attrib.get("Text"),
                            object_size=elem.attrib.get("ObjectSize"),
                            read_flag=elem.attrib.get("ReadFlag", False) == "Enabled",
                            write_flag=elem.attrib.get("WriteFlag", False) == "Enabled",
                            communication_flag=elem.attrib.get(
                                "CommunicationFlag", False
                            )
                            == "Enabled",
                            transmit_flag=elem.attrib.get("TransmitFlag", False)
                            == "Enabled",
                            update_flag=elem.attrib.get("UpdateFlag", False)
                            == "Enabled",
                            read_on_init_flag=elem.attrib.get("ReadOnInitFlag", False)
                            == "Enabled",
                            datapoint_type=parse_dpt_types(
                                elem.attrib.get("DatapointType", "").split(" ")
                            ),
                        )
                    if elem.tag.endswith("ComObjectRef"):
                        com_object_mapping[elem.attrib["Id"]] = {
                            "RefId": elem.attrib["RefId"],
                            "FunctionText": elem.attrib.get("FunctionText", None),
                            "DPTType": elem.attrib.get("DatapointType", None),
                            "Text": elem.attrib.get("Text", None),
                        }
                for device in devices:
                    device.add_com_object_id(com_object_mapping)
                    device.add_com_objects(com_objects)

        return []

    def _get_optimized_application_program_struct(
        self,
    ) -> dict[str, list[DeviceInstance]]:
        """Do not load the same application program multiple times."""
        result: dict[str, list[DeviceInstance]] = {}
        for device in self.devices:
            if device.application_program_ref != "":
                result.setdefault(device.application_program_xml(), []).append(device)

        return result
