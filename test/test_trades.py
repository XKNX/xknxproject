"""Test loading the trades of a project."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZipFile

from xknxproject import XKNXProj
from xknxproject.loader.project_loader import _TradeLoader
from xknxproject.models import DeviceInstance, XMLTrade
from xknxproject.xml.parser import _recursive_convert_trades

from . import RESOURCES_PATH
from .conftest import build_devices

# ETS 6 project schema namespace; the loader matches any namespace (`{*}`)
_NS = "http://knx.org/xml/project/23"


def _load_trades(trades_xml: str, devices: list[DeviceInstance]) -> list[XMLTrade]:
    """Load an ETS `Trades` element."""
    return _TradeLoader(devices).load(ElementTree.fromstring(trades_xml))


def test_trades_are_nested_and_list_their_devices() -> None:
    """Trades keep their hierarchy; devices belong to the trade listing them."""
    devices = build_devices(("P-1_DI-6", 6), ("P-1_DI-2", 2), ("P-1_DI-9", 9))
    trades = _load_trades(
        f"""
        <Trades xmlns="{_NS}">
          <Trade Id="P-1_T-1" Name="Beleuchtung" Puid="31">
            <Trade Id="P-1_T-3" Name="Innen" Number="1.1" Description="Wohnräume" Puid="33">
              <Trade Id="P-1_T-5" Name="Dimmen" Puid="35">
                <DeviceInstanceRef RefId="P-1_DI-2" />
              </Trade>
            </Trade>
            <Trade Id="P-1_T-4" Name="Aussen" Puid="34" />
            <DeviceInstanceRef RefId="P-1_DI-6" />
          </Trade>
          <Trade Id="P-1_T-2" Name="Heizung" />
        </Trades>
        """,
        devices,
    )

    assert _recursive_convert_trades(trades) == [
        {
            "identifier": "P-1_T-1",
            "name": "Beleuchtung",
            "number": "",
            "description": "",
            "project_uid": 31,
            "devices": ["1.1.6"],
            "trades": [
                {
                    "identifier": "P-1_T-3",
                    "name": "Innen",
                    "number": "1.1",
                    "description": "Wohnräume",
                    "project_uid": 33,
                    "devices": [],
                    "trades": [
                        {
                            "identifier": "P-1_T-5",
                            "name": "Dimmen",
                            "number": "",
                            "description": "",
                            "project_uid": 35,
                            "devices": ["1.1.2"],
                            "trades": [],
                        }
                    ],
                },
                {
                    "identifier": "P-1_T-4",
                    "name": "Aussen",
                    "number": "",
                    "description": "",
                    "project_uid": 34,
                    "devices": [],
                    "trades": [],
                },
            ],
        },
        {
            "identifier": "P-1_T-2",
            "name": "Heizung",
            "number": "",
            "description": "",
            "project_uid": None,
            "devices": [],
            "trades": [],
        },
    ]


def test_sibling_trades_may_share_a_name() -> None:
    """Trades are a list - equally named siblings are both kept, in file order."""
    trades = _load_trades(
        f"""
        <Trades xmlns="{_NS}">
          <Trade Id="P-1_T-1" Name="Allgemein" />
          <Trade Id="P-1_T-2" Name="Allgemein" />
        </Trades>
        """,
        devices=[],
    )

    assert [trade.identifier for trade in trades] == ["P-1_T-1", "P-1_T-2"]


def test_unknown_device_references_are_skipped() -> None:
    """A reference to a device not in the project does not break loading."""
    devices = build_devices(("P-1_DI-1", 1))
    (trade,) = _load_trades(
        f"""
        <Trades xmlns="{_NS}">
          <Trade Id="P-1_T-1" Name="Beleuchtung">
            <DeviceInstanceRef RefId="P-1_DI-404" />
            <DeviceInstanceRef RefId="P-1_DI-1" />
          </Trade>
        </Trades>
        """,
        devices,
    )

    assert trade.devices == ["1.1.1"]


def test_project_without_trades() -> None:
    """An empty `Trades` element yields no trades."""
    assert _load_trades(f'<Trades xmlns="{_NS}" />', devices=[]) == []


def test_trades_of_parsed_project(tmp_path: Path) -> None:
    """
    Trades of a project file end up in the parsed project.

    No fixture contains trades, so they are added to the project XML of an
    unprotected one - as ETS writes them, after the locations of the installation.
    """
    source = RESOURCES_PATH / "xknx_test_project_no_password.knxproj"
    project_path = tmp_path / "trades.knxproj"
    with ZipFile(source) as archive, ZipFile(project_path, "w", ZIP_DEFLATED) as copy:
        for name in archive.namelist():
            content = archive.read(name)
            if name.endswith("/0.xml"):
                project_xml = content.decode("utf-8")
                assert "</Locations>" in project_xml
                content = project_xml.replace(
                    "</Locations>",
                    """</Locations>
                    <Trades>
                      <Trade Id="P-01D2-0_T-1" Name="Beleuchtung" Puid="31">
                        <Trade Id="P-01D2-0_T-2" Name="Innen" Puid="32">
                          <DeviceInstanceRef RefId="P-01D2-0_DI-1" />
                        </Trade>
                      </Trade>
                    </Trades>""",
                ).encode("utf-8")
            copy.writestr(name, content)

    project = XKNXProj(project_path).parse()

    (device_address,) = project["devices"]
    assert project["trades"] == [
        {
            "identifier": "P-01D2-0_T-1",
            "name": "Beleuchtung",
            "number": "",
            "description": "",
            "project_uid": 31,
            "devices": [],
            "trades": [
                {
                    "identifier": "P-01D2-0_T-2",
                    "name": "Innen",
                    "number": "",
                    "description": "",
                    "project_uid": 32,
                    "devices": [device_address],
                    "trades": [],
                }
            ],
        }
    ]
