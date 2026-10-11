"""Test models."""

from __future__ import annotations

import pytest

from xknxproject.models import (
    ApplicationProgram,
    ComObject,
    ComObjectInstanceRef,
    ComObjectRef,
)


def _instance(
    ref_id: str = "MD-1_M-1_MI-1_O-1_R-1",
    com_object_ref_id: str | None = "A_MD-1_O-1_R-1",
    name: str | None = None,
    text: str | None = None,
    function_text: str | None = None,
) -> ComObjectInstanceRef:
    return ComObjectInstanceRef(
        identifier=None,
        ref_id=ref_id,
        text=text,
        function_text=function_text,
        read_flag=None,
        write_flag=None,
        communication_flag=None,
        transmit_flag=None,
        update_flag=None,
        read_on_init_flag=None,
        datapoint_types=[],
        description=None,
        channel=None,
        links=[],
        com_object_ref_id=com_object_ref_id,
        name=name,
    )


def _com_object_ref(
    name: str | None, text: str | None, function_text: str | None
) -> ComObjectRef:
    return ComObjectRef(
        identifier="A_MD-1_O-1_R-1",
        ref_id="A_MD-1_O-1",
        name=name,
        text=text,
        function_text=function_text,
        object_size=None,
        read_flag=None,
        write_flag=None,
        communication_flag=None,
        transmit_flag=None,
        update_flag=None,
        read_on_init_flag=None,
        datapoint_types=[],
        text_parameter_ref_id=None,
        semantics=None,
    )


def _com_object() -> ComObject:
    return ComObject(
        identifier="A_MD-1_O-1",
        name="Object {{ChNo}}",
        text="Text {{ChNo}}",
        number=1,
        function_text="Function {{ChNo}}",
        object_size="1 Bit",
        read_flag=False,
        write_flag=True,
        communication_flag=True,
        transmit_flag=False,
        update_flag=False,
        read_on_init_flag=False,
        datapoint_types=[],
        base_number_argument_ref=None,
    )


def _application(
    com_object_ref: ComObjectRef | None, com_object: ComObject | None
) -> ApplicationProgram:
    return ApplicationProgram(
        com_objects={"A_MD-1_O-1": com_object} if com_object else {},
        com_object_refs={"A_MD-1_O-1_R-1": com_object_ref} if com_object_ref else {},
        allocators={},
        module_def_arguments={},
        numeric_args={},
        channels={},
    )


@pytest.mark.parametrize(
    ("com_object_ref_id", "com_object_ref", "com_object"),
    [
        pytest.param(None, None, None, id="no_com_object_ref_id"),
        pytest.param("A_MD-1_O-1_R-1", None, None, id="unknown_com_object_ref"),
        pytest.param(
            "A_MD-1_O-1_R-1",
            _com_object_ref(None, None, None),
            None,
            id="unknown_com_object",
        ),
    ],
)
def test_instance_texts_replace_module_arguments_unresolved(
    com_object_ref_id: str | None,
    com_object_ref: ComObjectRef | None,
    com_object: ComObject | None,
) -> None:
    """Texts of the project get module arguments when the program does not resolve."""
    instance = _instance(
        com_object_ref_id=com_object_ref_id,
        name="Name {{ChNo}}",
        text="Text {{ChNo}}",
        function_text="Function {{ChNo}} {{Other}}",
    )

    instance.merge_application_program_info(
        _application(com_object_ref, com_object), {}, {"ChNo": "A"}
    )

    assert instance.name == "Name A"
    assert instance.text == "Text A"
    assert instance.function_text == "Function A {{Other}}"


def test_instance_texts_of_the_program_replace_module_arguments() -> None:
    """Texts taken from a ComObjectRef and the ComObject get module arguments."""
    instance = _instance()
    com_object_ref = _com_object_ref(None, None, "Reference {{ChNo}}")

    instance.merge_application_program_info(
        _application(com_object_ref, _com_object()), {}, {"ChNo": "B"}
    )

    assert instance.name == "Object B"
    assert instance.text == "Text B"
    assert instance.function_text == "Reference B"
    # the program stays unchanged for other instances
    assert com_object_ref.function_text == "Reference {{ChNo}}"
