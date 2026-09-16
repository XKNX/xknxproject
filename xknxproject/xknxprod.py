"""
Parse standalone KNX product files (``.knxprod``).

Companion to :class:`xknxproject.xknxproj.XKNXProj` (installation projects). This
parses a manufacturer product database and returns, per application program, the
full static definition: communication objects, parameters and the memory/segment
layout.

Like :class:`~xknxproject.xknxproj.XKNXProj`, the public result is a
:class:`~xknxproject.models.knxproject.KNXProduct` ``TypedDict``; the internal
dataclasses produced by the loader are converted here.

Example::

    from xknxproject import XKNXProd

    product = XKNXProd("MyProduct.knxprod").parse()
    for app in product["application_programs"].values():
        print(app["name"], app["mask_version"], len(app["communication_objects"]))
"""

from __future__ import annotations

import logging
from pathlib import Path
import time

from xknxproject.__version__ import __version__
from xknxproject.loader import ApplicationProgramLoader
from xknxproject.models import (
    ApplicationProgram,
    ApplicationProgramSegment,
    ComObject,
    ComObjectRef,
    Flags,
    KNXProduct,
    Parameter,
    ParameterRef,
    ProductApplicationProgram,
    ProductComObject,
    ProductParameter,
    ProductSegment,
)
from xknxproject.zip.extractor import extract_prod

_LOGGER = logging.getLogger("xknxproject.log")


class XKNXProd:
    """Class for parsing ETS product (``.knxprod``) files."""

    def __init__(self, path: str | Path) -> None:
        """Initialize a XKNXProd parser."""
        self.path = Path(path)

    def parse(self) -> KNXProduct:
        """Parse the KNX product."""
        _LOGGER.info(
            'Xknxproject version %s parsing product "%s"', __version__, self.path
        )
        _start = time.time()
        with extract_prod(self.path) as contents:
            application_programs = {
                app.identifier: _convert_application_program(app)
                for app in (
                    ApplicationProgramLoader.load_static(app_path)
                    for app_path in contents.application_program_paths()
                )
            }
            product = KNXProduct(
                manufacturer=contents.manufacturer_id,
                schema_version=contents.schema_version,
                application_programs=application_programs,
            )
        _LOGGER.info(
            "Parsing product took %s seconds - %s application program(s)",
            time.time() - _start,
            len(product["application_programs"]),
        )
        return product


def _convert_flags(obj: ComObject | ComObjectRef, base: ComObject) -> Flags:
    """Resolve flags of a ComObjectRef onto its base ComObject (ref wins)."""

    def _resolve(name: str) -> bool:
        value = getattr(obj, name)
        if value is None:
            value = getattr(base, name)
        return bool(value)

    return Flags(
        read=_resolve("read_flag"),
        write=_resolve("write_flag"),
        communication=_resolve("communication_flag"),
        transmit=_resolve("transmit_flag"),
        update=_resolve("update_flag"),
        read_on_init=_resolve("read_on_init_flag"),
    )


def _convert_com_object(ref: ComObjectRef, base: ComObject) -> ProductComObject:
    """Convert a ComObjectRef merged onto its base ComObject."""
    return ProductComObject(
        identifier=ref.identifier,
        number=base.number,
        name=ref.name or base.name,
        text=ref.text or base.text,
        function_text=ref.function_text or base.function_text,
        object_size=ref.object_size or base.object_size,
        dpts=ref.datapoint_types or base.datapoint_types,
        flags=_convert_flags(ref, base),
    )


def _convert_parameter(
    param: Parameter, app: ApplicationProgram, refs: list[ParameterRef]
) -> ProductParameter:
    """
    Convert a Parameter, resolving its type, memory location and defaults.

    ETS uses the ParameterRef's Value/Text as the effective defaults; the
    overrides are applied when the parameter has exactly one ref (multiple
    refs mean multiple contexts with no single effective value).
    """
    ptype = app.parameter_types.get(param.parameter_type_ref)
    memory = param.memory
    ref = refs[0] if len(refs) == 1 else None
    value = ref.value if ref is not None and ref.value is not None else param.value
    text = ref.text if ref is not None and ref.text is not None else param.text
    return ProductParameter(
        identifier=param.identifier,
        name=param.name,
        text=text,
        value=value,
        segment=memory.segment_ref if memory else None,
        offset=memory.offset if memory else None,
        bit_offset=memory.bit_offset if memory else None,
        size_in_bit=ptype.size_in_bit if ptype else None,
        type=ptype.kind if ptype else "",
        base=ptype.base if ptype else None,
        minimum=ptype.minimum if ptype else None,
        maximum=ptype.maximum if ptype else None,
        enumerations=ptype.enumerations if ptype else {},
    )


def _convert_segment(segment: ApplicationProgramSegment) -> ProductSegment:
    """Convert an application program segment."""
    return ProductSegment(
        identifier=segment.identifier,
        kind=segment.kind,
        size=segment.size,
        object_index=segment.load_state_machine,
        offset=segment.offset,
        address=segment.address,
        memory_type=segment.memory_type,
    )


def _convert_application_program(app: ApplicationProgram) -> ProductApplicationProgram:
    """Convert an internal ApplicationProgram to the public product output."""
    communication_objects = [
        _convert_com_object(ref, app.com_objects[ref.ref_id])
        for ref in app.com_object_refs.values()
        if ref.ref_id in app.com_objects
    ]
    refs_by_parameter: dict[str, list[ParameterRef]] = {}
    for parameter_ref in app.parameter_refs.values():
        refs_by_parameter.setdefault(parameter_ref.ref_id, []).append(parameter_ref)
    return ProductApplicationProgram(
        identifier=app.identifier,
        name=app.name,
        application_number=app.application_number,
        application_version=app.application_version,
        mask_version=app.mask_version,
        pei_type=app.pei_type,
        communication_objects=communication_objects,
        parameters=[
            _convert_parameter(p, app, refs_by_parameter.get(p.identifier, []))
            for p in app.parameters.values()
        ],
        segments=[_convert_segment(s) for s in app.segments.values()],
    )
