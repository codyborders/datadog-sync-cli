# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""PagerDuty Integration resource for syncing PagerDuty service objects."""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List, Dict, Tuple, cast

from datadog_sync.utils.base_resource import BaseResource, ResourceConfig

if TYPE_CHECKING:
    from datadog_sync.utils.custom_client import CustomClient


class PagerDutyIntegration(BaseResource):
    """Resource class for managing PagerDuty integration services.

    This resource manages PagerDuty service objects that are configured
    within the Datadog-PagerDuty integration. Each service object represents
    a PagerDuty service that can receive alerts from Datadog.

    Note: The PagerDuty integration must be activated in the Datadog UI
    before services can be managed via this resource.
    """

    resource_type = "pagerduty_integration"
    resource_config = ResourceConfig(
        base_path="/api/v1/integration/pagerduty/configuration/services",
        excluded_attributes=[
            "service_key",  # Write-only field, cannot be read back from API
        ],
    )
    # Cache for destination services (keyed by service_name)
    destination_services: Dict[str, Dict] = {}

    async def get_resources(self, client: CustomClient) -> List[Dict]:
        """Retrieve all PagerDuty service objects from the integration.

        Args:
            client: The HTTP client to use for the request.

        Returns:
            List of PagerDuty service objects.
        """
        resp = await client.get(self.resource_config.base_path)
        # API returns {"services": [...]} format
        return resp.get("services", [])

    async def import_resource(self, _id: Optional[str] = None, resource: Optional[Dict] = None) -> Tuple[str, Dict]:
        """Import a single PagerDuty service object.

        Args:
            _id: The service_name to fetch, if not providing resource directly.
            resource: The resource object, if already fetched.

        Returns:
            Tuple of (service_name, resource_dict).
        """
        if _id:
            source_client = self.config.source_client
            resource = await source_client.get(self.resource_config.base_path + f"/{_id}")
        resource = cast(dict, resource)
        return resource["service_name"], resource

    async def pre_resource_action_hook(self, _id: str, resource: Dict) -> None:
        """Hook called before each resource action.

        Args:
            _id: The resource identifier (service_name).
            resource: The resource object.
        """
        pass

    async def pre_apply_hook(self) -> None:
        """Hook called before applying resources.

        Fetches and caches destination services for deduplication.
        """
        self.destination_services = await self.get_destination_services()

    async def create_resource(self, _id: str, resource: Dict) -> Tuple[str, Dict]:
        """Create a new PagerDuty service object.

        If a service with the same name already exists at the destination,
        updates it instead.

        Args:
            _id: The resource identifier (service_name from source).
            resource: The resource object to create.

        Returns:
            Tuple of (service_name, created_resource).
        """
        destination_client = self.config.destination_client
        service_name = resource["service_name"]

        # Check if service already exists at destination
        if service_name in self.destination_services:
            self.config.state.destination[self.resource_type][_id] = self.destination_services[service_name]
            return await self.update_resource(_id, resource)

        resp = await destination_client.post(self.resource_config.base_path, resource)
        return _id, resp

    async def update_resource(self, _id: str, resource: Dict) -> Tuple[str, Dict]:
        """Update an existing PagerDuty service object.

        Args:
            _id: The resource identifier (service_name from source).
            resource: The resource object with updates.

        Returns:
            Tuple of (service_name, updated_resource).
        """
        destination_client = self.config.destination_client
        dest_service_name = self.config.state.destination[self.resource_type][_id]["service_name"]
        resp = await destination_client.put(
            self.resource_config.base_path + f"/{dest_service_name}",
            resource,
        )
        return _id, resp

    async def delete_resource(self, _id: str) -> None:
        """Delete a PagerDuty service object.

        Args:
            _id: The resource identifier (service_name from source).
        """
        destination_client = self.config.destination_client
        dest_service_name = self.config.state.destination[self.resource_type][_id]["service_name"]
        await destination_client.delete(self.resource_config.base_path + f"/{dest_service_name}")

    async def get_destination_services(self) -> Dict[str, Dict]:
        """Fetch all PagerDuty services from the destination.

        Returns:
            Dict mapping service_name to service object.
        """
        destination_client = self.config.destination_client
        services = await self.get_resources(destination_client)
        return {s["service_name"]: s for s in services}
