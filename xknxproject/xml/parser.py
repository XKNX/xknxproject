"""Parser logic for ETS XML files."""
from __future__ import annotations

from xknxproject.loader import (
    ApplicationProgramLoader,
    GroupAddressLoader,
    HardwareLoader,
    TopologyLoader,
    XMLLoader,
)
from xknxproject.models import Area, GroupAddress, Hardware
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
        devices = flatten(
            [
                line.devices
                for line in flatten(
                    [line for line in [area.lines for area in self.areas]]
                )
            ]
        )
        application_program_loader = ApplicationProgramLoader(devices)
        await application_program_loader.load(self.extractor.extraction_path)
