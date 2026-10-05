"""Test the application program definition loader."""

from __future__ import annotations

import io
import logging

import pytest

from xknxproject.exceptions import UnexpectedDataError
from xknxproject.loader import (
    ApplicationProgramDefinitionLoader,
    LoadedApplicationProgram,
)
from xknxproject.loader.application_program_definition_loader import _Placement

# ETS 5.7 project schema namespace; the loader takes it from the root element
_NS = "http://knx.org/xml/project/20"
_APP = "M-0083_A-013A-32-DCC1"

# Hand-written program covering: a channel inside a ModuleDef with refs repeated
# in choose/when branches, a Channel-less module (with a sub-module) instantiated
# in a channel, a module never instantiated, a ref that is channel independent and
# in a channel, ref attribute overrides and translations (Languages under
# Manufacturer, as in real files). "{{{{" in this f-string renders as "{{" in the XML.
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
          Text="Status feedback" Semantics="knx:dpa.417.51" />
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
</ApplicationProgram>
</ApplicationPrograms>
<Languages>
  <Language Identifier="de-DE">
    <TranslationUnit RefId="{_APP}">
      <TranslationElement RefId="{_APP}">
        <Translation AttributeName="Name" Text="AKD-0424V.02 Dimmaktor" />
      </TranslationElement>
      <TranslationElement RefId="{_APP}_MD-2_O-2-1">
        <Translation AttributeName="Text" Text="Schalten" />
        <Translation AttributeName="FunctionText" Text="Ein/Aus" />
      </TranslationElement>
      <TranslationElement RefId="{_APP}_MD-2_O-2-3">
        <Translation AttributeName="Text" Text="Rückmeldung" />
        <Translation AttributeName="FunctionText" Text="" />
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
</Manufacturer></ManufacturerData>
</KNX>
"""


def _load(language_code: str | None) -> LoadedApplicationProgram:
    """Load APPLICATION_XML in the given language."""
    return _load_xml(APPLICATION_XML, language_code)


def _load_xml(
    application_xml: str, language_code: str | None = None
) -> LoadedApplicationProgram:
    """Load an application program XML given as string."""
    return ApplicationProgramDefinitionLoader.load(
        io.BytesIO(application_xml.encode("utf-8")), language_code=language_code
    )


def _program_xml(module_defs: str, dynamic: str, static: str = "") -> str:
    """Return a minimal application program XML with the given sections."""
    return f"""<?xml version="1.0" encoding="utf-8"?>
<KNX xmlns="{_NS}">
<ManufacturerData><Manufacturer RefId="M-0083">
<ApplicationPrograms>
<ApplicationProgram Id="{_APP}" Name="Test">
<Static>{static}</Static>
<ModuleDefs>{module_defs}</ModuleDefs>
<Dynamic>{dynamic}</Dynamic>
</ApplicationProgram>
</ApplicationPrograms>
</Manufacturer></ManufacturerData>
</KNX>
"""


def _module_def(number: int, dynamic: str = "") -> str:
    """
    Return the ModuleDef "MD-<number>" with one object referenced in its Dynamic.

    The object definition is "MD-<number>_O-<number>-1_R-1"; `dynamic` is
    appended to the Dynamic section of the module.
    """
    module_id = f"{_APP}_MD-{number}"
    com_object_id = f"{module_id}_O-{number}-1"
    return f"""
<ModuleDef Id="{module_id}" Name="Module {number}">
  <Static>
    <ComObjectTable>
      <ComObject Id="{com_object_id}" Name="Object" Text="Object" Number="1"
        ObjectSize="1 Bit" />
    </ComObjectTable>
    <ComObjectRefs>
      <ComObjectRef Id="{com_object_id}_R-1" RefId="{com_object_id}" />
    </ComObjectRefs>
  </Static>
  <Dynamic>
    <ComObjectRefRef RefId="{com_object_id}_R-1" />{dynamic}
  </Dynamic>
