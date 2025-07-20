"""
API mapper module for BMad framework.

This module maps BMad agent commands to FastAPI endpoints.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .agent_loader import AgentDefinition
from .exceptions import APIMappingError, ValidationError

logger = logging.getLogger("clerk_api")


class HTTPMethod(str, Enum):
    """Supported HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class APIMapping:
    """
    Represents a mapping from BMad command to API endpoint.
    """

    command: str
    method: HTTPMethod
    endpoint: str
    path_params: List[str] = field(default_factory=list)
    query_params: List[str] = field(default_factory=list)
    body_params: List[str] = field(default_factory=list)
    websocket_enabled: bool = False
    description: str = ""

    @property
    def full_path(self) -> str:
        """Get the full API path with parameter placeholders."""
        path = self.endpoint
        for param in self.path_params:
            if f"{{{param}}}" not in path:
                path += f"/{{{param}}}"
        return path

    def format_endpoint(self, **kwargs) -> str:
        """
        Format the endpoint with actual parameter values.

        Args:
            **kwargs: Parameter values.

        Returns:
            Formatted endpoint path.
        """
        path = self.endpoint
        for param in self.path_params:
            if param in kwargs:
                path = path.replace(f"{{{param}}}", str(kwargs[param]))
        return path


class APIMapper:
    """
    Maps BMad commands to FastAPI endpoints.
    """

    # Default command to endpoint mappings
    DEFAULT_MAPPINGS = {
        # Analysis commands
        "analyze": APIMapping(
            command="analyze",
            method=HTTPMethod.POST,
            endpoint="/api/agents/{agent_id}/analyze",
            path_params=["agent_id"],
            body_params=["case_name", "data"],
            websocket_enabled=True,
            description="Analyze data using agent",
        ),
        # Search commands
        "search": APIMapping(
            command="search",
            method=HTTPMethod.POST,
            endpoint="/api/agents/{agent_id}/search",
            path_params=["agent_id"],
            body_params=["case_name", "query"],
            query_params=["limit", "offset"],
            description="Search using agent",
        ),
        # Generation commands
        "generate": APIMapping(
            command="generate",
            method=HTTPMethod.POST,
            endpoint="/api/agents/{agent_id}/generate",
            path_params=["agent_id"],
            body_params=["case_name", "template", "variables"],
            websocket_enabled=True,
            description="Generate document using agent",
        ),
        # CRUD operations
        "create": APIMapping(
            command="create",
            method=HTTPMethod.POST,
            endpoint="/api/agents/{agent_id}/resources",
            path_params=["agent_id"],
            body_params=["case_name", "resource_type", "data"],
            description="Create new resource",
        ),
        "list": APIMapping(
            command="list",
            method=HTTPMethod.GET,
            endpoint="/api/agents/{agent_id}/resources",
            path_params=["agent_id"],
            query_params=["case_name", "resource_type", "limit", "offset"],
            description="List resources",
        ),
        "get": APIMapping(
            command="get",
            method=HTTPMethod.GET,
            endpoint="/api/agents/{agent_id}/resources/{resource_id}",
            path_params=["agent_id", "resource_id"],
            query_params=["case_name"],
            description="Get specific resource",
        ),
        "update": APIMapping(
            command="update",
            method=HTTPMethod.PUT,
            endpoint="/api/agents/{agent_id}/resources/{resource_id}",
            path_params=["agent_id", "resource_id"],
            body_params=["case_name", "data"],
            description="Update resource",
        ),
        "delete": APIMapping(
            command="delete",
            method=HTTPMethod.DELETE,
            endpoint="/api/agents/{agent_id}/resources/{resource_id}",
            path_params=["agent_id", "resource_id"],
            query_params=["case_name"],
            description="Delete resource",
        ),
        # Report generation
        "report": APIMapping(
            command="report",
            method=HTTPMethod.POST,
            endpoint="/api/agents/{agent_id}/report",
            path_params=["agent_id"],
            body_params=["case_name", "report_type", "parameters"],
            websocket_enabled=True,
            description="Generate report",
        ),
        # Help/info commands
        "help": APIMapping(
            command="help",
            method=HTTPMethod.GET,
            endpoint="/api/agents/{agent_id}/commands",
            path_params=["agent_id"],
            description="Get available commands",
        ),
        "status": APIMapping(
            command="status",
            method=HTTPMethod.GET,
            endpoint="/api/agents/{agent_id}/status",
            path_params=["agent_id"],
            query_params=["case_name"],
            description="Get agent status",
        ),
    }

    def __init__(self, custom_mappings: Optional[Dict[str, APIMapping]] = None):
        """
        Initialize API mapper.

        Args:
            custom_mappings: Custom command to API mappings.
        """
        self.mappings = self.DEFAULT_MAPPINGS.copy()
        if custom_mappings:
            self.mappings.update(custom_mappings)

        # Registry for agent-specific mappings
        self._agent_mappings: Dict[str, Dict[str, APIMapping]] = {}

        # Numbered options support
        self._numbered_options: Dict[str, List[str]] = {}

    def get_mapping(self, command: str, agent_id: Optional[str] = None) -> APIMapping:
        """
        Get API mapping for a command.

        Args:
            command: Command name (without * prefix).
            agent_id: Optional agent ID for agent-specific mappings.

        Returns:
            API mapping for the command.

        Raises:
            APIMappingError: If no mapping found.
        """
        command = command.lstrip("*")

        # Check agent-specific mappings first
        if agent_id and agent_id in self._agent_mappings:
            if command in self._agent_mappings[agent_id]:
                return self._agent_mappings[agent_id][command]

        # Check default mappings
        if command in self.mappings:
            return self.mappings[command]

        # Try to find by prefix
        for cmd, mapping in self.mappings.items():
            if command.startswith(cmd):
                # Create a copy with the actual command
                return APIMapping(
                    command=command,
                    method=mapping.method,
                    endpoint=mapping.endpoint,
                    path_params=mapping.path_params,
                    query_params=mapping.query_params,
                    body_params=mapping.body_params,
                    websocket_enabled=mapping.websocket_enabled,
                    description=f"{mapping.description} ({command})",
                )

        raise APIMappingError(
            command,
            "No API mapping found",
            {"available_commands": list(self.mappings.keys())},
        )

    def register_agent_mappings(
        self, agent_def: AgentDefinition, base_path: str = "/api/agents"
    ) -> None:
        """
        Register API mappings for an agent's commands.

        Args:
            agent_def: Agent definition with commands.
            base_path: Base API path for agent endpoints.
        """
        agent_mappings = {}

        for cmd in agent_def.command_names:
            # Skip if already has explicit mapping
            if cmd in self.mappings:
                continue

            # Create agent-specific mapping
            mapping = self._create_agent_mapping(agent_def.id, cmd, base_path)
            agent_mappings[cmd] = mapping

        self._agent_mappings[agent_def.id] = agent_mappings
        logger.info(
            f"Registered {len(agent_mappings)} API mappings for agent {agent_def.id}"
        )

    def _create_agent_mapping(
        self, agent_id: str, command: str, base_path: str
    ) -> APIMapping:
        """
        Create API mapping for agent-specific command.

        Uses heuristics to determine HTTP method and parameters.
        """
        # Determine HTTP method based on command name
        method = self._infer_http_method(command)

        # Build endpoint path
        endpoint = f"{base_path}/{agent_id}/{command}"

        # Determine parameters based on method
        if method == HTTPMethod.GET:
            return APIMapping(
                command=command,
                method=method,
                endpoint=endpoint,
                path_params=["agent_id"],
                query_params=["case_name"],
                description=f"Execute {command} command",
            )
        else:
            # POST/PUT/DELETE typically need body params
            websocket = self._should_enable_websocket(command)

            return APIMapping(
                command=command,
                method=method,
                endpoint=endpoint,
                path_params=["agent_id"],
                body_params=["case_name", "parameters"],
                websocket_enabled=websocket,
                description=f"Execute {command} command",
            )

    def _infer_http_method(self, command: str) -> HTTPMethod:
        """Infer HTTP method from command name."""
        command_lower = command.lower()

        # GET operations
        if any(
            command_lower.startswith(prefix)
            for prefix in ["get", "list", "search", "find", "view", "show", "fetch"]
        ):
            return HTTPMethod.GET

        # DELETE operations
        elif any(
            command_lower.startswith(prefix)
            for prefix in ["delete", "remove", "destroy"]
        ):
            return HTTPMethod.DELETE

        # PUT operations
        elif any(
            command_lower.startswith(prefix)
            for prefix in ["update", "edit", "modify", "change"]
        ):
            return HTTPMethod.PUT

        # Default to POST
        else:
            return HTTPMethod.POST

    def _should_enable_websocket(self, command: str) -> bool:
        """Determine if command should use WebSocket."""
        # Long-running operations that benefit from progress updates
        long_ops = [
            "analyze",
            "generate",
            "process",
            "draft",
            "compile",
            "build",
            "scan",
            "extract",
            "train",
            "optimize",
        ]

        return any(command.lower().startswith(op) for op in long_ops)

    def transform_parameters(
        self, mapping: APIMapping, input_params: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """
        Transform input parameters into path, query, and body params.

        Args:
            mapping: API mapping with parameter definitions.
            input_params: Input parameters from command.

        Returns:
            Tuple of (path_params, query_params, body_params).
        """
        path_params = {}
        query_params = {}
        body_params = {}

        for key, value in input_params.items():
            if key in mapping.path_params:
                path_params[key] = value
            elif key in mapping.query_params:
                query_params[key] = value
            elif key in mapping.body_params:
                body_params[key] = value
            else:
                # Unknown params go to body by default
                body_params[key] = value

        # Validate required parameters
        missing_path = [p for p in mapping.path_params if p not in path_params]
        if missing_path:
            raise ValidationError(
                "Parameter",
                f"Missing required path parameters: {', '.join(missing_path)}",
                {"missing": missing_path, "provided": list(path_params.keys())},
            )

        return path_params, query_params, body_params

    def register_numbered_options(self, command: str, options: List[str]) -> None:
        """
        Register numbered options for a command (BMad pattern).

        Args:
            command: Command that uses numbered options.
            options: List of option descriptions.
        """
        self._numbered_options[command] = options
        logger.debug(
            f"Registered {len(options)} numbered options for command {command}"
        )

    def get_numbered_options(self, command: str) -> Optional[List[str]]:
        """Get numbered options for a command."""
        return self._numbered_options.get(command)

    def format_websocket_channel(
        self, agent_id: str, command: str, case_id: str
    ) -> str:
        """
        Format WebSocket channel name for a command.

        Args:
            agent_id: Agent executing the command.
            command: Command being executed.
            case_id: Case ID for isolation.

        Returns:
            WebSocket channel name.
        """
        # Standard format: agent:{agent_id}:{command}:{case_id}
        return f"agent:{agent_id}:{command}:{case_id}"

    def get_all_endpoints(self, agent_id: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Get all available endpoints.

        Args:
            agent_id: Optional agent ID to include agent-specific endpoints.

        Returns:
            List of endpoint information.
        """
        endpoints = []

        # Add default mappings
        for cmd, mapping in self.mappings.items():
            endpoints.append(
                {
                    "command": cmd,
                    "method": mapping.method,
                    "endpoint": mapping.full_path,
                    "description": mapping.description,
                    "websocket": "Yes" if mapping.websocket_enabled else "No",
                }
            )

        # Add agent-specific mappings
        if agent_id and agent_id in self._agent_mappings:
            for cmd, mapping in self._agent_mappings[agent_id].items():
                endpoints.append(
                    {
                        "command": cmd,
                        "method": mapping.method,
                        "endpoint": mapping.full_path,
                        "description": mapping.description,
                        "websocket": "Yes" if mapping.websocket_enabled else "No",
                    }
                )

        return sorted(endpoints, key=lambda x: x["command"])
