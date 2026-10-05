"""Test the application program definition loader."""

from __future__ import annotations

import io

from xknxproject.loader import (
    ApplicationProgramDefinitionLoader,
    LoadedApplicationProgram,
)
from xknxproject.loader.application_program_definition_loader import _Placement
from xknxproject.models import ChannelDefinition

_NS = "http://knx.org/xml/project/20"
_APP = "M-0083_A-013A-32-DCC1"

APPLICATION_XML = f"""<?xml version="1.0" encoding="utf-8"?>
<KNX xmlns="{_NS}" CreatedBy="ETS5" ToolVersion="5.7">
<ManufacturerData><Manufacturer RefId="M-0083">
<ApplicationPrograms>
<ApplicationProgram Id="{_APP}" ApplicationNumber="314" ApplicationVersion="50"
  MaskVersion="MV-07B0" Name="AKD-0424V.02" Hash="abc=" OriginalManufacturer="M-000A"
  Semantics="# Serialization-Format-Version=2, KIM-Version=(&lt;http://schema.knx.org/2020/ontology/v2&gt;, 92, 60), @prefix knx: &lt;http://x&gt;">
<Static>
  <ComObjectTable>
    <ComObject Id="{_APP}_O-0" Name="Central" Text="Central switch" Number="0"
      FunctionText="Switch" ObjectSize="1 Bit" ReadFlag="Disabled" WriteFlag="Enabled"
      CommunicationFlag="Enabled" TransmitFlag="Disabled" UpdateFlag="Disabled"
      ReadOnInitFlag="Disabled" DatapointType="DPST-1-1" />
  </ComObjectTable>
  <ComObjectRefs>
    <ComObjectRef Id="{_APP}_O-0_R-1" RefId="{_APP}_O-0" />
  </ComObjectRefs>
</Static>
<ModuleDefs>
  <ModuleDef Id="{_APP}_MD-2" Name="ModuleDefChannel">
    <Static>
      <ComObjectTable>
        <ComObject Id="{_APP}_MD-2_O-2-1" Name="Switch" Text="Switch" Number="1"
          FunctionText="On/Off" ObjectSize="1 Bit" ReadFlag="Disabled" WriteFlag="Enabled"
          CommunicationFlag="Enabled" TransmitFlag="Disabled" UpdateFlag="Disabled"
          ReadOnInitFlag="Disabled" DatapointType="DPST-1-1" BaseNumber="{_APP}_MD-2_A-2" />
        <ComObject Id="{_APP}_MD-2_O-2-3" Name="Status" Text="Status" Number="3"
          FunctionText="On/Off" ObjectSize="1 Bit" ReadFlag="Enabled" WriteFlag="Disabled"
          CommunicationFlag="Enabled" TransmitFlag="Enabled" UpdateFlag="Disabled"
          ReadOnInitFlag="Disabled" DatapointType="DPST-1-1" BaseNumber="{_APP}_MD-2_A-2" />
      </ComObjectTable>
      <ComObjectRefs>
        <ComObjectRef Id="{_APP}_MD-2_O-2-1_R-1" RefId="{_APP}_MD-2_O-2-1"
          Semantics="knx:dpa.417.52" />
        <ComObjectRef Id="{_APP}_MD-2_O-2-1_R-2" RefId="{_APP}_MD-2_O-2-1"
          Text="Switch inverted" DatapointType="DPST-1-2" />
        <ComObjectRef Id="{_APP}_MD-2_O-2-3_R-1" RefId="{_APP}_MD-2_O-2-3"
          Semantics="knx:dpa.417.51" />
      </ComObjectRefs>
    </Static>
    <Dynamic>
      <Channel Id="{_APP}_MD-2_CH-1" Name="Channel 1" Text="Channel {{{{ChNo}}}}: {{{{0}}}}"
        Number="1" Semantics="knx:fb.417">
        <ParameterBlock Id="{_APP}_MD-2_PB-1" Name="Settings">
          <choose ParamRefId="{_APP}_MD-2_P-1_R-1">
            <when test="0">
              <ComObjectRefRef RefId="{_APP}_MD-2_O-2-1_R-1" />
              <ComObjectRefRef RefId="{_APP}_MD-2_O-2-3_R-1" />
            </when>
            <when test="1">
              <ComObjectRefRef RefId="{_APP}_MD-2_O-2-1_R-2" />
              <ComObjectRefRef RefId="{_APP}_MD-2_O-2-3_R-1" />
            </when>
          </choose>
        </ParameterBlock>
      </Channel>
    </Dynamic>
  </ModuleDef>
  <ModuleDef Id="{_APP}_MD-3" Name="Page">
    <Static>
      <ComObjectTable>
        <ComObject Id="{_APP}_MD-3_O-3-1" Name="Page" Text="Page" Number="1"
          FunctionText="Page" ObjectSize="1 Bit" ReadFlag="Disabled" WriteFlag="Enabled"
          CommunicationFlag="Enabled" TransmitFlag="Disabled" UpdateFlag="Disabled"
          ReadOnInitFlag="Disabled" DatapointType="DPST-1-1" />
      </ComObjectTable>
      <ComObjectRefs>
        <ComObjectRef Id="{_APP}_MD-3_O-3-1_R-1" RefId="{_APP}_MD-3_O-3-1" />
      </ComObjectRefs>
    </Static>
    <SubModuleDefs>
      <ModuleDef Id="{_APP}_MD-3_SM-1" Name="Sub">
        <Static>
          <ComObjectTable>
            <ComObject Id="{_APP}_MD-3_SM-1_O-4-1" Name="Sub" Text="Sub" Number="4"
              FunctionText="Sub" ObjectSize="1 Bit" ReadFlag="Disabled" WriteFlag="Enabled"
              CommunicationFlag="Enabled" TransmitFlag="Disabled" UpdateFlag="Disabled"
              ReadOnInitFlag="Disabled" DatapointType="DPST-1-1" />
          </ComObjectTable>
          <ComObjectRefs>
            <ComObjectRef Id="{_APP}_MD-3_SM-1_O-4-1_R-1" RefId="{_APP}_MD-3_SM-1_O-4-1" />
          </ComObjectRefs>
        </Static>
        <Dynamic>
          <ParameterBlock Id="{_APP}_MD-3_SM-1_PB-1" Name="Sub settings">
            <ComObjectRefRef RefId="{_APP}_MD-3_SM-1_O-4-1_R-1" />
          </ParameterBlock>
        </Dynamic>
      </ModuleDef>
    </SubModuleDefs>
    <Dynamic>
      <ParameterBlock Id="{_APP}_MD-3_PB-1" Name="Page settings">
        <ComObjectRefRef RefId="{_APP}_MD-3_O-3-1_R-1" />
      </ParameterBlock>
      <Module Id="{_APP}_MD-3_M-1_SM-1_M-1" RefId="{_APP}_MD-3_SM-1" />
    </Dynamic>
  </ModuleDef>
  <ModuleDef Id="{_APP}_MD-9" Name="Unused">
    <Static>
      <ComObjectTable>
        <ComObject Id="{_APP}_MD-9_O-9-1" Name="Unused" Text="Unused" Number="9"
          FunctionText="Unused" ObjectSize="1 Bit" ReadFlag="Disabled" WriteFlag="Enabled"
          CommunicationFlag="Enabled" TransmitFlag="Disabled" UpdateFlag="Disabled"
          ReadOnInitFlag="Disabled" DatapointType="DPST-1-1" />
      </ComObjectTable>
      <ComObjectRefs>
        <ComObjectRef Id="{_APP}_MD-9_O-9-1_R-1" RefId="{_APP}_MD-9_O-9-1" />
      </ComObjectRefs>
    </Static>
    <Dynamic>
      <ParameterBlock Id="{_APP}_MD-9_PB-1" Name="Unused settings">
        <ComObjectRefRef RefId="{_APP}_MD-9_O-9-1_R-1" />
      </ParameterBlock>
    </Dynamic>
  </ModuleDef>
</ModuleDefs>
<Dynamic>
  <ChannelIndependentBlock>
    <ParameterBlock Id="{_APP}_PB-0" Name="General">
      <ComObjectRefRef RefId="{_APP}_O-0_R-1" />
    </ParameterBlock>
  </ChannelIndependentBlock>
  <Channel Id="{_APP}_CH-9" Name="Logic" Text="Logic" Number="9">
    <ParameterBlock Id="{_APP}_PB-9" Name="Logic">
      <ComObjectRefRef RefId="{_APP}_O-0_R-1" />
    </ParameterBlock>
  </Channel>
  <Module Id="{_APP}_MD-2_M-1" RefId="{_APP}_MD-2" />
  <Channel Id="{_APP}_CH-5" Name="Pages" Text="Pages" Number="5">
    <Module Id="{_APP}_MD-3_M-1" RefId="{_APP}_MD-3" />
  </Channel>
</Dynamic>
<Languages>
  <Language Identifier="de-DE">
    <TranslationUnit RefId="{_APP}">
      <TranslationElement RefId="{_APP}_MD-2_O-2-1">
        <Translation AttributeName="Text" Text="Schalten" />
        <Translation AttributeName="FunctionText" Text="Ein/Aus" />
      </TranslationElement>
      <TranslationElement RefId="{_APP}_MD-2_O-2-1_R-2">
        <Translation AttributeName="Text" Text="Schalten invertiert" />
      </TranslationElement>
      <TranslationElement RefId="{_APP}_MD-2_CH-1">
        <Translation AttributeName="Text" Text="Kanal {{{{ChNo}}}}: {{{{0}}}}" />
      </TranslationElement>
    </TranslationUnit>
  </Language>
</Languages>
</ApplicationProgram>
</ApplicationPrograms>
</Manufacturer></ManufacturerData>
</KNX>
"""


