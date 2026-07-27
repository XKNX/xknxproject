"""
Host-agnostic MCP tool functions for parsed ETS projects.

These are plain async functions operating on a parsed
:class:`~xknxproject.models.KNXProject`, with frozen, JSON-serialisable
dataclass inputs and outputs. They carry **no dependency on any MCP SDK, Home
Assistant or a web framework** — each consumer (SpectrumKNX, Home Assistant, …)
wraps them into its own MCP transport.

See :mod:`xknxproject.mcp.tools` for the tool functions and
:mod:`xknxproject.mcp.types` for the input/output models.
"""

from .tools import (
    describe_function,
    describe_group_address,
    get_project_info,
    get_topology,
    list_communication_objects,
    list_devices,
    list_functions,
    list_group_addresses,
    list_locations,
)
from .types import (
    AreaSummary,
    CommunicationObjectFilter,
    CommunicationObjectListResult,
    CommunicationObjectSummary,
    DeviceFilter,
    DeviceListResult,
    DeviceSummary,
    FunctionDetail,
    FunctionFilter,
    FunctionListResult,
    FunctionSummary,
    GroupAddressDetail,
    GroupAddressFilter,
    GroupAddressListResult,
    GroupAddressRefSummary,
    GroupAddressSummary,
    LineSummary,
    LocationsResult,
    ProjectInfoResult,
    SpaceSummary,
    TopologyResult,
)

__all__ = [
    "AreaSummary",
    "CommunicationObjectFilter",
    "CommunicationObjectListResult",
    "CommunicationObjectSummary",
    "DeviceFilter",
    "DeviceListResult",
    "DeviceSummary",
    "FunctionDetail",
    "FunctionFilter",
    "FunctionListResult",
    "FunctionSummary",
    "GroupAddressDetail",
    # inputs
    "GroupAddressFilter",
    "GroupAddressListResult",
    "GroupAddressRefSummary",
    "GroupAddressSummary",
    "LineSummary",
    "LocationsResult",
    # outputs
    "ProjectInfoResult",
    "SpaceSummary",
    "TopologyResult",
    "describe_function",
    "describe_group_address",
    # tools
    "get_project_info",
    "get_topology",
    "list_communication_objects",
    "list_devices",
    "list_functions",
    "list_group_addresses",
    "list_locations",
]
