"""Refresh stubs for testing."""
import json

from xknxproject import XKNXProj

# run from project directory
# python3 -m script.refresh_stubs

file_names = [
    ("module-definition-test", "test", "de-DE"),
    ("xknx_test_project", "test", None),
    ("test_project-ets4", "test", "de-DE"),
    ("testprojekt-ets6-functions", None, "de-DE"),
    ("ets6_free", None, "de-DE"),
    ("ets6_two_level", None, "de-DE"),
]

for file_name, password, language in file_names:
    print(f"Parsing {file_name}.knxproj")
    knxproj = XKNXProj(
        path=f"test/resources/{file_name}.knxproj",
        password=password,
        language=language,
    )
    project = knxproj.parse()

    with open(f"test/resources/stubs/{file_name}.json", "w", encoding="utf8") as f:
        json.dump(project, f, indent=2, ensure_ascii=False)
