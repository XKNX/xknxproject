"""Refresh stubs for testing."""

import json
from pathlib import Path

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
