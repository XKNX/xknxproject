"""Parser logic for ETS XML files."""
from xml.sax import make_parser

from xknxproject.zip import KNXProjExtractor

from .models import GroupAddress
from .sax_content_handler_0 import GroupAddressSAXContentHandler


class XMLParser:
    """Class that parses XMLs and returns useful information."""

    def __init__(self, extractor: KNXProjExtractor):
        """Initialize the parser."""
        self.extractor = extractor
        self.group_addresses: list[GroupAddress] = []

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
