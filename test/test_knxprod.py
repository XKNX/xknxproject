"""Test parsing standalone KNX products (.knxprod)."""

from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

from xknxproject import XKNXProd
from xknxproject.loader import ApplicationProgramLoader
from xknxproject.zip.extractor import extract_prod

# Synthetic System B (MV-07B0) application program exercising the product parser:
# two communication objects (one with a ComObjectRef DPT + flag override), a
# relative memory segment, an 8-bit number parameter and an enumeration
# parameter (both stored in memory), one parameter without a Memory location,
# a float parameter (camelCase minInclusive, size derived from encoding), a
# Union whose members inherit the shared Memory shifted by their own offsets,
# and a ParameterRef Value override. ModuleDefs and Dynamic sections are
# included to verify parsing excludes them.
APPLICATION_PROGRAM_ID = "M-00FA_A-1234-10-0000"
APPLICATION_PROGRAM_XML = f"""<?xml version="1.0"?>
<KNX xmlns="http://knx.org/xml/project/21">
  <ManufacturerData>
    <Manufacturer RefId="M-00FA">
      <ApplicationPrograms>
        <ApplicationProgram Id="{APPLICATION_PROGRAM_ID}" ApplicationNumber="4660"
            ApplicationVersion="16" MaskVersion="MV-07B0" Name="Test Product"
            LoadProcedureStyle="MergedProcedure" PeiType="0"
            DynamicTableManagement="false">
          <Static>
            <Code>
              <RelativeSegment Id="{APPLICATION_PROGRAM_ID}_RS-04-00000" Name=""
                  Size="16" LoadStateMachine="4" Offset="0" />
            </Code>
            <ComObjectTable>
              <ComObject Id="{APPLICATION_PROGRAM_ID}_O-1" Name="switch" Text=""
                  Number="0" FunctionText="Switch" ObjectSize="1 Bit"
                  ReadFlag="Disabled" WriteFlag="Enabled" CommunicationFlag="Enabled"
                  TransmitFlag="Disabled" UpdateFlag="Disabled" ReadOnInitFlag="Disabled"
                  DatapointType="DPST-1-1" />
              <ComObject Id="{APPLICATION_PROGRAM_ID}_O-2" Name="status" Text=""
                  Number="1" FunctionText="Status" ObjectSize="1 Byte"
                  ReadFlag="Enabled" WriteFlag="Disabled" CommunicationFlag="Enabled"
                  TransmitFlag="Enabled" UpdateFlag="Disabled" ReadOnInitFlag="Disabled"
                  DatapointType="DPST-5-1" />
            </ComObjectTable>
            <ComObjectRefs>
              <ComObjectRef Id="{APPLICATION_PROGRAM_ID}_O-1_R-1"
                  RefId="{APPLICATION_PROGRAM_ID}_O-1" />
              <ComObjectRef Id="{APPLICATION_PROGRAM_ID}_O-2_R-2"
                  RefId="{APPLICATION_PROGRAM_ID}_O-2" DatapointType="DPST-5-10"
                  WriteFlag="Enabled" />
            </ComObjectRefs>
            <Parameters>
              <Parameter Id="{APPLICATION_PROGRAM_ID}_P-1" Name="brightness"
                  ParameterType="{APPLICATION_PROGRAM_ID}_PT-num" Text="Brightness"
                  Value="50">
                <Memory CodeSegment="{APPLICATION_PROGRAM_ID}_RS-04-00000" Offset="0"
                    BitOffset="0" />
              </Parameter>
              <Parameter Id="{APPLICATION_PROGRAM_ID}_P-2" Name="mode"
                  ParameterType="{APPLICATION_PROGRAM_ID}_PT-enum" Text="Mode" Value="1">
                <Memory CodeSegment="{APPLICATION_PROGRAM_ID}_RS-04-00000" Offset="1"
                    BitOffset="0" />
              </Parameter>
              <Parameter Id="{APPLICATION_PROGRAM_ID}_P-3" Name="hidden"
                  ParameterType="{APPLICATION_PROGRAM_ID}_PT-enum" Text="Hidden"
                  Value="0" />
              <Parameter Id="{APPLICATION_PROGRAM_ID}_P-4" Name="setpoint"
                  ParameterType="{APPLICATION_PROGRAM_ID}_PT-float" Text="Setpoint"
                  Value="21">
                <Memory CodeSegment="{APPLICATION_PROGRAM_ID}_RS-04-00000" Offset="2"
                    BitOffset="0" />
              </Parameter>
              <Union SizeInBit="8">
                <Memory CodeSegment="{APPLICATION_PROGRAM_ID}_RS-04-00000" Offset="4"
                    BitOffset="0" />
                <Parameter Id="{APPLICATION_PROGRAM_ID}_UP-1" Name="scene"
                    ParameterType="{APPLICATION_PROGRAM_ID}_PT-num" Text="Scene"
                    Value="0" Offset="0" BitOffset="0" />
                <Parameter Id="{APPLICATION_PROGRAM_ID}_UP-2" Name="scene_off"
                    ParameterType="{APPLICATION_PROGRAM_ID}_PT-num" Text=""
                    Value="255" Offset="0" BitOffset="4" />
              </Union>
            </Parameters>
            <ParameterTypes>
              <ParameterType Id="{APPLICATION_PROGRAM_ID}_PT-num" Name="PT_num">
                <TypeNumber SizeInBit="8" Type="unsignedInt" minInclusive="0"
                    maxInclusive="100" />
              </ParameterType>
              <ParameterType Id="{APPLICATION_PROGRAM_ID}_PT-float" Name="PT_float">
                <TypeFloat Encoding="DPT 9" minInclusive="7.5" maxInclusive="30" />
              </ParameterType>
              <ParameterType Id="{APPLICATION_PROGRAM_ID}_PT-enum" Name="PT_enum">
                <TypeRestriction Base="Value" SizeInBit="8">
                  <Enumeration Text="off" Value="0"
                      Id="{APPLICATION_PROGRAM_ID}_PT-enum_EN-0" />
                  <Enumeration Text="on" Value="1"
                      Id="{APPLICATION_PROGRAM_ID}_PT-enum_EN-1" />
                </TypeRestriction>
              </ParameterType>
            </ParameterTypes>
            <ParameterRefs>
              <ParameterRef Id="{APPLICATION_PROGRAM_ID}_P-1_R-1"
                  RefId="{APPLICATION_PROGRAM_ID}_P-1" Value="60" />
              <ParameterRef Id="{APPLICATION_PROGRAM_ID}_P-2_R-2"
                  RefId="{APPLICATION_PROGRAM_ID}_P-2" />
            </ParameterRefs>
          </Static>
          <ModuleDefs>
            <!-- instantiation templates; must be excluded by the parser -->
            <ModuleDef Id="{APPLICATION_PROGRAM_ID}_MD-1" Name="Module 1">
              <Static>
                <Parameters>
                  <Parameter Id="{APPLICATION_PROGRAM_ID}_MD-1_P-1" Name="mod_param"
                      ParameterType="{APPLICATION_PROGRAM_ID}_PT-num" Text="Module"
                      Value="0" />
                </Parameters>
                <ComObjectRefs>
                  <ComObjectRef Id="{APPLICATION_PROGRAM_ID}_MD-1_O-1_R-1"
                      RefId="{APPLICATION_PROGRAM_ID}_O-1" />
                </ComObjectRefs>
              </Static>
              <Dynamic />
            </ModuleDef>
          </ModuleDefs>
          <Dynamic>
            <!-- must be ignored by the parser -->
            <Channel Id="{APPLICATION_PROGRAM_ID}_CH-1" Name="Channel 1" Number="1"
                Text="Channel 1">
              <ParameterRefRef RefId="{APPLICATION_PROGRAM_ID}_P-1_R-1" />
              <ComObjectRefRef RefId="{APPLICATION_PROGRAM_ID}_O-1_R-1" />
            </Channel>
          </Dynamic>
        </ApplicationProgram>
      </ApplicationPrograms>
    </Manufacturer>
  </ManufacturerData>
</KNX>
"""


