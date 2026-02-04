# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""Webhooks Integration resource for syncing Datadog webhooks.

This module provides functionality to import, sync, and manage Datadog webhooks
between source and destination organizations.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List, Dict, Tuple, cast

from datadog_sync.utils.base_resource import BaseResource, ResourceConfig
from datadog_sync.utils.resource_utils import CustomClientHTTPError

if TYPE_CHECKING:
    from datadog_sync.utils.custom_client import CustomClient


class WebhooksIntegration(BaseResource):
    """Resource class for managing Datadog Webhooks Integration.

    Webhooks allow you to send notifications to custom endpoints when alerts are
    triggered in Datadog. This resource handles syncing webhooks between organizations.

    Note: The Webhooks API does not have a list endpoint, so webhooks must be
    retrieved individually by name.
    """

    resource_type = "webhooks_integration"
    resource_config = ResourceConfig(
        base_path="/api/v1/integration/webhooks/configuration/webhooks",
        excluded_attributes=[],
    )
    # Additional WebhooksIntegration specific attributes
    destination_webhooks: Dict[str, Dict] = {}

    async def get_resources(self, client: CustomClient) -> List[Dict]:
        """Get webhooks from the source organization.

        Note: The Datadog API does not provide a list endpoint for webhooks.
        This method returns an empty list as webhooks must be imported by name
        using filters or explicit resource IDs.

        Args:
            client: The HTTP client for making API requests.

        Returns:
            An empty list since webhooks cannot be listed via API.
        """
        # The Datadog API does not provide a list endpoint for webhooks.
        # Users must specify webhook names via filters or resource IDs.
        self.config.logger.warning(
            "Webhooks Integration API does not support listing all webhooks. "
            "Please use --filter to specify webhook names, or use import with specific webhook names."
        )
        return []

    async def import_resource(self, _id: Optional[str] = None, resource: Optional[Dict] = None) -> Tuple[str, Dict]:
        """Import a webhook resource from the source organization.

        Args:
            _id: The webhook name to import.
            resource: Optional pre-fetched resource data.

        Returns:
            A tuple of (webhook_name, webhook_data).

        Raises:
            CustomClientHTTPError: If the webhook cannot be retrieved.
        """
        if _id:
            source_client = self.config.source_client
            resource = await source_client.get(self.resource_config.base_path + f"/{_id}")

        resource = cast(dict, resource)
        return resource["name"], resource

    async def pre_resource_action_hook(self, _id: str, resource: Dict) -> None:
        """Hook called before each resource action.

        Args:
            _id: The webhook name.
            resource: The webhook resource data.
        """
        pass

    async def pre_apply_hook(self) -> None:
        """Hook called before applying changes.

        Fetches existing webhooks at the destination to enable matching by name.
        """
        self.destination_webhooks = await self.get_destination_webhooks()

    async def create_resource(self, _id: str, resource: Dict) -> Tuple[str, Dict]:
        """Create a new webhook at the destination.

        If a webhook with the same name already exists at the destination,
        it will be updated instead.

        Args:
            _id: The webhook name.
            resource: The webhook resource data.

        Returns:
            A tuple of (webhook_name, created_webhook_data).
        """
        destination_client = self.config.destination_client

        # Check if webhook already exists at destination by name
        if resource["name"] in self.destination_webhooks:
            self.config.state.destination[self.resource_type][_id] = self.destination_webhooks[resource["name"]]
            return await self.update_resource(_id, resource)

        resp = await destination_client.post(self.resource_config.base_path, resource)
        return _id, resp

    async def update_resource(self, _id: str, resource: Dict) -> Tuple[str, Dict]:
        """Update an existing webhook at the destination.

        Args:
            _id: The webhook name.
            resource: The webhook resource data.

        Returns:
            A tuple of (webhook_name, updated_webhook_data).
        """
        destination_client = self.config.destination_client
        webhook_name = self.config.state.destination[self.resource_type][_id]["name"]

        resp = await destination_client.put(
            self.resource_config.base_path + f"/{webhook_name}",
            resource,
        )
        return _id, resp

    async def delete_resource(self, _id: str) -> None:
        """Delete a webhook from the destination.

        Args:
            _id: The webhook name.
        """
        destination_client = self.config.destination_client
        webhook_name = self.config.state.destination[self.resource_type][_id]["name"]
        await destination_client.delete(self.resource_config.base_path + f"/{webhook_name}")

    async def get_destination_webhooks(self) -> Dict[str, Dict]:
        """Retrieve webhooks that exist at the destination.

        Since the API doesn't support listing, this method retrieves webhooks
        that are already tracked in the destination state.

        Returns:
            A dictionary mapping webhook names to their data.
        """
        destination_webhooks: Dict[str, Dict] = {}
        destination_client = self.config.destination_client

        # Check each webhook in the current destination state
        for _id, webhook_data in self.config.state.destination.get(self.resource_type, {}).items():
            webhook_name = webhook_data.get("name")
            if webhook_name:
                try:
                    resp = await destination_client.get(self.resource_config.base_path + f"/{webhook_name}")
                    destination_webhooks[webhook_name] = resp
                except CustomClientHTTPError as e:
                    if e.status_code == 404:
                        # Webhook no longer exists at destination
                        self.config.logger.debug(f"Webhook '{webhook_name}' not found at destination")
                    else:
                        self.config.logger.warning(f"Error fetching webhook '{webhook_name}': {e}")

        # Also check source webhooks that might already exist at destination
        for _id, webhook_data in self.config.state.source.get(self.resource_type, {}).items():
            webhook_name = webhook_data.get("name")
            if webhook_name and webhook_name not in destination_webhooks:
                try:
                    resp = await destination_client.get(self.resource_config.base_path + f"/{webhook_name}")
                    destination_webhooks[webhook_name] = resp
                except CustomClientHTTPError as e:
                    if e.status_code == 404:
                        # Webhook doesn't exist at destination yet, which is expected
                        pass
                    else:
                        self.config.logger.warning(f"Error fetching webhook '{webhook_name}': {e}")

        return destination_webhooks
