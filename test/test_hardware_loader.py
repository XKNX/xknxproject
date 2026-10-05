"""Test hardware loader."""

from __future__ import annotations

from xml.etree import ElementTree

from xknxproject.loader import HardwareLoader

# ETS 5.7 project schema namespace; the loader matches any namespace (`{*}`)
_NS = "http://knx.org/xml/project/20"

# one Hardware element with two Products and one Hardware2Program
HARDWARE_XML = f"""
<Hardware xmlns="{_NS}" Id="M-0008_H-1-1" Name="Taster" OriginalManufacturer="M-000A">
  <Products>
    <Product Id="M-0008_H-1-1_P-1" Text="Taster 4fach" OrderNumber="4711" />
    <Product Id="M-0008_H-1-1_P-2" Text="Taster 6fach" OrderNumber="4712" />
  </Products>
  <Hardware2Programs>
    <Hardware2Program Id="M-0008_H-1-1_HP-20E0-21-9997-O000A">
      <ApplicationProgramRef RefId="M-0008_A-20E0-21-9997-O000A" />
    </Hardware2Program>
  </Hardware2Programs>
</Hardware>
"""


def test_parse_hardware_element_tags_products_with_hardware() -> None:
    """Each product carries Id, Name and OriginalManufacturer of its Hardware element."""
    node = ElementTree.fromstring(HARDWARE_XML)
    products, hardware_programs = HardwareLoader.parse_hardware_element(node)

    assert {
        identifier: (
            product.hardware_id,
            product.hardware_name,
            product.original_manufacturer,
        )
        for identifier, product in products.items()
    } == {
        "M-0008_H-1-1_P-1": ("M-0008_H-1-1", "Taster", "M-000A"),
        "M-0008_H-1-1_P-2": ("M-0008_H-1-1", "Taster", "M-000A"),
    }
    assert hardware_programs == {
        "M-0008_H-1-1_HP-20E0-21-9997-O000A": "M-0008_A-20E0-21-9997-O000A"
    }


def test_parse_hardware_element_without_id() -> None:
    """Products of a Hardware element without Id and Name get empty strings."""
    node = ElementTree.fromstring(
        f"""
        <Hardware xmlns="{_NS}">
          <Products>
            <Product Id="M-0008_H-1-1_P-1" Text="Taster 4fach" OrderNumber="4711" />
          </Products>
        </Hardware>
        """
    )
    products, _ = HardwareLoader.parse_hardware_element(node)

    assert products["M-0008_H-1-1_P-1"].hardware_id == ""
    assert products["M-0008_H-1-1_P-1"].hardware_name == ""


def test_parse_hardware_element_without_original_manufacturer() -> None:
    """OriginalManufacturer is optional."""
    xml = HARDWARE_XML.replace(' OriginalManufacturer="M-000A"', "")
    products, _ = HardwareLoader.parse_hardware_element(ElementTree.fromstring(xml))
    assert products["M-0008_H-1-1_P-1"].original_manufacturer is None
