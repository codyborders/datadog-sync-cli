# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""AWS Integration resource for Datadog sync CLI.

This module implements sync support for AWS Integration accounts in Datadog.
The AWS Integration API uses a composite key of (account_id, role_name) or
(account_id, access_key_id) to uniquely identify an integration.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List, Dict, Tuple, cast

from datadog_sync.utils.base_resource import BaseResource, ResourceConfig

if TYPE_CHECKING:
    from datadog_sync.utils.custom_client import CustomClient


class AWSIntegration(BaseResource):
    """AWS Integration resource handler.

    Manages syncing of AWS integration accounts between Datadog organizations.
    Each AWS integration is uniquely identified by a composite key of
    account_id and either role_name (for IAM role delegation) or
    access_key_id (for GovCloud/China regions).
    """

    resource_type = "aws_integration"
    resource_config = ResourceConfig(
        base_path="/api/v1/integration/aws",
        excluded_attributes=[
            "external_id",  # Generated per-org, should not be synced
            "errors",  # Runtime state
        ],
    )
    # Additional AWSIntegration specific attributes
    destination_integrations: Dict[str, Dict] = {}

    def _get_resource_id(self, resource: Dict) -> str:
        """Generate a unique identifier for an AWS integration.

        The AWS Integration API uses a composite key. For role-based auth,
        this is (account_id, role_name). For access key auth, this is
        (account_id, access_key_id).

        Args:
            resource: The AWS integration resource dict.

        Returns:
            A unique string identifier for the resource.
        """
        account_id = resource.get("account_id", "")
        role_name = resource.get("role_name", "")
        access_key_id = resource.get("access_key_id", "")

        if access_key_id:
            return f"{account_id}:{access_key_id}"
        return f"{account_id}:{role_name}"

    async def get_resources(self, client: CustomClient) -> List[Dict]:
        """Retrieve all AWS integrations from the Datadog API.

        Args:
            client: The CustomClient instance to use for API calls.

        Returns:
            A list of AWS integration dictionaries.
        """
        resp = await client.get(self.resource_config.base_path)
        return resp.get("accounts", [])

    async def import_resource(self, _id: Optional[str] = None, resource: Optional[Dict] = None) -> Tuple[str, Dict]:
        """Import an AWS integration resource.

        Args:
            _id: Optional resource ID to fetch directly.
            resource: Optional pre-fetched resource dict.

        Returns:
            A tuple of (resource_id, resource_dict).
        """
        if _id:
            # The AWS API doesn't support fetching a single integration by ID.
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
        """Retrieve all AWS integrations from the destination org.

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
        """Create a new AWS integration at the destination.

        If the integration already exists at destination (matched by account_id
        and role_name/access_key_id), update it instead.

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

        resp = await destination_client.post(self.resource_config.base_path, resource)

        # The API returns the external_id in the response
        # We merge it with the original resource data
        created_resource = resource.copy()
        if "external_id" in resp:
            created_resource["external_id"] = resp["external_id"]

        return _id, created_resource

    async def update_resource(self, _id: str, resource: Dict) -> Tuple[str, Dict]:
        """Update an existing AWS integration at the destination.

        The AWS API requires account_id and role_name/access_key_id as query
        params to identify which integration to update.

        Args:
            _id: The source resource ID.
            resource: The resource dict with updated values.

        Returns:
            A tuple of (resource_id, updated_resource_dict).
        """
        destination_client = self.config.destination_client
        dest_resource = self.config.state.destination[self.resource_type].get(_id, {})

        # Build query params to identify the integration
        params = {"account_id": dest_resource.get("account_id", resource.get("account_id"))}

        if dest_resource.get("role_name") or resource.get("role_name"):
            params["role_name"] = dest_resource.get("role_name", resource.get("role_name"))
        elif dest_resource.get("access_key_id") or resource.get("access_key_id"):
            params["access_key_id"] = dest_resource.get("access_key_id", resource.get("access_key_id"))

        resp = await destination_client.put(self.resource_config.base_path, resource, params=params)

        # Merge response with resource data
        updated_resource = resource.copy()
        if isinstance(resp, dict):
            updated_resource.update(resp)

        return _id, updated_resource

    async def delete_resource(self, _id: str) -> None:
        """Delete an AWS integration from the destination.

        Args:
            _id: The resource ID to delete.
        """
        destination_client = self.config.destination_client
        dest_resource = self.config.state.destination[self.resource_type].get(_id, {})

        # Build the body to identify which integration to delete
        body = {"account_id": dest_resource.get("account_id")}

        if dest_resource.get("role_name"):
            body["role_name"] = dest_resource.get("role_name")
        elif dest_resource.get("access_key_id"):
            body["access_key_id"] = dest_resource.get("access_key_id")

        await destination_client.delete(self.resource_config.base_path, body=body)