</ModuleDef>"""


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


@pytest.mark.parametrize(
    ("semantics", "expected"),
    [
        (
            "# Serialization-Format-Version=2, "
            "KIM-Version=(<http://schema.knx.org/2020/ontology/v2>, 109, 77), @prefix",
            "109.77",
        ),
        (None, None),
        ("", None),
        ("# Serialization-Format-Version=2", None),
        ("KIM-Version=(<http://schema.knx.org/2020/ontology/v2>, 92)", None),
    ],
)
def test_parse_kim_version(semantics: str | None, expected: str | None) -> None:
    """The KIM version is read from the header, None without a valid one."""
    assert ApplicationProgramDefinitionLoader._parse_kim_version(semantics) == expected


def test_identity_without_optional_attributes() -> None:
    """Missing or non-integer optional attributes of the root element become None."""
    application_xml = _program_xml(module_defs="", dynamic="").replace(
        'Name="Test"', 'Name="Test" ApplicationVersion="1.0"'
    )
    identity = _load_xml(application_xml).identity
    assert identity.application_number is None
    assert identity.application_version is None
    assert identity.program_hash is None
    assert identity.kim_version is None
    assert identity.original_manufacturer is None
    assert identity.mask_version == ""


def test_missing_application_program_raises() -> None:
    """An XML without ApplicationProgram element is unexpected data."""
    with pytest.raises(UnexpectedDataError):
        _load_xml(f'<KNX xmlns="{_NS}"><ManufacturerData /></KNX>')


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
    """Texts of objects, refs and channels and the program name are translated."""
    loaded = _load("de-DE")
    assert loaded.identity.name == "AKD-0424V.02 Dimmaktor"
    assert loaded.objects["MD-2_O-2-1_R-1"]["text"] == "Schalten"
    assert loaded.objects["MD-2_O-2-1_R-1"]["function_text"] == "Ein/Aus"
    assert loaded.objects["MD-2_O-2-1_R-2"]["text"] == "Schalten invertiert"
    assert loaded.channels["MD-2_CH-1"]["text"] == "Kanal {{ChNo}}: {{0}}"


def test_translation_precedence() -> None:
    """
    A ref's own Text wins over the translated ComObject Text.

    A ref without own Text inherits the translated ComObject Text; an empty
    translation keeps the default text.
    """
    loaded = _load("de-DE")
    # MD-2_O-2-3 is translated, its ref has an own, untranslated Text
    assert loaded.objects["MD-2_O-2-3_R-1"]["text"] == "Status feedback"
    assert loaded.objects["MD-2_O-2-3_R-1"]["function_text"] == "On/Off"
    # MD-2_O-2-1_R-1 has no own Text
    assert loaded.objects["MD-2_O-2-1_R-1"]["text"] == "Schalten"


def test_translation_missing_language_keeps_defaults() -> None:
    """An unknown language leaves the default texts untouched."""
    loaded = _load("fr-FR")
    assert loaded.objects["MD-2_O-2-1_R-1"]["text"] == "Switch"
    assert loaded.channels["MD-2_CH-1"]["text"] == "Channel {{ChNo}}: {{0}}"


def test_cyclic_module_instantiation_terminates() -> None:
    """Modules instantiating each other do not recurse forever."""
    channel_refs: dict[str, dict[str, None]] = {"CH-1": {}}
    independent = ApplicationProgramDefinitionLoader._place_module_refs(
        channel_refs=channel_refs,
        module_ids=["MD-1", "MD-2", "MD-3", "MD-4"],
        module_refs={
            "MD-1": {"MD-1_O-1_R-1": None},
            "MD-2": {"MD-2_O-2_R-1": None},
            "MD-3": {"MD-3_O-3_R-1": None},
            "MD-4": {"MD-4_O-4_R-1": None},
        },
        module_placements=[
            # MD-1 in CH-1, MD-2 in MD-1 and MD-1 in MD-2
            ("MD-1", _Placement(channel_id="CH-1", module_id=None)),
            ("MD-2", _Placement(channel_id=None, module_id="MD-1")),
            ("MD-1", _Placement(channel_id=None, module_id="MD-2")),
            # MD-3 and MD-4 only instantiate each other
            ("MD-3", _Placement(channel_id=None, module_id="MD-4")),
            ("MD-4", _Placement(channel_id=None, module_id="MD-3")),
        ],
        independent_candidates=[
            ("MD-1", "MD-1_O-1_R-1"),
            ("MD-2", "MD-2_O-2_R-1"),
            ("MD-3", "MD-3_O-3_R-1"),
            ("MD-4", "MD-4_O-4_R-1"),
        ],
    )
    assert list(channel_refs["CH-1"]) == ["MD-1_O-1_R-1", "MD-2_O-2_R-1"]
    # modules only reachable through a cycle are treated as not instantiated
    assert independent == ["MD-3_O-3_R-1", "MD-4_O-4_R-1"]


def test_module_refs_follow_document_order_of_the_channel() -> None:
    """Modules of a channel add their refs in the order of the channel's Module elements."""
    loaded = _load_xml(
        _program_xml(
            module_defs=_module_def(1) + _module_def(2),
            dynamic=f"""
            <Channel Id="{_APP}_CH-0" Name="First" Number="0">
              <Module Id="{_APP}_MD-1_M-1" RefId="{_APP}_MD-1" />
            </Channel>
            <Channel Id="{_APP}_CH-1" Name="Second" Number="1">
              <Module Id="{_APP}_MD-2_M-1" RefId="{_APP}_MD-2" />
              <Module Id="{_APP}_MD-1_M-2" RefId="{_APP}_MD-1" />
            </Channel>
            """,
        )
    )
    assert loaded.channels["CH-0"]["object_ids"] == ["MD-1_O-1-1_R-1"]
    assert loaded.channels["CH-1"]["object_ids"] == [
        "MD-2_O-2-1_R-1",
        "MD-1_O-1-1_R-1",
    ]
    assert loaded.objects["MD-1_O-1-1_R-1"]["channel_ids"] == ["CH-0", "CH-1"]


