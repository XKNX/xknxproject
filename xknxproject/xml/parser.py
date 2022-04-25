"""Parser logic for ETS XML files."""
from xml.dom.minidom import Document, parse
from xml.sax import make_parser

from xknxproject.zip import KNXProjExtractor

from .models import Area, GroupAddress
from .sax_content_handler_0 import GroupAddressSAXContentHandler


class XMLParser:
    """Class that parses XMLs and returns useful information."""

    def __init__(self, extractor: KNXProjExtractor):
        """Initialize the parser."""
        self.extractor = extractor
        self.group_addresses: list[GroupAddress] = []
        self.areas: list[Area] = []

    def parse(self) -> None:
        """Parse ETS files."""
        handler = GroupAddressSAXContentHandler()
        with open(
            self.extractor.extraction_path + self.extractor.get_project_id() + "/0.xml",
            encoding="utf-8",
        ) as file:
            parser = make_parser()
            parser.setContentHandler(handler)  # type: ignore[no-untyped-call]
            parser.parse(file)  # type: ignore[no-untyped-call]

        self.group_addresses = handler.group_addresses
        self._parse_topology()

    def _parse_topology(self) -> None:
        """Parse the topology."""
        with open(
            self.extractor.extraction_path + self.extractor.get_project_id() + "/0.xml",
            encoding="utf-8",
        ) as file:
            dom: Document = parse(file)
            node: Document = dom.getElementsByTagName("Topology")[0]

            for sub_node in filter(lambda x: x.nodeType != 3, node.childNodes):
                if sub_node.nodeName == "Area":
                    self.areas.append(Area.from_xml(sub_node))
