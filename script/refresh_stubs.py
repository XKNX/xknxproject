import json
from pathlib import Path
import logging

from xknxproject import XKNXProj

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

file_names = [
    ("module-definition-test", "test", "de-DE"),
    ("xknx_test_project", "test", None),
    ("test_project-ets4", "test", "de-DE"),
    ("testprojekt-ets6-functions", None, "de-DE"),
    ("ets6_free", None, "de-DE"),
    ("ets6_two_level", None, "de-DE"),
]

base_dir = Path("test/resources")
stub_dir = base_dir / "stubs"
stub_dir.mkdir(exist_ok=True)

for file_name, password, language in file_names:
    try:
        knxproj_path = base_dir / f"{file_name}.knxproj"
        logging.info(f"Parsing {knxproj_path}")
        knxproj = XKNXProj(
            path=str(knxproj_path),
            password=password,
            language=language,
        )
        project = knxproj.parse()

        stub_path = stub_dir / f"{file_name}.json"
        with stub_path.open(mode="w", encoding="utf8") as f:
            json.dump(project, f, indent=2, ensure_ascii=False)
        logging.info(f"Stub written to {stub_path}")
    except Exception as e:
        logging.error(f"Failed to process {file_name}: {e}")