def _load(language_code: str | None) -> LoadedApplicationProgram:
    return ApplicationProgramDefinitionLoader.load(
        io.BytesIO(APPLICATION_XML.encode("utf-8")), language_code=language_code
    )


def test_identity_attributes() -> None:
    """Root attributes and the KIM header are parsed."""
    loaded = _load(None)
    assert loaded.identity.application_id == _APP
    assert loaded.identity.application_number == 314
    assert loaded.identity.application_version == 50
    assert loaded.identity.name == "AKD-0424V.02"
    assert loaded.identity.mask_version == "MV-07B0"
    assert loaded.identity.program_hash == "abc="
    assert loaded.identity.kim_version == "92.60"
    assert loaded.identity.original_manufacturer == "M-000A"


def test_channel_object_ids_deduplicated() -> None:
    """Objects referenced in several `when` branches appear once, in first-seen order."""
    loaded = _load(None)
    assert loaded.channels["MD-2_CH-1"]["object_ids"] == [
        "MD-2_O-2-1_R-1",
        "MD-2_O-2-3_R-1",
        "MD-2_O-2-1_R-2",
    ]
    assert loaded.channels["MD-2_CH-1"]["module_definition_id"] == "MD-2"
    assert loaded.channels["MD-2_CH-1"]["functional_blocks"] == ["417"]
    assert loaded.channels["MD-2_CH-1"]["text"] == "Channel {{ChNo}}: {{0}}"
    assert loaded.channels["CH-9"]["module_definition_id"] is None
    assert loaded.modules["MD-2"] == {
        "identifier": "MD-2",
        "name": "ModuleDefChannel",
        "channel_ids": ["MD-2_CH-1"],
    }
    assert loaded.channel_independent_object_ids == ["MD-9_O-9-1_R-1", "O-0_R-1"]
    # the same object can be channel independent and referenced by a channel
    assert loaded.objects["O-0_R-1"]["channel_ids"] == ["CH-9"]
    assert loaded.objects["MD-2_O-2-3_R-1"]["channel_ids"] == ["MD-2_CH-1"]