@pytest.fixture
def application_program_xml(tmp_path: Path) -> Path:
    """Write the synthetic application program to a standalone XML file."""
    path = tmp_path / f"{APPLICATION_PROGRAM_ID}.xml"
    path.write_text(APPLICATION_PROGRAM_XML, encoding="utf-8")
    return path


@pytest.fixture
def knxprod_path(tmp_path: Path) -> Path:
    """Build a minimal .knxprod archive around the synthetic application program."""
    path = tmp_path / "test_product.knxprod"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "knx_master.xml",
            '<?xml version="1.0"?>\n<KNX xmlns="http://knx.org/xml/project/21"></KNX>\n',
        )
        archive.writestr("M-00FA.signature", "signature")
        archive.writestr(
            f"M-00FA/{APPLICATION_PROGRAM_ID}.xml", APPLICATION_PROGRAM_XML
        )
    return path


def test_load_static(application_program_xml: Path) -> None:
    """Test the complete (unfiltered) application program parse."""
    # load_static() takes a zipfile.Path in production; a plain Path works here
    # since it only relies on .open()
    app = ApplicationProgramLoader.load_static(application_program_xml)  # type: ignore[arg-type]

    assert app.identifier == APPLICATION_PROGRAM_ID
    assert app.application_number == 4660
    assert app.application_version == 16
    assert app.mask_version == "MV-07B0"
    assert app.pei_type == 0
    assert app.dynamic_table_management is False

    # communication objects (Dynamic content is not counted)
    assert len(app.com_objects) == 2
    assert len(app.com_object_refs) == 2
    switch = app.com_objects[f"{APPLICATION_PROGRAM_ID}_O-1"]
    assert switch.number == 0
    assert switch.object_size == "1 Bit"
    assert switch.datapoint_types == [{"main": 1, "sub": 1}]
    assert switch.communication_flag is True
    assert switch.write_flag is True
    assert switch.read_flag is False

    # parameters (ModuleDef templates are not counted)
    assert len(app.parameters) == 6
    assert f"{APPLICATION_PROGRAM_ID}_MD-1_P-1" not in app.parameters
    brightness = app.parameters[f"{APPLICATION_PROGRAM_ID}_P-1"]
    assert brightness.memory is not None
    assert brightness.memory.offset == 0
    assert brightness.memory.bit_offset == 0
    assert brightness.value == "50"
    hidden = app.parameters[f"{APPLICATION_PROGRAM_ID}_P-3"]
    assert hidden.memory is None  # not stored in memory

    # union members share the union Memory shifted by their own offsets
    scene = app.parameters[f"{APPLICATION_PROGRAM_ID}_UP-1"]
    assert scene.memory is not None
    assert scene.memory.segment_ref == f"{APPLICATION_PROGRAM_ID}_RS-04-00000"
    assert scene.memory.offset == 4
    assert scene.memory.bit_offset == 0
    scene_off = app.parameters[f"{APPLICATION_PROGRAM_ID}_UP-2"]
    assert scene_off.memory is not None
    assert scene_off.memory.offset == 4
    assert scene_off.memory.bit_offset == 4

    # parameter types
    num = app.parameter_types[f"{APPLICATION_PROGRAM_ID}_PT-num"]
    assert num.kind == "TypeNumber"
    assert num.size_in_bit == 8
    assert num.minimum == 0
    assert num.maximum == 100
    enum = app.parameter_types[f"{APPLICATION_PROGRAM_ID}_PT-enum"]
    assert enum.kind == "TypeRestriction"
    assert enum.base == "Value"
    assert enum.enumerations == {0: "off", 1: "on"}
    flt = app.parameter_types[f"{APPLICATION_PROGRAM_ID}_PT-float"]
    assert flt.kind == "TypeFloat"
    assert flt.encoding == "DPT 9"
    assert flt.size_in_bit == 16  # derived from the encoding
    assert flt.minimum == 7.5
    assert flt.maximum == 30

    # segment
    assert len(app.segments) == 1
    segment = app.segments[f"{APPLICATION_PROGRAM_ID}_RS-04-00000"]
    assert segment.kind == "relative"
    assert segment.size == 16
    assert segment.load_state_machine == 4