def test_unresolved_refs_are_dropped_with_one_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Refs without ComObjectRef or ComObject are left out of every id list."""
    loaded = _load_xml(
        _program_xml(
            static=f"""
            <ComObjectTable>
              <ComObject Id="{_APP}_O-1" Name="Valid" Text="Valid" Number="1" />
            </ComObjectTable>
            <ComObjectRefs>
              <ComObjectRef Id="{_APP}_O-1_R-1" RefId="{_APP}_O-1" />
              <ComObjectRef Id="{_APP}_O-2_R-1" RefId="{_APP}_O-2" />
            </ComObjectRefs>
            """,
            module_defs=_module_def(1),
            dynamic=f"""
            <ComObjectRefRef RefId="{_APP}_O-1_R-1" />
            <ComObjectRefRef RefId="{_APP}_O-2_R-1" />
            <ComObjectRefRef RefId="{_APP}_O-9_R-9" />
            <Channel Id="{_APP}_CH-1" Name="Channel" Number="1">
              <ComObjectRefRef RefId="{_APP}_O-9_R-9" />
              <ComObjectRefRef RefId="{_APP}_O-1_R-1" />
              <ComObjectRefRef RefId="{_APP}_O-2_R-1" />
              <Module Id="{_APP}_MD-1_M-1" RefId="{_APP}_MD-1" />
            </Channel>
            """,
        )
    )
    assert loaded.channels["CH-1"]["object_ids"] == ["O-1_R-1", "MD-1_O-1-1_R-1"]
    assert loaded.channel_independent_object_ids == ["O-1_R-1"]
    assert set(loaded.objects) == {"O-1_R-1", "MD-1_O-1-1_R-1"}
    assert [(record.levelno, record.getMessage()) for record in caplog.records] == [
        (
            logging.WARNING,
            f"Application program {_APP}: ignoring object references without "
            "ComObjectRef or ComObject: O-2_R-1, O-9_R-9",
        )
    ]


def test_module_placed_in_and_outside_channels_is_in_both_lists() -> None:
    """Refs of a module instantiated at top level and in a channel are in both lists."""
    loaded = _load_xml(
        _program_xml(
            module_defs=_module_def(1),
            dynamic=f"""
            <Module Id="{_APP}_MD-1_M-1" RefId="{_APP}_MD-1" />
            <Channel Id="{_APP}_CH-1" Name="Channel" Number="1">
              <Module Id="{_APP}_MD-1_M-2" RefId="{_APP}_MD-1" />
            </Channel>
            """,
        )
    )
    assert loaded.channel_independent_object_ids == ["MD-1_O-1-1_R-1"]
    assert loaded.channels["CH-1"]["object_ids"] == ["MD-1_O-1-1_R-1"]
    assert loaded.objects["MD-1_O-1-1_R-1"]["channel_ids"] == ["CH-1"]


def test_modules_in_repeat_belong_to_the_enclosing_channel() -> None:
    """A Module inside a Repeat, also inside a module, belongs to the enclosing channel."""
    repeat_in_module = f"""
      <Repeat Id="{_APP}_MD-2_X-1" Name="" ParameterRefId="{_APP}_MD-2_P-1_R-1">
        <Module Id="{_APP}_MD-1_M-1" RefId="{_APP}_MD-1" />
      </Repeat>"""
    loaded = _load_xml(
        _program_xml(
            module_defs=_module_def(1) + _module_def(2, dynamic=repeat_in_module),
            dynamic=f"""
            <Channel Id="{_APP}_CH-1" Name="Channel" Number="1">
              <Repeat Id="{_APP}_X-1" Name="" ParameterRefId="{_APP}_P-1_R-1">
                <Module Id="{_APP}_MD-2_M-1" RefId="{_APP}_MD-2" />
              </Repeat>
            </Channel>
            """,
        )
    )
    assert loaded.channels["CH-1"]["object_ids"] == [
        "MD-2_O-2-1_R-1",
        "MD-1_O-1-1_R-1",
    ]
    assert loaded.channel_independent_object_ids == []


def test_channel_independent_block_in_module_follows_the_module() -> None:
    """A ChannelIndependentBlock inside a ModuleDef is not treated specially."""
    channel_independent_block = f"""
      <ChannelIndependentBlock>
        <ComObjectRefRef RefId="{_APP}_MD-1_O-1-1_R-1" />
      </ChannelIndependentBlock>"""
    loaded = _load_xml(
        _program_xml(
            module_defs=_module_def(1, dynamic=channel_independent_block),
            dynamic=f"""
            <Channel Id="{_APP}_CH-1" Name="Channel" Number="1">
              <Module Id="{_APP}_MD-1_M-1" RefId="{_APP}_MD-1" />
            </Channel>
            """,
        )
    )
    assert loaded.channels["CH-1"]["object_ids"] == ["MD-1_O-1-1_R-1"]
    assert loaded.channel_independent_object_ids == []
