"""Test loading the trades of a project."""

from __future__ import annotations

from xml.etree import ElementTree

from xknxproject.loader.project_loader import _TradeLoader
from xknxproject.models import DeviceInstance, XMLTrade
from xknxproject.xml.parser import _recursive_convert_trades

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
    # a device maps to the trade listing it, not its ancestors, or else to None
    assert {device.identifier: device.trade_id for device in devices} == {
        "P-1_DI-6": "P-1_T-1",
        "P-1_DI-2": "P-1_T-5",
        "P-1_DI-9": None,
    }


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
    assert devices[0].trade_id == "P-1_T-1"


def test_project_without_trades() -> None:
    """An empty `Trades` element yields no trades."""
    assert _load_trades(f'<Trades xmlns="{_NS}" />', devices=[]) == []
