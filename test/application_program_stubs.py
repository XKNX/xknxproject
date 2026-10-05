"""
Build the stub format of application program definitions.

Complete definitions are large. A stub therefore keeps the `info` block
without `xknxproject_version`, complete definitions for selected programs
only, and a digest (identity, counts and a checksum of the complete,
canonically serialized definition) for every program of a project. Used by
the tests and by `script/refresh_stubs.py`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import json
from typing import Any

from xknxproject.models import ApplicationProgramDefinition, ApplicationPrograms

# complete snapshots are kept for these programs only (by project file stem);
# each has channels, a module and channel independent objects
SELECTED_APPLICATION_PROGRAMS: Mapping[str, tuple[str, ...]] = {
    "module-definition-test": ("M-0083_A-013A-32-DCC1",),
    "smart_linking": ("M-0083_A-00ED-10-33FD",),
}


def program_digest(definition: ApplicationProgramDefinition) -> dict[str, Any]:
    """
    Summarize a definition: identity, counts and a checksum of all content.

    The checksum is the SHA-256 of the definition serialized as JSON with
    sorted keys, so it depends on the content only, not on the key order. A
    definition carries no library version, so the checksum is stable across
    releases unless the output changes.
    """
    serialized = json.dumps(
        definition, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return {
        "identity": definition["identity"],
        "channels": len(definition["channels"]),
        "modules": len(definition["modules"]),
        "objects": len(definition["objects"]),
        "channel_independent_objects": len(
            definition["channel_independent_object_ids"]
        ),
        "sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
    }


def application_program_stub(
    result: ApplicationPrograms, selected: Iterable[str]
) -> dict[str, Any]:
    """Build the stub of a project: info, complete selected programs, digests of all."""
    programs = result["application_programs"]
    return {
        # the library version changes with every release
        "info": {
            key: value
            for key, value in result["info"].items()
            if key != "xknxproject_version"
        },
        "programs": {
            application_id: programs[application_id] for application_id in selected
        },
        "digests": {
            application_id: program_digest(definition)
            for application_id, definition in programs.items()
        },
    }
