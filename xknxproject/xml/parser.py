"""Parser logic for ETS XML files."""
from __future__ import annotations

from xknxproject.__version__ import __version__
from xknxproject.loader import (
    ApplicationProgramLoader,
    GroupAddressLoader,
    HardwareLoader,
    TopologyLoader,
    XMLLoader,
)
from xknxproject.models import (
    MANUFACTURERS,
    MEDIUM_TYPES,
    Area,
    Device,
    DeviceInstance,
    Flags,
    GroupAddress,
    GroupAddressAssignment,
    Hardware,
    KNXProject,
    Line,
    XMLArea,
    XMLGroupAddress,
)
from xknxproject.zip import KNXProjExtractor


class XMLParser:
    """Class that parses XMLs and returns useful information."""

    def __init__(self, extractor: KNXProjExtractor):
        """Initialize the parser."""
        self.extractor = extractor
        self.hardware_loader: XMLLoader = HardwareLoader()
        self.group_address_loader: XMLLoader | None = None
        self.topology_loader: XMLLoader | None = None
        self.group_addresses: list[XMLGroupAddress] = []
        self.hardware: list[Hardware] = []
        self.areas: list[XMLArea] = []
        self.devices: list[DeviceInstance] = []

    async def parse(self) -> KNXProject:
        """Parse ETS files."""
        await self.load()

        devices_dict: dict[str, Device] = {}
        for device in self.devices:
            group_address_assignments: list[GroupAddressAssignment] = []
            for link in device.com_object_instance_refs:
                if len(link.links) > 0:
                    group_address_assignments.append(
                        GroupAddressAssignment(
                            co_name=link.text,
                            dpt_type=link.data_point_type,
                            flags=Flags(
                                read=True,
                                write=True,
                                communication=True,
                                update=True,
                                read_on_init=True,
                                transmit=False,
                            ),
                            group_address_links=link.links,
                        )
                    )

            devices_dict[device.individual_address] = Device(
                name=device.name or device.product_name,
                product_name=device.product_name,
                description=device.hardware_name,
                individual_address=device.individual_address,
                manufacturer_name=MANUFACTURERS.get(device.manufacturer, "Unknown"),
                group_address_assignments=group_address_assignments,
            )

        topology_dict: dict[str, Area] = {}
        for area in self.areas:
            lines_dict: dict[str, Line] = {}
            for line in area.lines:
                devices_topology: list[str] = []
                for device in line.devices:
                    devices_topology.append(device.individual_address)
                lines_dict[str(line.address)] = Line(
                    name=line.name,
                    description=line.description,
                    devices=devices_topology,
                    medium_type=MEDIUM_TYPES.get(line.medium_type, "Unknown"),
                )
            topology_dict[str(area.address)] = Area(
                name=area.name, description=area.description, lines=lines_dict
            )

        group_address_dict: dict[str, GroupAddress] = {}
        for group_address in self.group_addresses:
            group_address_dict[group_address.identifier] = GroupAddress(
                name=group_address.name,
                identifier=group_address.identifier,
                raw_address=group_address.raw_address,
                address=group_address.address,
                dpt_type=group_address.dpt_type,
            )

        return KNXProject(
            version=__version__,
            topology=topology_dict,
            devices=devices_dict,
            group_addresses=group_address_dict,
        )

    async def load(self) -> None:
        """Load XML files."""
        self.group_address_loader = GroupAddressLoader(self.extractor.get_project_id())
        self.topology_loader = TopologyLoader(self.extractor.get_project_id())

        self.group_addresses = await self.group_address_loader.load(
            self.extractor.extraction_path
        )
        self.hardware = await self.hardware_loader.load(self.extractor.extraction_path)
        self.areas = await self.topology_loader.load(self.extractor.extraction_path)

        for area in self.areas:
            for line in area.lines:
                self.devices.extend(line.devices)

        application_program_loader = ApplicationProgramLoader(self.devices)
        await application_program_loader.load(self.extractor.extraction_path)

        for hardware in self.hardware:
            for device in self.devices:
                if device.hardware_program_ref == hardware.identifier:
                    device.product_name = hardware.name
                    device.hardware_name = hardware.product_name
