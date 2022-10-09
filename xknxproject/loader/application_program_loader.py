"""Application Program Loader."""
from xml.etree import ElementTree
from zipfile import Path

from xknxproject.models import ComObject, ComObjectRef, DeviceInstance
from xknxproject.util import parse_dpt_types, parse_xml_flag


class ApplicationProgramLoader:
    """Load the application program from KNX XML."""

    @staticmethod
    def load(
        application_program_path: Path, devices: list[DeviceInstance]
    ) -> None:  # tuple[dict[str, ComObjectRef], dict[str, ComObject]]:
        """Load Hardware mappings and assign to devices."""
        com_object_instance_refs = [
            instance_ref
            for device in devices
            for instance_ref in device.com_object_instance_refs
        ]
        used_com_object_ref_ids = {
            instance_ref.ref_id for instance_ref in com_object_instance_refs
        }
        com_object_refs: dict[str, ComObjectRef] = {}  # {Id: ComObjectRef}
        com_objects: dict[str, ComObject] = {}  # {Id: ComObject}

        with application_program_path.open(mode="rb") as application_xml:
            for _, elem in ElementTree.iterparse(application_xml):
                if elem.tag.endswith("ComObject"):
                    # we take all since we don't know which are referenced to yet
                    identifier = elem.attrib.get("Id")
                    com_objects[identifier] = ComObject(
                        identifier=identifier,
                        name=elem.get("Name"),
                        text=elem.get("Text"),
                        number=elem.get("Number"),
                        function_text=elem.get("FunctionText"),
                        object_size=elem.get("ObjectSize"),
                        read_flag=parse_xml_flag(elem.get("ReadFlag"), False),
                        write_flag=parse_xml_flag(elem.get("WriteFlag"), False),
                        communication_flag=parse_xml_flag(
                            elem.get("CommunicationFlag"), False
                        ),
                        transmit_flag=parse_xml_flag(elem.get("TransmitFlag"), False),
                        update_flag=parse_xml_flag(elem.get("UpdateFlag"), False),
                        read_on_init_flag=parse_xml_flag(
                            elem.get("ReadOnInitFlag"), False
                        ),
                        datapoint_type=parse_dpt_types(
                            elem.get("DatapointType", "").split(" ")
                        ),
                    )
                if elem.tag.endswith("ComObjectRef"):
                    identifier = elem.attrib.get("Id")
                    if identifier in used_com_object_ref_ids:
                        _dpt_type = elem.get("DatapointType")
                        datapoint_type = (
                            parse_dpt_types(_dpt_type.split(" ")) if _dpt_type else None
                        )

                        com_object_refs[identifier] = ComObjectRef(
                            identifier=identifier,
                            ref_id=elem.get("RefId"),
                            name=elem.get("Name"),
                            text=elem.get("Text"),
                            function_text=elem.get("FunctionText"),
                            object_size=elem.get("ObjectSize"),
                            read_flag=parse_xml_flag(elem.get("ReadFlag")),
                            write_flag=parse_xml_flag(elem.get("WriteFlag")),
                            communication_flag=parse_xml_flag(
                                elem.get("CommunicationFlag")
                            ),
                            transmit_flag=parse_xml_flag(elem.get("TransmitFlag")),
                            update_flag=parse_xml_flag(elem.get("UpdateFlag")),
                            read_on_init_flag=parse_xml_flag(
                                elem.get("ReadOnInitFlag")
                            ),
                            datapoint_type=datapoint_type,
                        )
                if elem.tag.endswith("ApplicationPrograms"):
                    # We don't need anything after ApplicationPrograms
                    elem.clear()
                    break
                elem.clear()

            for com_instance in com_object_instance_refs:
                _com_object_ref = com_object_refs[com_instance.ref_id]
                com_instance.merge_from_application(_com_object_ref)
                com_instance.merge_from_application(com_objects[_com_object_ref.ref_id])

    @staticmethod
    def get_application_program_files_for_devices(
        project_root_path: Path,
        devices: list[DeviceInstance],
    ) -> dict[Path, list[DeviceInstance]]:
        """Do not load the same application program multiple times."""
        _result: dict[str, list[DeviceInstance]] = {}
        for device in devices:
            if device.application_program_ref:
                # zipfile.Path hashes are not equal, therefore we use str to create the struct
                xml_file_name = device.application_program_xml()
                _result.setdefault(xml_file_name, []).append(device)

        return {
            (project_root_path / xml_file): devices
            for xml_file, devices in _result.items()
        }
