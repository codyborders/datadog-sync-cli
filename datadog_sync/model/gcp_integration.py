# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""GCP Integration resource module for syncing GCP STS accounts between Datadog orgs."""

from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, cast

from datadog_sync.utils.base_resource import BaseResource, ResourceConfig

if TYPE_CHECKING:
    from datadog_sync.utils.custom_client import CustomClient


class GCPIntegration(BaseResource):
    """Resource class for managing GCP Integration STS accounts.

    This resource handles the synchronization of GCP Service Token Service (STS)
    accounts between Datadog organizations using the v2 API.
    """

    resource_type = "gcp_integration"
    resource_config = ResourceConfig(
        base_path="/api/v2/integration/gcp/accounts",
        excluded_attributes=[
            "id",
        ],
    )
    # Additional GCPIntegration specific attributes
    destination_gcp_accounts: Dict[str, Dict] = {}

    async def get_resources(self, client: CustomClient) -> List[Dict]:
        """Retrieve all GCP STS accounts from the Datadog organization.

        Args:
            client: The CustomClient instance for making API requests.

        Returns:
            A list of GCP account dictionaries.
        """
        resp = await client.get(self.resource_config.base_path)
        return resp.get("data", [])

    async def import_resource(self, _id: Optional[str] = None, resource: Optional[Dict] = None) -> Tuple[str, Dict]:
        """Import a GCP account resource from the source organization.

        Args:
            _id: Optional resource ID to fetch directly.
            resource: Optional pre-fetched resource dictionary.

        Returns:
            A tuple of (resource_id, resource_dict).
        """
        if _id:
            source_client = self.config.source_client
            resource = (await source_client.get(self.resource_config.base_path + f"/{_id}"))["data"]

        resource = cast(dict, resource)
        return resource["id"], resource

    async def pre_resource_action_hook(self, _id: str, resource: Dict) -> None:
        """Hook executed before each resource action.

        Args:
            _id: The resource ID.
            resource: The resource dictionary.
        """
        pass

    async def pre_apply_hook(self) -> None:
        """Hook executed before applying changes to destination.

        Retrieves existing GCP accounts from the destination to enable
        matching by client_email for updates.
        """
        self.destination_gcp_accounts = await self._get_destination_gcp_accounts()

    async def create_resource(self, _id: str, resource: Dict) -> Tuple[str, Dict]:
        """Create a new GCP account in the destination organization.

        If an account with the same client_email already exists, updates it instead.

        Args:
            _id: The source resource ID.
            resource: The resource dictionary to create.

        Returns:
            A tuple of (resource_id, created_resource_dict).
        """
        destination_client = self.config.destination_client

        # Check if account already exists by client_email
        client_email = resource.get("attributes", {}).get("client_email")
        if client_email and client_email in self.destination_gcp_accounts:
            self.config.state.destination[self.resource_type][_id] = self.destination_gcp_accounts[client_email]
            return await self.update_resource(_id, resource)

        payload = {"data": resource}
        resp = await destination_client.post(self.resource_config.base_path, payload)

        return _id, resp["data"]

    async def update_resource(self, _id: str, resource: Dict) -> Tuple[str, Dict]:
        """Update an existing GCP account in the destination organization.

        Args:
            _id: The source resource ID.
            resource: The resource dictionary with updates.

        Returns:
            A tuple of (resource_id, updated_resource_dict).
        """
        destination_client = self.config.destination_client
        dest_id = self.config.state.destination[self.resource_type][_id]["id"]

        payload = {"data": resource}
        resp = await destination_client.patch(
            self.resource_config.base_path + f"/{dest_id}",
            payload,
        )

        return _id, resp["data"]

    async def delete_resource(self, _id: str) -> None:
        """Delete a GCP account from the destination organization.

        Args:
            _id: The source resource ID.
        """
        destination_client = self.config.destination_client
        dest_id = self.config.state.destination[self.resource_type][_id]["id"]

        await destination_client.delete(self.resource_config.base_path + f"/{dest_id}")

    async def _get_destination_gcp_accounts(self) -> Dict[str, Dict]:
        """Retrieve existing GCP accounts from the destination indexed by client_email.

        Returns:
            A dictionary mapping client_email to account resource dictionaries.
        """
        destination_client = self.config.destination_client
        destination_accounts: Dict[str, Dict] = {}

        resp = await self.get_resources(destination_client)
        for account in resp:
            client_email = account.get("attributes", {}).get("client_email")
            if client_email:
                destination_accounts[client_email] = account

        return destination_accounts
