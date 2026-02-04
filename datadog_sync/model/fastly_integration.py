# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""Fastly Integration resource for syncing Fastly accounts between Datadog organizations."""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List, Dict, Tuple, cast

from datadog_sync.utils.base_resource import BaseResource, ResourceConfig

if TYPE_CHECKING:
    from datadog_sync.utils.custom_client import CustomClient


class FastlyIntegration(BaseResource):
    """Resource class for managing Fastly Integration accounts.

    This resource handles syncing Fastly integration accounts between
    source and destination Datadog organizations.
    """

    resource_type = "fastly_integration"
    resource_config = ResourceConfig(
        base_path="/api/v2/integrations/fastly/accounts",
        excluded_attributes=[
            "id",
        ],
    )
    # Additional FastlyIntegration specific attributes
    destination_accounts: Dict[str, Dict] = {}

    async def get_resources(self, client: CustomClient) -> List[Dict]:
        """Fetch all Fastly integration accounts from the client.

        Args:
            client: The CustomClient instance to use for API requests.

        Returns:
            A list of Fastly account dictionaries.
        """
        resp = await client.get(self.resource_config.base_path)

        return resp.get("data", [])

    async def import_resource(self, _id: Optional[str] = None, resource: Optional[Dict] = None) -> Tuple[str, Dict]:
        """Import a Fastly integration account resource.

        Args:
            _id: Optional ID of the resource to import.
            resource: Optional resource dictionary if already fetched.

        Returns:
            A tuple of (resource_id, resource_dict).
        """
        if _id:
            source_client = self.config.source_client
            resource = (await source_client.get(self.resource_config.base_path + f"/{_id}"))["data"]

        resource = cast(dict, resource)
        return resource["id"], resource

    async def pre_resource_action_hook(self, _id: str, resource: Dict) -> None:
        """Hook called before any resource action (create/update).

        Args:
            _id: The resource ID.
            resource: The resource dictionary.
        """
        pass

    async def pre_apply_hook(self) -> None:
        """Hook called before applying changes to destination.

        Fetches existing Fastly accounts from the destination to enable
        matching by account name during create operations.
        """
        client = self.config.destination_client
        resp = await self.get_resources(client)
        self.destination_accounts = {}
        for r in resp:
            # Use the account name as the key for matching
            self.destination_accounts[r["attributes"]["name"]] = r

    async def create_resource(self, _id: str, resource: Dict) -> Tuple[str, Dict]:
        """Create a Fastly integration account at the destination.

        If an account with the same name already exists at the destination,
        updates that account instead of creating a new one.

        Args:
            _id: The source resource ID.
            resource: The resource dictionary to create.

        Returns:
            A tuple of (resource_id, created_resource_dict).
        """
        destination_client = self.config.destination_client

        # Check if account with same name already exists at destination
        account_name = resource["attributes"]["name"]
        if account_name in self.destination_accounts:
            # Account exists, update the destination state and call update instead
            self.config.state.destination[self.resource_type][_id] = self.destination_accounts[account_name]
            return await self.update_resource(_id, resource)

        payload = {"data": resource}
        resp = await destination_client.post(self.resource_config.base_path, payload)

        return _id, resp["data"]

    async def update_resource(self, _id: str, resource: Dict) -> Tuple[str, Dict]:
        """Update a Fastly integration account at the destination.

        Args:
            _id: The source resource ID.
            resource: The resource dictionary with updates.

        Returns:
            A tuple of (resource_id, updated_resource_dict).
        """
        destination_client = self.config.destination_client
        destination_resource_id = self.config.state.destination[self.resource_type][_id]["id"]
        payload = {"data": resource}
        resp = await destination_client.patch(
            self.resource_config.base_path + f"/{destination_resource_id}",
            payload,
        )

        return _id, resp["data"]

    async def delete_resource(self, _id: str) -> None:
        """Delete a Fastly integration account at the destination.

        Args:
            _id: The source resource ID (maps to destination via state).
        """
        destination_client = self.config.destination_client
        destination_resource_id = self.config.state.destination[self.resource_type][_id]["id"]
        await destination_client.delete(self.resource_config.base_path + f"/{destination_resource_id}")
