import pytest
from xknxproject import XKNXProj
from . import RESOURCES_PATH

def test_parameterization_output():
    """Test that the parsed KNX project contains parameterization info (should fail until implemented)."""
    knxproj = XKNXProj(RESOURCES_PATH / "ets6_two_level.knxproj")
    project = knxproj.parse()
    # The following fields should be present after extension
    assert "parameterization" in project, "Missing 'parameterization' in KNXProject output"
    paramz = project["parameterization"]
    assert "parameter_types" in paramz, "Missing 'parameter_types' in parameterization output"
    assert "parameter_blocks" in paramz, "Missing 'parameter_blocks' in parameterization output"
    assert "channels" in paramz, "Missing 'channels' in parameterization output"
    # Optionally check for block_trees or other fields as needed
    # assert "block_trees" in paramz, "Missing 'block_trees' in parameterization output" 