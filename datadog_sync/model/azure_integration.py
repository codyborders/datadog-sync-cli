# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""Azure Integration resource for Datadog sync CLI.

This module implements sync support for Azure Integration accounts in Datadog.
The Azure Integration API uses a composite key of (tenant_name, client_id) to
uniquely identify an integration.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List, Dict, Tuple, cast

from datadog_sync.utils.base_resource import BaseResource, ResourceConfig

if TYPE_CHECKING:
    from datadog_sync.utils.custom_client import CustomClient


class AzureIntegration(BaseResource):
    """Azure Integration resource handler.

    Manages syncing of Azure integration accounts between Datadog organizations.
    Each Azure integration is uniquely identified by a composite key of
    tenant_name and client_id.
    """

    resource_type = "azure_integration"
    resource_config = ResourceConfig(
        base_path="/api/v1/integration/azure",
        excluded_attributes=[
            "client_secret",  # Write-only, never returned by API
            "errors",  # Runtime state
        ],
    )
    # Additional AzureIntegration specific attributes
    destination_integrations: Dict[str, Dict] = {}

    def _get_resource_id(self, resource: Dict) -> str:
        """Generate a unique identifier for an Azure integration.

        The Azure Integration API uses a composite key of (tenant_name, client_id).

        Args:
            resource: The Azure integration resource dict.

        Returns:
            A unique string identifier for the resource.
        """
        tenant_name = resource.get("tenant_name", "")
        client_id = resource.get("client_id", "")
        return f"{tenant_name}:{client_id}"

    async def get_resources(self, client: CustomClient) -> List[Dict]:
        """Retrieve all Azure integrations from the Datadog API.

        Args:
            client: The CustomClient instance to use for API calls.

        Returns:
            A list of Azure integration dictionaries.
        """
        resp = await client.get(self.resource_config.base_path)
        # The API returns a list directly, not wrapped in a key
        if isinstance(resp, list):
            return resp
        return []

    async def import_resource(self, _id: Optional[str] = None, resource: Optional[Dict] = None) -> Tuple[str, Dict]:
        """Import an Azure integration resource.

        Args:
            _id: Optional resource ID to fetch directly.
            resource: Optional pre-fetched resource dict.

        Returns:
            A tuple of (resource_id, resource_dict).
        """
        if _id:
            # The Azure API doesn't support fetching a single integration by ID.
            # Re-fetch all and find the matching one.
            source_client = self.config.source_client
            all_resources = await self.get_resources(source_client)
            for r in all_resources:
                if self._get_resource_id(r) == _id:
                    resource = r
                    break

        resource = cast(dict, resource)
        resource_id = self._get_resource_id(resource)
        return resource_id, resource

    async def pre_resource_action_hook(self, _id: str, resource: Dict) -> None:
        """Hook called before each resource action.

        Args:
            _id: The resource ID.
            resource: The resource dict.
        """
        pass

    async def pre_apply_hook(self) -> None:
        """Hook called before applying changes.

        Caches destination integrations for efficient lookup during sync.
        """
        self.destination_integrations = await self._get_destination_integrations()

    async def _get_destination_integrations(self) -> Dict[str, Dict]:
        """Retrieve all Azure integrations from the destination org.

        Returns:
            A dict mapping resource IDs to their integration dicts.
        """
        destination_client = self.config.destination_client
        integrations = {}

        resources = await self.get_resources(destination_client)
        for r in resources:
            resource_id = self._get_resource_id(r)
            integrations[resource_id] = r

        return integrations

    async def create_resource(self, _id: str, resource: Dict) -> Tuple[str, Dict]:
        """Create a new Azure integration at the destination.

        If the integration already exists at destination (matched by tenant_name
        and client_id), update it instead.

        Args:
            _id: The source resource ID.
            resource: The resource dict to create.

        Returns:
            A tuple of (resource_id, created_resource_dict).
        """
        destination_client = self.config.destination_client
        resource_id = self._get_resource_id(resource)

        # Check if integration already exists at destination
        if resource_id in self.destination_integrations:
            self.config.state.destination[self.resource_type][_id] = self.destination_integrations[resource_id]
            return await self.update_resource(_id, resource)

        await destination_client.post(self.resource_config.base_path, resource)

        return _id, resource

    async def update_resource(self, _id: str, resource: Dict) -> Tuple[str, Dict]:
        """Update an existing Azure integration at the destination.

        The Azure API uses PUT to replace the entire configuration.

        Args:
            _id: The source resource ID.
            resource: The resource dict with updated values.

        Returns:
            A tuple of (resource_id, updated_resource_dict).
        """
        destination_client = self.config.destination_client

        await destination_client.put(self.resource_config.base_path, resource)

        return _id, resource

    async def delete_resource(self, _id: str) -> None:
        """Delete an Azure integration from the destination.

        The Azure API requires the request body to contain tenant_name and
        client_id to identify which integration to delete.

        Args:
            _id: The resource ID to delete.
        """
        destination_client = self.config.destination_client
        dest_resource = self.config.state.destination[self.resource_type].get(_id, {})

        # Build the body to identify which integration to delete
        body = {
            "tenant_name": dest_resource.get("tenant_name"),
            "client_id": dest_resource.get("client_id"),
        }

        await destination_client.delete(self.resource_config.base_path, body=body)
