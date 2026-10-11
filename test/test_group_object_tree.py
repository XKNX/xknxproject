"""Test parsing the GroupObjectTree of devices - channels and folders."""

from __future__ import annotations

from xml.etree import ElementTree

from xknxproject import XKNXProj
from xknxproject.loader.project_loader import _TopologyLoader
from xknxproject.models import (
    ApplicationProgram,
    ApplicationProgramParameterBlock,
    ChannelNode,
    FolderNode,
    ModuleInstance,
    ModuleInstanceArgument,
    ParameterInstanceRef,
)
from xknxproject.models.knxproject import GroupObjectTreeNode

from . import RESOURCES_PATH
from .conftest import build_devices

# ETS 6 project schema namespace; the loader matches any namespace (`{*}`)
_NS = "http://knx.org/xml/project/23"
_APPLICATION = "M-00FA_A-A012-55-E5F5"


def _parse_tree(
    group_object_tree_xml: str,
) -> tuple[list[ChannelNode | FolderNode], list[ChannelNode]]:
    """Parse a `GroupObjectTree` element into its nodes and the flat channel list."""
    channels: list[ChannelNode] = []
    nodes = _TopologyLoader._parse_group_object_tree_nodes(  # pylint: disable=protected-access
        ElementTree.fromstring(group_object_tree_xml), channels
    )
    return nodes, channels


def _application(
    *parameter_blocks: ApplicationProgramParameterBlock,
) -> ApplicationProgram:
    return ApplicationProgram(
        com_objects={},
        com_object_refs={},
        allocators={},
        module_def_arguments={},
        numeric_args={},
        channels={},
        parameter_blocks={block.identifier: block for block in parameter_blocks},
    )


def test_folders_are_nested_below_their_channel() -> None:
    """Folders keep their place in the tree and their own communication objects."""
    nodes, channels = _parse_tree(
        f"""
        <GroupObjectTree xmlns="{_NS}">
          <Nodes>
            <Node Type="Channel" RefId="CH-BASE" GroupObjectInstances="O-1_R-1 O-2_R-2" />
            <Node Type="Channel" RefId="CH-23">
              <Nodes>
                <Node Type="Folder" RefId="PB-1300" GroupObjectInstances="O-448_R-8" />
                <Node Type="Folder" RefId="PB-1301">
                  <Nodes>
                    <Node Type="Folder" RefId="PB-1303" GroupObjectInstances="O-460_R-1 O-461_R-2" />
                  </Nodes>
                </Node>
              </Nodes>
            </Node>
          </Nodes>
        </GroupObjectTree>
        """
    )

    assert [channel.ref_id for channel in channels] == ["CH-BASE", "CH-23"]
    base, shutter = nodes
    assert base.group_object_instances == ["O-1_R-1", "O-2_R-2"]
    assert base.nodes == []
    # a channel holding its communication objects in folders only is kept
    assert isinstance(shutter, ChannelNode)
    assert shutter.group_object_instances == []
    general, channel_1 = shutter.nodes
    assert isinstance(general, FolderNode)
    assert (general.ref_id, general.group_object_instances) == (
        "PB-1300",
        ["O-448_R-8"],
    )
    assert channel_1.group_object_instances == []
    assert [(node.ref_id, node.group_object_instances) for node in channel_1.nodes] == [
        ("PB-1303", ["O-460_R-1", "O-461_R-2"])
    ]


def test_unused_nodes_are_omitted() -> None:
    """Nodes without a communication object anywhere below them are not parsed."""
    nodes, channels = _parse_tree(
        f"""
        <GroupObjectTree xmlns="{_NS}">
          <Nodes>
            <Node Type="Channel" RefId="CH-UCT" />
            <Node Type="Channel" RefId="CH-SENS">
              <Nodes>
                <Node Type="Folder" RefId="PB-30" />
                <Node Type="Folder" RefId="PB-31" GroupObjectInstances="O-45_R-1" />
              </Nodes>
            </Node>
            <Node Type="Folder" RefId="PB-2">
              <Nodes>
                <Node Type="Folder" RefId="PB-3" />
              </Nodes>
            </Node>
          </Nodes>
        </GroupObjectTree>
        """
    )

    assert [channel.ref_id for channel in channels] == ["CH-SENS"]
    assert [node.ref_id for node in nodes] == ["CH-SENS"]
    assert [node.ref_id for node in nodes[0].nodes] == ["PB-31"]


