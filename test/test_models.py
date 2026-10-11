"""Test internal model behavior."""

from __future__ import annotations

from xknxproject.models import ApplicationProgram, ComObjectInstanceRef


def test_missing_module_instance_is_non_fatal() -> None:
    """Keep communication objects when their module instance is missing."""
    com_object = ComObjectInstanceRef(
        identifier="O-1",
        ref_id="MD-2_M-22_MI-1_O-2-31_R-3",
        text="Broken module reference",
        function_text=None,
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
        base_number_argument_ref="ObjNumberBase",
        number=12,
    )
    application = ApplicationProgram({}, {}, {}, {}, {}, {})

    com_object.apply_module_base_number_argument([], application)

    assert com_object.number == 12
    assert com_object.module is None
