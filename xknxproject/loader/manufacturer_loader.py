"""KNX Master Data Loader."""
from __future__ import annotations

from xml.etree import ElementTree
from zipfile import Path

from xknxproject.models import DeviceInstance


class ManufacturerLoader:
    """Load KNX master XML."""

    @staticmethod
    def load(knx_master_file: Path, devices: list[DeviceInstance]) -> None:
        """Load KNX manufacturer."""
        manufacturer_mapping: dict[str, str | None] = dict.fromkeys(
            {device.manufacturer for device in devices}
        )

        with knx_master_file.open(mode="rb") as master_xml:
            tree = ElementTree.parse(master_xml)
            for manufacturer in tree.findall(".//{*}Manufacturers/{*}Manufacturer"):
                identifier = manufacturer.get("Id", "")
                if identifier in manufacturer_mapping:
                    manufacturer_mapping[identifier] = manufacturer.get("Name", "")

        for device in devices:
            device.manufacturer_name = manufacturer_mapping[device.manufacturer]  # type: ignore[assignment]