def test_channels_below_folders_are_listed_in_document_order() -> None:
    """Channels are collected regardless of their depth; folders may sit on top."""
    nodes, channels = _parse_tree(
        f"""
        <GroupObjectTree xmlns="{_NS}">
          <Nodes>
            <Node Type="Folder" RefId="PB-1">
              <Nodes>
                <Node Type="Channel" RefId="CH-1" GroupObjectInstances="O-1_R-1">
                  <Nodes>
                    <Node Type="Folder" RefId="PB-4" GroupObjectInstances="O-2_R-2" />
                  </Nodes>
                </Node>
                <Node Type="Channel" RefId="CH-2" GroupObjectInstances="O-3_R-3" />
              </Nodes>
            </Node>
            <Node Type="Channel" RefId="CH-3" GroupObjectInstances="O-4_R-4" />
          </Nodes>
        </GroupObjectTree>
        """
    )

    assert [channel.ref_id for channel in channels] == ["CH-1", "CH-2", "CH-3"]
    assert [(type(node), node.ref_id) for node in nodes] == [
        (FolderNode, "PB-1"),
        (ChannelNode, "CH-3"),
    ]
    assert [node.ref_id for node in nodes[0].nodes] == ["CH-1", "CH-2"]


def test_device_without_group_object_tree() -> None:
    """A device without the element has no tree and no channels."""
    channels: list[ChannelNode] = []
    assert (
        _TopologyLoader._parse_group_object_tree_nodes(None, channels)  # pylint: disable=protected-access
        == []
    )
    assert channels == []


def test_folder_name_from_the_application_program() -> None:
    """ETS 6 nodes carry no Text - the name is the text of the ParameterBlock."""
    (device,) = build_devices(("P-1_DI-1", 1))
    device.application_program_ref = _APPLICATION
    device.group_object_tree = [
        FolderNode(ref_id="PB-31", name="", group_object_instances=["O-45_R-1"]),
        FolderNode(ref_id="PB-32", name="", group_object_instances=["O-46_R-1"]),
        FolderNode(ref_id="PB-99", name="", group_object_instances=["O-47_R-1"]),
        FolderNode(ref_id="PB-40", name="Kept", group_object_instances=["O-48_R-1"]),
    ]
    device.merge_application_program_info(
        _application(
            ApplicationProgramParameterBlock(
                identifier=f"{_APPLICATION}_PB-31",
                name="SENS_Helligkeit",
                text="Helligkeit",
                text_parameter_ref_id=None,
            ),
            ApplicationProgramParameterBlock(
                identifier=f"{_APPLICATION}_PB-32",
                name="SENS_Humidity",
                text=None,
                text_parameter_ref_id=None,
            ),
            ApplicationProgramParameterBlock(
                identifier=f"{_APPLICATION}_PB-40",
                name="Other",
                text="Other",
                text_parameter_ref_id=None,
            ),
        )
    )

    assert [folder.name for folder in device.folders()] == [
        "Helligkeit",
        "SENS_Humidity",  # falls back to the name without a text
        "",  # ParameterBlock unknown
        "Kept",  # the text of the node takes precedence
    ]


def test_folder_name_text_parameter() -> None:
    """The text parameter template is filled from the device, or by its default."""
    (device,) = build_devices(("P-1_DI-1", 1))
    device.application_program_ref = _APPLICATION
    device.parameter_instance_refs = {
        f"{_APPLICATION}_P-1_R-1": ParameterInstanceRef(
            ref_id=f"{_APPLICATION}_P-1_R-1", value="Bad"
        )
    }
    device.group_object_tree = [
        FolderNode(ref_id="PB-707", name="", group_object_instances=["O-1_R-1"]),
        FolderNode(ref_id="PB-708", name="", group_object_instances=["O-2_R-1"]),
        FolderNode(
            ref_id="PB-36", name="{{0:Steuerungen}}", group_object_instances=["O-3_R-1"]
        ),
    ]
    device.merge_application_program_info(
        _application(
            ApplicationProgramParameterBlock(
                identifier=f"{_APPLICATION}_PB-707",
                name="PM_PM1Page",
                text="PM 1: {{0: ...}}",
                text_parameter_ref_id=f"{_APPLICATION}_P-1_R-1",
            ),
            ApplicationProgramParameterBlock(
                identifier=f"{_APPLICATION}_PB-708",
                name="PM_PM2Page",
                text="PM 2: {{0:unbenannt}}",
                text_parameter_ref_id=f"{_APPLICATION}_P-2_R-2",  # not set in device
            ),
        )
    )

    assert [folder.name for folder in device.folders()] == [
        "PM 1: Bad",
        "PM 2: unbenannt",
        "Steuerungen",  # no ParameterBlock - the default of the node text
    ]


