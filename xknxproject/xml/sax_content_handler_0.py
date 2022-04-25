"""Content Handler for parsing 0.xml ETS files."""
import logging
from xml.sax.handler import ContentHandler
from xml.sax.xmlreader import AttributesImpl

from .models import GroupAddress

logger = logging.getLogger("xknxproject.xml")


class GroupAddressSAXContentHandler(ContentHandler):
    """SAX parser for parsing all group adresses from an ETS file."""

    def __init__(self) -> None:
        """Initialize."""
        self.group_addresses: list[GroupAddress] = []
        super().__init__()

    def startElement(self, name: str, attrs: AttributesImpl) -> None:
        """Start Element."""
        if name == "GroupAddress":
            self.group_addresses.append(
                GroupAddress(
                    name=attrs.get("Name"),  # type: ignore[no-untyped-call]
                    identifier=attrs.get("Id"),  # type: ignore[no-untyped-call]
                    address=attrs.get("Address"),  # type: ignore[no-untyped-call]
                    dpt_type=attrs.get("DatapointType"),  # type: ignore[no-untyped-call]
                )
            )
