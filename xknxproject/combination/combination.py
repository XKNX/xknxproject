"""Combine the project data for more details inferred from linked objects."""

from __future__ import annotations

from typing import NamedTuple

from xknxproject.models import CommunicationObject, DPTType, KNXProject


class DPTTuple(NamedTuple):
    """A tuple representation of a DPT."""

    # used to have a hashable object to generate sets and do equality checks
    main: int
    sub: int | None

    def to_dpttype(self) -> DPTType:
        """Return a DPTType representation."""
        return DPTType(main=self.main, sub=self.sub)


def combine_project(project: KNXProject) -> KNXProject:
    """Combine the parsed project data for more details inferred from linked objects."""
    for comm_object in project["communication_objects"].values():
        if not comm_object["dpts"]:
            comm_object["dpts"] = _get_dpt_from_object_size(comm_object["object_size"])

    for group_address in project["group_addresses"].values():
        if not group_address["dpt"]:
            comm_objects = [
                project["communication_objects"][co_id]
                for co_id in group_address["communication_object_ids"]
            ]
            group_address["dpt"] = _get_dpt_from_comm_objects(comm_objects)
    return project


def _get_dpt_from_object_size(object_size: str) -> list[DPTType]:
    """Infer a DPTType from a CommunicationObjects object_size."""
    if object_size == "1 Bit":
        return [DPTType(main=1, sub=None)]
    if object_size == "2 Bit":
        # ignoring DPT 23.x which also has 2 bits
        return [DPTType(main=2, sub=None)]
    if object_size == "4 Bit":
        return [DPTType(main=3, sub=None)]
    return []


def _get_dpt_from_comm_objects(
    comm_objects: list[CommunicationObject],
) -> DPTType | None:
    """Infer a DPTType from a set of CommunicationObject DPTs."""
    dpts: set[DPTTuple] = {
        DPTTuple(**dpt) for co in comm_objects for dpt in co["dpts"] if dpt
    }
    if not dpts:
        return None
    if len(dpts) == 1:
        return next(iter(dpts)).to_dpttype()
    # if they all share the same main type, use a generic DPTType
    mains = {dpt.main for dpt in dpts}
    if len(mains) == 1:
        _main = next(iter(mains))
        return DPTType(main=_main, sub=None)
    return None