def test_refs_outside_channels_are_channel_independent() -> None:
    """
    Refs outside any Channel are channel independent.

    That is a ChannelIndependentBlock or a Channel-less ModuleDef that is never
    instantiated inside a Channel.
    """
    loaded = _load(None)
    # in a ChannelIndependentBlock
    assert "O-0_R-1" in loaded.channel_independent_object_ids
    # in a ModuleDef never instantiated
    assert "MD-9_O-9-1_R-1" in loaded.channel_independent_object_ids
    assert loaded.objects["MD-9_O-9-1_R-1"]["channel_ids"] == []
    assert all(
        "MD-9_O-9-1_R-1" not in channel["object_ids"]
        for channel in loaded.channels.values()
    )
    assert loaded.modules["MD-9"]["channel_ids"] == []


def test_module_instantiated_in_channel_inherits_channel() -> None:
    """Refs of a Channel-less ModuleDef belong to the Channel instantiating it."""
    loaded = _load(None)
    assert loaded.channels["CH-5"]["module_definition_id"] is None
    assert loaded.channels["CH-5"]["object_ids"] == [
        "MD-3_O-3-1_R-1",
        "MD-3_SM-1_O-4-1_R-1",
    ]
    assert loaded.objects["MD-3_O-3-1_R-1"]["channel_ids"] == ["CH-5"]
    assert "MD-3_O-3-1_R-1" not in loaded.channel_independent_object_ids
    # channel_ids of a module only lists channels defined inside the module
    assert loaded.modules["MD-3"]["channel_ids"] == []


