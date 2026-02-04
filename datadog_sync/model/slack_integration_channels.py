# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""Slack Integration Channels resource for syncing Slack channel configurations between Datadog organizations."""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List, Dict, Tuple, cast

from datadog_sync.utils.base_resource import BaseResource, ResourceConfig

if TYPE_CHECKING:
    from datadog_sync.utils.custom_client import CustomClient


class SlackIntegrationChannels(BaseResource):
    """Resource class for managing Slack Integration channel configurations.

    This resource handles syncing Slack integration channel configurations between
    source and destination Datadog organizations. Channels are identified by a
    composite key of account_name:channel_name.

    The Slack Integration API has a hierarchical structure:
    - First, list all Slack accounts
    - For each account, list all configured channels

    API Endpoints:
    - GET /api/v1/integration/slack/configuration/accounts - List accounts
    - GET /api/v1/integration/slack/configuration/accounts/{account_name}/channels - List channels
    - GET /api/v1/integration/slack/configuration/accounts/{account_name}/channels/{channel_name} - Get channel
    - POST /api/v1/integration/slack/configuration/accounts/{account_name}/channels - Create channel
    - PATCH /api/v1/integration/slack/configuration/accounts/{account_name}/channels/{channel_name} - Update
    - DELETE /api/v1/integration/slack/configuration/accounts/{account_name}/channels/{channel_name} - Delete
    """

    resource_type = "slack_integration_channels"
    resource_config = ResourceConfig(
        base_path="/api/v1/integration/slack/configuration/accounts",
        excluded_attributes=[],
    )
    # Additional SlackIntegrationChannels specific attributes
    destination_channels: Dict[str, Dict] = {}

    async def get_resources(self, client: CustomClient) -> List[Dict]:
        """Fetch all Slack integration channels from all accounts.

        This method first retrieves all Slack accounts, then for each account
        retrieves all configured channels. Each channel is augmented with its
        account_name for identification purposes.

        Args:
            client: The CustomClient instance to use for API requests.

        Returns:
            A list of Slack channel dictionaries, each containing an _account_name field.
        """
        all_channels: List[Dict] = []

        # Get all Slack accounts
        accounts_resp = await client.get(self.resource_config.base_path)
        accounts = accounts_resp if isinstance(accounts_resp, list) else []

        # For each account, get all channels
        for account in accounts:
            account_name = account.get("name", account.get("account_name", ""))
            if not account_name:
                continue

            channels_path = f"{self.resource_config.base_path}/{account_name}/channels"
            try:
                channels_resp = await client.get(channels_path)
                channels = channels_resp if isinstance(channels_resp, list) else []

                # Augment each channel with account_name for identification
                for channel in channels:
                    channel["_account_name"] = account_name
                    all_channels.append(channel)
            except Exception as e:
                self.config.logger.warning(f"Error fetching channels for account {account_name}: {e}")

        return all_channels

    async def import_resource(self, _id: Optional[str] = None, resource: Optional[Dict] = None) -> Tuple[str, Dict]:
        """Import a Slack integration channel resource.

        Args:
            _id: Optional composite ID (account_name:channel_name) of the resource to import.
            resource: Optional resource dictionary if already fetched.

        Returns:
            A tuple of (composite_id, resource_dict).
        """
        if _id:
            source_client = self.config.source_client
            # Parse composite ID
            account_name, channel_name = self._parse_composite_id(_id)
            channel_path = f"{self.resource_config.base_path}/{account_name}/channels/{channel_name}"
            resource = await source_client.get(channel_path)
            resource["_account_name"] = account_name

        resource = cast(dict, resource)
        composite_id = self._get_composite_id(resource)
        return composite_id, resource

    async def pre_resource_action_hook(self, _id: str, resource: Dict) -> None:
        """Hook called before any resource action (create/update).

        Args:
            _id: The resource ID.
            resource: The resource dictionary.
        """
        pass

    async def pre_apply_hook(self) -> None:
        """Hook called before applying changes to destination.

        Fetches existing Slack channels from the destination to enable
        matching by composite key (account_name:channel_name) during create operations.
        """
        client = self.config.destination_client
        resp = await self.get_resources(client)
        self.destination_channels = {}
        for channel in resp:
            composite_id = self._get_composite_id(channel)
            self.destination_channels[composite_id] = channel

    async def create_resource(self, _id: str, resource: Dict) -> Tuple[str, Dict]:
        """Create a Slack integration channel at the destination.

        If a channel with the same account_name:channel_name already exists at the
        destination, updates that channel instead of creating a new one.

        Args:
            _id: The source resource composite ID.
            resource: The resource dictionary to create.

        Returns:
            A tuple of (composite_id, created_resource_dict).
        """
        destination_client = self.config.destination_client

        # Check if channel already exists at destination
        if _id in self.destination_channels:
            # Channel exists, update the destination state and call update instead
            self.config.state.destination[self.resource_type][_id] = self.destination_channels[_id]
            return await self.update_resource(_id, resource)

        account_name = resource.get("_account_name", "")
        channels_path = f"{self.resource_config.base_path}/{account_name}/channels"

        # Remove internal tracking field before sending to API
        payload = self._prepare_payload(resource)
        resp = await destination_client.post(channels_path, payload)

        # Add back the account_name for state tracking
        resp["_account_name"] = account_name

        return _id, resp

    async def update_resource(self, _id: str, resource: Dict) -> Tuple[str, Dict]:
        """Update a Slack integration channel at the destination.

        Args:
            _id: The source resource composite ID.
            resource: The resource dictionary with updates.

        Returns:
            A tuple of (composite_id, updated_resource_dict).
        """
        destination_client = self.config.destination_client
        account_name, channel_name = self._parse_composite_id(_id)

        channel_path = f"{self.resource_config.base_path}/{account_name}/channels/{channel_name}"
        payload = self._prepare_payload(resource)
        resp = await destination_client.patch(channel_path, payload)

        # Add back the account_name for state tracking
        resp["_account_name"] = account_name

        return _id, resp

    async def delete_resource(self, _id: str) -> None:
        """Delete a Slack integration channel at the destination.

        Args:
            _id: The source resource composite ID.
        """
        destination_client = self.config.destination_client
        account_name, channel_name = self._parse_composite_id(_id)

        channel_path = f"{self.resource_config.base_path}/{account_name}/channels/{channel_name}"
        await destination_client.delete(channel_path)

    def _get_composite_id(self, resource: Dict) -> str:
        """Generate a composite ID from account_name and channel_name.

        Args:
            resource: The channel resource dictionary.

        Returns:
            A composite ID string in the format "account_name:channel_name".
        """
        account_name = resource.get("_account_name", "")
        channel_name = resource.get("channel_name", resource.get("name", ""))
        return f"{account_name}:{channel_name}"

    def _parse_composite_id(self, composite_id: str) -> Tuple[str, str]:
        """Parse a composite ID into account_name and channel_name.

        Args:
            composite_id: The composite ID string.

        Returns:
            A tuple of (account_name, channel_name).
        """
        parts = composite_id.split(":", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return "", composite_id

    def _prepare_payload(self, resource: Dict) -> Dict:
        """Prepare the resource payload for API requests.

        Removes internal tracking fields that should not be sent to the API.

        Args:
            resource: The resource dictionary.

        Returns:
            A new dictionary suitable for API requests.
        """
        payload = dict(resource)
        # Remove internal tracking field
        payload.pop("_account_name", None)
        return payload
