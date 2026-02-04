# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""Service Definition resource for syncing Datadog Service Catalog entries."""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List, Dict, Tuple, cast

from datadog_sync.utils.base_resource import BaseResource, ResourceConfig
from datadog_sync.utils.custom_client import PaginationConfig

if TYPE_CHECKING:
    from datadog_sync.utils.custom_client import CustomClient


def _remaining_func(idx: int, resp: Dict, page_size: int, page_number: int) -> int:
    """Calculate remaining pages for pagination.

    Args:
        idx: Current index in pagination.
        resp: Response from API containing pagination metadata.
        page_size: Number of items per page.
        page_number: Current page number.

    Returns:
        Number of remaining items to fetch, or 0 if done.
    """
    total_count = resp.get("meta", {}).get("page", {}).get("total_count", 0)
    fetched = page_size * (page_number + 1)
    return max(0, total_count - fetched)


class ServiceDefinition(BaseResource):
    """Resource class for Datadog Service Definitions (Service Catalog).

    Service definitions are identified by service_name rather than a numeric ID.
    This class handles import, sync, and deletion of service definitions between
    Datadog organizations.

    Attributes:
        resource_type: The identifier for this resource type.
        resource_config: Configuration for API paths and excluded attributes.
        pagination_config: Pagination configuration for list requests.
        destination_service_definitions: Cache of destination service definitions.
    """

    resource_type = "service_definition"
    resource_config = ResourceConfig(
        base_path="/api/v2/services/definitions",
        excluded_attributes=[
            "meta",
        ],
    )
    # Additional ServiceDefinition specific attributes
    pagination_config = PaginationConfig(
        page_size=100,
        remaining_func=_remaining_func,
    )
    destination_service_definitions: Dict[str, Dict] = {}

    async def get_resources(self, client: CustomClient) -> List[Dict]:
        """Fetch all service definitions from the API.

        Args:
            client: The HTTP client to use for the request.

        Returns:
            List of service definition dictionaries.
        """
        resp = await client.paginated_request(client.get)(
            self.resource_config.base_path,
            pagination_config=self.pagination_config,
        )

        return resp

    async def import_resource(
        self, _id: Optional[str] = None, resource: Optional[Dict] = None
    ) -> Tuple[str, Dict]:
        """Import a service definition from the source organization.

        Args:
            _id: The service name to import. If provided, fetches from source API.
            resource: Optional pre-fetched resource data.

        Returns:
            Tuple of (service_name, resource_dict).
        """
        if _id:
            source_client = self.config.source_client
            resource = (
                await source_client.get(self.resource_config.base_path + f"/{_id}")
            )["data"]

        resource = cast(dict, resource)

        # The service name is the unique identifier
        service_name = self._get_service_name(resource)
        return service_name, resource

    async def pre_resource_action_hook(self, _id: str, resource: Dict) -> None:
        """Hook called before each resource action.

        Args:
            _id: The resource identifier (service_name).
            resource: The resource data.
        """
        pass

    async def pre_apply_hook(self) -> None:
        """Hook called before applying changes to destination.

        Caches the destination service definitions for efficient lookup
        during create operations.
        """
        self.destination_service_definitions = (
            await self._get_destination_service_definitions()
        )

    async def create_resource(self, _id: str, resource: Dict) -> Tuple[str, Dict]:
        """Create or update a service definition in the destination organization.

        If the service definition already exists at the destination (matched by
        service_name), this will update it instead.

        Args:
            _id: The service name.
            resource: The service definition data.

        Returns:
            Tuple of (service_name, created_resource_dict).
        """
        # If the service definition already exists at destination, update it
        if _id in self.destination_service_definitions:
            self.config.state.destination[self.resource_type][_id] = (
                self.destination_service_definitions[_id]
            )
            return await self.update_resource(_id, resource)

        destination_client = self.config.destination_client

        # Extract the schema data for the POST request
        schema_data = self._extract_schema_data(resource)
        resp = await destination_client.post(
            self.resource_config.base_path, schema_data
        )

        return _id, (
            resp["data"][0] if isinstance(resp.get("data"), list) else resp["data"]
        )

    async def update_resource(self, _id: str, resource: Dict) -> Tuple[str, Dict]:
        """Update a service definition in the destination organization.

        The Service Definition API uses POST for both create and update operations.

        Args:
            _id: The service name.
            resource: The service definition data.

        Returns:
            Tuple of (service_name, updated_resource_dict).
        """
        destination_client = self.config.destination_client

        # Extract the schema data for the POST request
        schema_data = self._extract_schema_data(resource)
        resp = await destination_client.post(
            self.resource_config.base_path, schema_data
        )

        return _id, (
            resp["data"][0] if isinstance(resp.get("data"), list) else resp["data"]
        )

    async def delete_resource(self, _id: str) -> None:
        """Delete a service definition from the destination organization.

        Args:
            _id: The service name to delete.
        """
        destination_client = self.config.destination_client
        # Use the service name directly in the delete path
        await destination_client.delete(self.resource_config.base_path + f"/{_id}")

    def _get_service_name(self, resource: Dict) -> str:
        """Extract the service name from a service definition resource.

        The service name can be in different locations depending on the schema version
        and whether it's from a list or get response.

        Args:
            resource: The service definition resource data.

        Returns:
            The service name.
        """
        # Try attributes.schema."dd-service" first (v2/v2.1/v2.2 in API response)
        if "attributes" in resource:
            schema = resource["attributes"].get("schema", {})
            if "dd-service" in schema:
                return schema["dd-service"]
            # v3 uses "name" instead of "dd-service"
            if "name" in schema:
                return schema["name"]

        # Try direct schema access (when resource is just the schema)
        if "dd-service" in resource:
            return resource["dd-service"]
        if "name" in resource:
            return resource["name"]

        # Fallback to id field
        return resource.get("id", "")

    def _extract_schema_data(self, resource: Dict) -> Dict:
        """Extract the schema data from a resource for API submission.

        The POST API expects the raw schema, not the wrapped API response format.

        Args:
            resource: The service definition resource data.

        Returns:
            The schema data suitable for POST request.
        """
        # If resource has attributes.schema, extract just the schema
        if "attributes" in resource and "schema" in resource["attributes"]:
            return resource["attributes"]["schema"]

        # If resource is already a schema, return it as-is
        return resource

    async def _get_destination_service_definitions(self) -> Dict[str, Dict]:
        """Fetch and cache destination service definitions.

        Returns:
            Dictionary mapping service_name to service definition data.
        """
        destination_client = self.config.destination_client
        service_definitions = {}

        resp = await self.get_resources(destination_client)
        for service_def in resp:
            service_name = self._get_service_name(service_def)
            if service_name:
                service_definitions[service_name] = service_def

        return service_definitions