def test_parse_product(knxprod_path: Path) -> None:
    """Test parsing a .knxprod into the public KNXProduct output."""
    product = XKNXProd(knxprod_path).parse()

    assert product["manufacturer"] == "M-00FA"
    assert product["schema_version"] == 21
    assert list(product["application_programs"]) == [APPLICATION_PROGRAM_ID]

    app = product["application_programs"][APPLICATION_PROGRAM_ID]
    assert app["name"] == "Test Product"
    assert app["application_number"] == 4660
    assert app["mask_version"] == "MV-07B0"
    assert app["pei_type"] == 0

    com_objects = {co["number"]: co for co in app["communication_objects"]}
    assert set(com_objects) == {0, 1}

    switch = com_objects[0]
    assert switch["object_size"] == "1 Bit"
    assert switch["dpts"] == [{"main": 1, "sub": 1}]
    assert switch["flags"]["communication"] is True
    assert switch["flags"]["write"] is True

    # ComObjectRef overrides win over the base ComObject
    status = com_objects[1]
    assert status["object_size"] == "1 Byte"  # not overridden -> from base
    assert status["dpts"] == [{"main": 5, "sub": 10}]  # overridden on the ref
    assert status["flags"]["write"] is True  # overridden on the ref
    assert status["flags"]["communication"] is True  # inherited from the base

    parameters = {p["name"]: p for p in app["parameters"]}
    assert set(parameters) == {
        "brightness",
        "mode",
        "hidden",
        "setpoint",
        "scene",
        "scene_off",
    }
    assert parameters["brightness"]["segment"] is not None
    assert parameters["brightness"]["offset"] == 0
    assert parameters["brightness"]["type"] == "TypeNumber"
    assert parameters["brightness"]["size_in_bit"] == 8
    assert parameters["brightness"]["minimum"] == 0
    assert parameters["brightness"]["maximum"] == 100
    assert parameters["brightness"]["value"] == "60"  # ParameterRef override
    assert parameters["mode"]["value"] == "1"  # ref without Value -> no override
    assert parameters["mode"]["enumerations"] == {0: "off", 1: "on"}
    assert parameters["hidden"]["segment"] is None  # not stored in memory
    assert parameters["hidden"]["offset"] is None
    assert parameters["setpoint"]["type"] == "TypeFloat"
    assert parameters["setpoint"]["size_in_bit"] == 16
    assert parameters["setpoint"]["minimum"] == 7.5
    assert parameters["setpoint"]["maximum"] == 30
    assert parameters["scene"]["offset"] == 4
    assert parameters["scene"]["bit_offset"] == 0
    assert parameters["scene_off"]["offset"] == 4
    assert parameters["scene_off"]["bit_offset"] == 4

    assert len(app["segments"]) == 1
    assert app["segments"][0]["object_index"] == 4


def test_extract_prod(knxprod_path: Path) -> None:
    """Test the .knxprod container extraction."""
    with extract_prod(knxprod_path) as contents:
        assert contents.manufacturer_id == "M-00FA"
        assert contents.schema_version == 21
        paths = contents.application_program_paths()
        assert len(paths) == 1
        assert paths[0].name == f"{APPLICATION_PROGRAM_ID}.xml"
