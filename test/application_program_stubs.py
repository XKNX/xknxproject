"""Stub format of application program definitions."""

# Complete definitions are large. A stub therefore keeps them for selected
# programs only and a digest (identity, counts and a checksum of the complete,
# canonically serialized definition) for every program of a project.

from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import json
from typing import Any

from xknxproject.models import ApplicationProgramDefinition

# complete snapshots are kept for these programs only (by project file stem)
SELECTED_APPLICATION_PROGRAMS: Mapping[str, tuple[str, ...]] = {
    "module-definition-test": ("M-0083_A-013A-32-DCC1",),
    "smart_linking": ("M-0083_A-00ED-10-33FD",),
}


def _without_version(definition: ApplicationProgramDefinition) -> dict[str, Any]:
    """Return a definition without the version of the library creating it."""
    return {
        key: value for key, value in definition.items() if key != "xknxproject_version"
    }


def program_digest(definition: ApplicationProgramDefinition) -> dict[str, Any]:
    """Summarize a definition: identity, counts and a checksum of all content."""
    content = _without_version(definition)
    serialized = json.dumps(
        content, sort_keys=True, ensure_ascii=False, separators=(",", ":")
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
    programs: Mapping[str, ApplicationProgramDefinition], selected: Iterable[str]
) -> dict[str, Any]:
    """Build the stub of a project: complete selected programs, digests of all."""
    return {
        "programs": {
            application_id: _without_version(programs[application_id])
            for application_id in selected
        },
        "digests": {
            application_id: program_digest(definition)
            for application_id, definition in programs.items()
        },
    }
