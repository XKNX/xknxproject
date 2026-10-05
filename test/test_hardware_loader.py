"""Test hardware loader."""

from __future__ import annotations

from xml.etree import ElementTree

from xknxproject.loader import HardwareLoader

_NS = "http://knx.org/xml/project/20"

HARDWARE_XML = f"""
<Hardware xmlns="{_NS}" Id="M-0008_H-1-1" Name="Taster">
  <Products>
    <Product Id="M-0008_H-1-1_P-1" Text="Taster 4fach" OrderNumber="4711" />
  </Products>
  <Hardware2Programs>
    <Hardware2Program Id="M-0008_H-1-1_HP-20E0-21-9997-O000A">
      <ApplicationProgramRef RefId="M-0008_A-20E0-21-9997-O000A" />
    </Hardware2Program>
  </Hardware2Programs>
</Hardware>
"""


def test_parse_hardware_element_tags_products_with_hardware() -> None:
    """Hardware id and name are attached to each product."""
    node = ElementTree.fromstring(HARDWARE_XML)
    products, hardware_programs = HardwareLoader.parse_hardware_element(node)

    product = products["M-0008_H-1-1_P-1"]
    assert product.hardware_id == "M-0008_H-1-1"
    assert product.hardware_name == "Taster"
    assert hardware_programs == {
        "M-0008_H-1-1_HP-20E0-21-9997-O000A": "M-0008_A-20E0-21-9997-O000A"
    }