def test_sub_module_inherits_channel_transitively() -> None:
    """A sub-module instantiated in a module inherits the channels placing that module."""
    loaded = _load(None)
    assert loaded.modules["MD-3_SM-1"] == {
        "identifier": "MD-3_SM-1",
        "name": "Sub",
        "channel_ids": [],
    }
    assert "MD-3_SM-1_O-4-1_R-1" in loaded.channels["CH-5"]["object_ids"]
    assert loaded.objects["MD-3_SM-1_O-4-1_R-1"]["channel_ids"] == ["CH-5"]
    assert "MD-3_SM-1_O-4-1_R-1" not in loaded.channel_independent_object_ids


def test_object_definition_merges_ref_over_com_object() -> None:
    """ComObjectRef attributes override ComObject attributes."""
    loaded = _load(None)
    plain = loaded.objects["MD-2_O-2-1_R-1"]
    assert plain["com_object_id"] == "MD-2_O-2-1"
    assert plain["number"] == 1
    assert plain["text"] == "Switch"
    assert plain["dpts"] == [{"main": 1, "sub": 1}]
    assert plain["flags"] == {
        "read": False,
        "write": True,
        "communication": True,
        "transmit": False,
        "update": False,
        "read_on_init": False,
    }
    assert plain["dpas"] == ["417.52"]
    inverted = loaded.objects["MD-2_O-2-1_R-2"]
    assert inverted["text"] == "Switch inverted"
    assert inverted["dpts"] == [{"main": 1, "sub": 2}]
    assert inverted["dpas"] is None


def test_translations_applied() -> None:
    """Texts of objects, refs and channels are translated."""
    loaded = _load("de-DE")
    assert loaded.objects["MD-2_O-2-1_R-1"]["text"] == "Schalten"
    assert loaded.objects["MD-2_O-2-1_R-1"]["function_text"] == "Ein/Aus"
    assert loaded.objects["MD-2_O-2-1_R-2"]["text"] == "Schalten invertiert"
    assert loaded.channels["MD-2_CH-1"]["text"] == "Kanal {{ChNo}}: {{0}}"


def test_translation_missing_language_keeps_defaults() -> None:
    """An unknown language leaves the default texts untouched."""
    loaded = _load("fr-FR")
    assert loaded.objects["MD-2_O-2-1_R-1"]["text"] == "Switch"
    assert loaded.channels["MD-2_CH-1"]["text"] == "Channel {{ChNo}}: {{0}}"


def test_cyclic_module_instantiation_terminates() -> None:
    """Modules instantiating each other do not recurse forever."""
    channels = {
        "CH-1": ChannelDefinition(
            identifier="CH-1",
            name="",
            text=None,
            number="1",
            functional_blocks=None,
            module_definition_id=None,
            object_ids=[],
        )
    }
    independent = ApplicationProgramDefinitionLoader._place_module_refs(
        channels=channels,
        module_ids=["MD-1", "MD-2", "MD-3", "MD-4"],
        module_refs={
            "MD-1": ["MD-1_O-1_R-1"],
            "MD-2": ["MD-2_O-2_R-1"],
            "MD-3": ["MD-3_O-3_R-1"],
            "MD-4": ["MD-4_O-4_R-1"],
        },
        module_placements={
            # MD-1 in CH-1, MD-2 in MD-1 and MD-1 in MD-2
            "MD-1": [
                _Placement(channel_id="CH-1", module_id=None),
                _Placement(channel_id=None, module_id="MD-2"),
            ],
            "MD-2": [_Placement(channel_id=None, module_id="MD-1")],
            # MD-3 and MD-4 only instantiate each other
            "MD-3": [_Placement(channel_id=None, module_id="MD-4")],
            "MD-4": [_Placement(channel_id=None, module_id="MD-3")],
        },
        independent_candidates=[
            ("MD-1", "MD-1_O-1_R-1"),
            ("MD-2", "MD-2_O-2_R-1"),
            ("MD-3", "MD-3_O-3_R-1"),
            ("MD-4", "MD-4_O-4_R-1"),
        ],
    )
    assert channels["CH-1"]["object_ids"] == ["MD-1_O-1_R-1", "MD-2_O-2_R-1"]
    # modules only reachable through a cycle are treated as not instantiated
    assert independent == ["MD-3_O-3_R-1", "MD-4_O-4_R-1"]
