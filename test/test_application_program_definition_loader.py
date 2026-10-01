"""Test the application program definition loader."""

from __future__ import annotations

import io

from xknxproject.loader import ApplicationProgramDefinitionLoader
from xknxproject.loader.application_program_definition_loader import _RawIdentity
from xknxproject.models import ChannelDefinition, ModuleDefinition, ObjectDefinition

_NS = "http://knx.org/xml/project/20"
_APP = "M-0083_A-013A-32-DCC1"

APPLICATION_XML = f"""<?xml version="1.0" encoding="utf-8"?>
<KNX xmlns="{_NS}" CreatedBy="ETS5" ToolVersion="5.7">
<ManufacturerData><Manufacturer RefId="M-0083">
<ApplicationPrograms>
<ApplicationProgram Id="{_APP}" ApplicationNumber="314" ApplicationVersion="50"
  MaskVersion="MV-07B0" Name="AKD-0424V.02" Hash="abc="
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
    <Dynamic>
      <ParameterBlock Id="{_APP}_MD-3_PB-1" Name="Page settings">
        <ComObjectRefRef RefId="{_APP}_MD-3_O-3-1_R-1" />
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


_Loaded = tuple[
    _RawIdentity,
    dict[str, ChannelDefinition],
    dict[str, ModuleDefinition],
    dict[str, ObjectDefinition],
    list[str],
]


def _load(language_code: str | None) -> _Loaded:
    return ApplicationProgramDefinitionLoader.load(
        io.BytesIO(APPLICATION_XML.encode("utf-8")), language_code=language_code
    )


def test_identity_attributes() -> None:
    """Root attributes and the KIM header are parsed."""
    identity, _, _, _, _ = _load(None)
    assert identity.application_id == _APP
    assert identity.application_number == 314
    assert identity.application_version == 50
    assert identity.name == "AKD-0424V.02"
    assert identity.mask_version == "MV-07B0"
    assert identity.program_hash == "abc="
    assert identity.kim_version == "92.60"


def test_channel_object_ids_deduplicated() -> None:
    """Objects referenced in several `when` branches appear once, in first-seen order."""
    _, channels, modules, objects, independent = _load(None)
    assert channels["MD-2_CH-1"]["object_ids"] == [
        "MD-2_O-2-1_R-1",
        "MD-2_O-2-3_R-1",
        "MD-2_O-2-1_R-2",
    ]
    assert channels["MD-2_CH-1"]["module_definition_id"] == "MD-2"
    assert channels["MD-2_CH-1"]["functional_blocks"] == ["417"]
    assert channels["MD-2_CH-1"]["text"] == "Channel {{ChNo}}: {{0}}"
    assert channels["CH-9"]["module_definition_id"] is None
    assert modules["MD-2"] == {
        "identifier": "MD-2",
        "name": "ModuleDefChannel",
        "channel_ids": ["MD-2_CH-1"],
    }
    assert independent == ["MD-3_O-3-1_R-1", "O-0_R-1"]
    # the same object can be channel independent and referenced by a channel
    assert objects["O-0_R-1"]["channel_ids"] == ["CH-9"]
    assert objects["MD-2_O-2-3_R-1"]["channel_ids"] == ["MD-2_CH-1"]


def test_refs_outside_channels_are_channel_independent() -> None:
    """Refs outside any Channel are channel independent, e.g. in a Channel-less ModuleDef."""
    _, _, modules, objects, independent = _load(None)
    assert "O-0_R-1" in independent  # in a ChannelIndependentBlock
    assert "MD-3_O-3-1_R-1" in independent  # in a ModuleDef without Channel
    assert objects["MD-3_O-3-1_R-1"]["channel_ids"] == []
    assert modules["MD-3"]["channel_ids"] == []


def test_object_definition_merges_ref_over_com_object() -> None:
    """ComObjectRef attributes override ComObject attributes."""
    _, _, _, objects, _ = _load(None)
    plain = objects["MD-2_O-2-1_R-1"]
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
    inverted = objects["MD-2_O-2-1_R-2"]
    assert inverted["text"] == "Switch inverted"
    assert inverted["dpts"] == [{"main": 1, "sub": 2}]
    assert inverted["dpas"] is None


def test_translations_applied() -> None:
    """Texts of objects, refs and channels are translated."""
    _, channels, _, objects, _ = _load("de-DE")
    assert objects["MD-2_O-2-1_R-1"]["text"] == "Schalten"
    assert objects["MD-2_O-2-1_R-1"]["function_text"] == "Ein/Aus"
    assert objects["MD-2_O-2-1_R-2"]["text"] == "Schalten invertiert"
    assert channels["MD-2_CH-1"]["text"] == "Kanal {{ChNo}}: {{0}}"


def test_translation_missing_language_keeps_defaults() -> None:
    """An unknown language leaves the default texts untouched."""
    _, channels, _, objects, _ = _load("fr-FR")
    assert objects["MD-2_O-2-1_R-1"]["text"] == "Switch"
    assert channels["MD-2_CH-1"]["text"] == "Channel {{ChNo}}: {{0}}"
