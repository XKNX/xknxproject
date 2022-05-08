"""Parser logic for ETS XML files."""
from __future__ import annotations

from xknxproject.loader import (
    ApplicationProgramLoader,
    GroupAddressLoader,
    HardwareLoader,
    TopologyLoader,
    XMLLoader,
)
from xknxproject.models import Area, DeviceInstance, GroupAddress, Hardware
from xknxproject.util import flatten
from xknxproject.zip import KNXProjExtractor


class XMLParser:
    """Class that parses XMLs and returns useful information."""

    def __init__(self, extractor: KNXProjExtractor):
        """Initialize the parser."""
        self.extractor = extractor
        self.hardware_loader: XMLLoader = HardwareLoader()
        self.group_address_loader: XMLLoader | None = None
        self.topology_loader: XMLLoader | None = None
        self.group_addresses: list[GroupAddress] = []
        self.hardware: list[Hardware] = []
        self.areas: list[Area] = []

    async def parse(self) -> None:
        """Parse ETS files."""
        self.group_address_loader = GroupAddressLoader(self.extractor.get_project_id())
        self.topology_loader = TopologyLoader(self.extractor.get_project_id())

        self.group_addresses = await self.group_address_loader.load(
            self.extractor.extraction_path
        )
        self.hardware = await self.hardware_loader.load(self.extractor.extraction_path)
        self.areas = await self.topology_loader.load(self.extractor.extraction_path)

        # TODO: Make this nicer... Noone will understand this in a months time :-)
        devices: list[DeviceInstance] = flatten(
            [
                line.devices
                for line in flatten(
                    list(line for line in list(area.lines for area in self.areas))
                )
            ]
        )
        application_program_loader = ApplicationProgramLoader(devices)
        await application_program_loader.load(self.extractor.extraction_path)

        for hardware in self.hardware:
            for device in devices:
                if device.hardware_program_ref == hardware.identifier:
                    device.product_name = hardware.name
                    device.hardware_name = hardware.product_name
