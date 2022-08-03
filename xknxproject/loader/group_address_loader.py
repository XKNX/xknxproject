"""Group Address Loader."""
from lxml import etree

from xknxproject.models import XMLGroupAddress
from xknxproject.zip import KNXProjContents


class GroupAddressLoader:
    """Load GroupAddress info from KNX XML."""

    def load(self, knx_proj_contents: KNXProjContents) -> list[XMLGroupAddress]:
        """Load GroupAddress mappings."""
        group_address_list: list[XMLGroupAddress] = []

        with knx_proj_contents.open_project_0() as project_file:
            for _, elem in etree.iterparse(project_file):
                if elem.tag.endswith("GroupAddress"):
                    group_address_list.append(
                        XMLGroupAddress(
                            name=elem.get("Name"),
                            identifier=elem.get("Id"),
                            address=elem.get("Address"),
                            dpt_type=elem.get("DatapointType"),
                        )
                    )
                elem.clear()

        return group_address_list
