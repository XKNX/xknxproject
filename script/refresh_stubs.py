"""Refresh stubs for testing."""

import json
from pathlib import Path

from test.application_program_stubs import (
    SELECTED_APPLICATION_PROGRAMS,
    application_program_stub,
)
from test.test_application_programs import APPLICATION_PROGRAM_FIXTURES
from test.test_knxproj import PROJECT_FIXTURES
from xknxproject import XKNXProj

# run from project directory
# python3 -m script.refresh_stubs

for file_name, password, language in PROJECT_FIXTURES:
    print(f"Parsing {file_name}.knxproj")
    knxproj = XKNXProj(
        path=f"test/resources/{file_name}.knxproj",
        password=password,
        language=language,
    )
    project = knxproj.parse()

    with Path(f"test/resources/stubs/{file_name}.json").open(
        mode="w", encoding="utf8"
    ) as f:
        json.dump(project, f, indent=2, ensure_ascii=False)

# application program definitions: info, complete definitions of selected
# programs and digests of all (see test/application_program_stubs.py)
Path("test/resources/stubs/application_programs").mkdir(exist_ok=True)
for file_name, password, language in APPLICATION_PROGRAM_FIXTURES:
    print(f"Parsing application programs of {file_name}.knxproj")
    knxproj = XKNXProj(
        path=f"test/resources/{file_name}.knxproj",
        password=password,
        language=language,
    )
    application_programs = knxproj.parse_application_programs()

    with Path(f"test/resources/stubs/application_programs/{file_name}.json").open(
        mode="w", encoding="utf8"
    ) as f:
        json.dump(
            application_program_stub(
                application_programs, SELECTED_APPLICATION_PROGRAMS.get(file_name, ())
            ),
            f,
            indent=2,
            ensure_ascii=False,
        )