def test_folder_name_in_module_instance() -> None:
    """Folders of modules resolve the ParameterBlock and arguments of their instance."""
    (device,) = build_devices(("P-1_DI-1", 1))
    device.application_program_ref = _APPLICATION
    device.module_instances = [
        ModuleInstance(
            identifier="MD-1_M-2_MI-1",
            ref_id="MD-1_M-2",
            arguments=[
                ModuleInstanceArgument(
                    ref_id=f"{_APPLICATION}_MD-1_A-1", value="7", name="ECG_NO"
                )
            ],
        )
    ]
    device.parameter_instance_refs = {
        f"{_APPLICATION}_MD-1_M-2_MI-1_P-27_R-27": ParameterInstanceRef(
            ref_id=f"{_APPLICATION}_MD-1_M-2_MI-1_P-27_R-27", value="Flur"
        )
    }
    folder = FolderNode(
        ref_id="MD-1_M-2_MI-1_PB-1", name="", group_object_instances=["O-1_R-1"]
    )
    application = _application(
        ApplicationProgramParameterBlock(
            identifier=f"{_APPLICATION}_MD-1_PB-1",
            name="ECG1",
            text="ECG {{ECG_NO}}, {{0:Leuchte {{ECG_NO}}}}",
            text_parameter_ref_id=f"{_APPLICATION}_MD-1_P-27_R-27",
        )
    )
    folder.resolve_folder_attributes(
        device_instance=device,
        application=application,
        module_arguments=device.module_arguments(folder.ref_id, application),
    )
    assert folder.name == "ECG 7, Flur"

    # without a parameter value the default applies - module argument resolved in it
    device.parameter_instance_refs = {}
    folder.name = ""
    folder.resolve_folder_attributes(
        device_instance=device,
        application=application,
        module_arguments=device.module_arguments(folder.ref_id, application),
    )
    assert folder.name == "ECG 7, Leuchte 7"


def _find_node(
    nodes: list[GroupObjectTreeNode], identifier: str
) -> GroupObjectTreeNode:
    return next(node for node in nodes if node["identifier"] == identifier)


def test_group_object_tree_of_parsed_project() -> None:
    """The exported tree nests channels and folders around the linked objects."""
    project = XKNXProj(
        RESOURCES_PATH / "module-definition-test.knxproj", language="De"
    ).parse()

    # all linked communication objects of this device sit in folders of channels
    # listing none themselves - `channels` does not know about them
    device = project["devices"]["1.1.3"]
    assert device["channels"] == {}

    ecg = _find_node(device["group_object_tree"], "CH-17")
    assert (ecg["type"], ecg["name"]) == ("Channel", "EVG")
    assert ecg["communication_object_ids"] == []
    # only the two of its folders holding a linked communication object remain
    assert [node["identifier"] for node in ecg["nodes"]] == [
        "MD-1_M-1_MI-1_PB-1",
        "MD-1_M-1_MI-4_PB-1",
    ]
    ecg_1 = ecg["nodes"][0]
    # "EVG {{ECG_NO}}, {{0}}" - the text parameter is resolved; the module argument
    # is computed from an allocator and keeps its placeholder, like in channel names
    assert (ecg_1["type"], ecg_1["name"]) == ("Folder", "EVG {{ECG_NO}}, ")
    (behaviour,) = ecg_1["nodes"]
    assert behaviour["name"] == "Verhalten"
    assert behaviour["communication_object_ids"] == ["1.1.3/MD-1_M-1_MI-1_O-2-0_R-7"]
    assert behaviour["nodes"] == []

    # a folder may hold communication objects and folders at once
    motion = _find_node(device["group_object_tree"], "CH-84")
    assert motion["nodes"][0]["communication_object_ids"] == [
        "1.1.3/MD-3_M-2_MI-2_O-2-4_R-5"
    ]
    assert motion["nodes"][1]["communication_object_ids"] == []
    assert [node["name"] for node in motion["nodes"][1]["nodes"]] == ["Helligkeit"]


def test_group_object_tree_lists_exported_communication_objects_only() -> None:
    """Every id of a tree is a key of `communication_objects`; no node is empty."""
    for file_stem, password in (
        ("module-definition-test", None),
        ("smart_linking", "test"),
        ("xknx_test_project", "test"),
    ):
        project = XKNXProj(
            RESOURCES_PATH / f"{file_stem}.knxproj", password, language="de-DE"
        ).parse()

        def _check(nodes: list[GroupObjectTreeNode], device_ids: set[str]) -> int:
            count = 0
            for node in nodes:
                assert set(node["communication_object_ids"]) <= device_ids
                below = _check(node["nodes"], device_ids)
                assert node["communication_object_ids"] or below, node["identifier"]
                count += len(node["communication_object_ids"]) + below
            return count

        in_trees = 0
        for device in project["devices"].values():
            in_trees += _check(
                device["group_object_tree"], set(device["communication_object_ids"])
            )
            # channels are exported as before: those listing objects themselves
            assert all(
                channel["communication_object_ids"]
                for channel in device["channels"].values()
            )
        assert in_trees > 0
