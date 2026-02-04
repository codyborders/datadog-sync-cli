# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""Unit tests for the AzureIntegration resource."""

import pytest
from unittest.mock import AsyncMock

from datadog_sync.model.azure_integration import AzureIntegration


@pytest.fixture
def azure_integration(config):
    """Create an AzureIntegration instance for testing."""
    return AzureIntegration(config)


class TestGetResourceId:
    """Tests for the _get_resource_id method."""

    def test_get_resource_id(self, azure_integration):
        """Test resource ID generation with tenant and client ID."""
        resource = {
            "tenant_name": "my-tenant.onmicrosoft.com",
            "client_id": "12345678-1234-1234-1234-123456789012",
        }
        result = azure_integration._get_resource_id(resource)
        assert result == "my-tenant.onmicrosoft.com:12345678-1234-1234-1234-123456789012"

    def test_get_resource_id_empty_values(self, azure_integration):
        """Test resource ID generation with empty values."""
        resource = {}
        result = azure_integration._get_resource_id(resource)
        assert result == ":"

    def test_get_resource_id_partial_values(self, azure_integration):
        """Test resource ID generation with only tenant_name."""
        resource = {"tenant_name": "my-tenant.onmicrosoft.com"}
        result = azure_integration._get_resource_id(resource)
        assert result == "my-tenant.onmicrosoft.com:"


class TestResourceConfig:
    """Tests for the resource configuration."""

    def test_resource_type(self, azure_integration):
        """Test that resource_type is correctly set."""
        assert azure_integration.resource_type == "azure_integration"

    def test_base_path(self, azure_integration):
        """Test that base_path is correctly set."""
        assert azure_integration.resource_config.base_path == "/api/v1/integration/azure"

    def test_excluded_attributes(self, azure_integration):
        """Test that excluded_attributes are correctly set."""
        # The attributes are transformed in build_excluded_attributes
        # Check that client_secret and errors were in the original list
        config = azure_integration.resource_config
        # After transformation, they become deepdiff paths
        assert any("client_secret" in attr for attr in config.excluded_attributes)
        assert any("errors" in attr for attr in config.excluded_attributes)


class TestGetResources:
    """Tests for the get_resources method."""

    @pytest.mark.asyncio
    async def test_get_resources(self, azure_integration):
        """Test fetching all Azure integrations."""
        mock_client = AsyncMock()
        mock_client.get.return_value = [
            {"tenant_name": "tenant1.onmicrosoft.com", "client_id": "client-id-1"},
            {"tenant_name": "tenant2.onmicrosoft.com", "client_id": "client-id-2"},
        ]

        result = await azure_integration.get_resources(mock_client)

        mock_client.get.assert_called_once_with("/api/v1/integration/azure")
        assert len(result) == 2
        assert result[0]["tenant_name"] == "tenant1.onmicrosoft.com"

    @pytest.mark.asyncio
    async def test_get_resources_empty(self, azure_integration):
        """Test fetching when no Azure integrations exist."""
        mock_client = AsyncMock()
        mock_client.get.return_value = []

        result = await azure_integration.get_resources(mock_client)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_resources_non_list_response(self, azure_integration):
        """Test fetching when response is not a list."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {}

        result = await azure_integration.get_resources(mock_client)

        assert result == []


class TestImportResource:
    """Tests for the import_resource method."""

    @pytest.mark.asyncio
    async def test_import_resource_with_resource(self, azure_integration):
        """Test importing with a provided resource."""
        resource = {
            "tenant_name": "my-tenant.onmicrosoft.com",
            "client_id": "12345678-1234-1234-1234-123456789012",
            "host_filters": "tag:env:production",
        }

        result_id, result_resource = await azure_integration.import_resource(resource=resource)

        assert result_id == "my-tenant.onmicrosoft.com:12345678-1234-1234-1234-123456789012"
        assert result_resource == resource

    @pytest.mark.asyncio
    async def test_import_resource_with_id(self, azure_integration):
        """Test importing by fetching a specific resource ID."""
        azure_integration.config.source_client = AsyncMock()
        azure_integration.config.source_client.get.return_value = [
            {"tenant_name": "my-tenant.onmicrosoft.com", "client_id": "12345678-1234-1234-1234-123456789012"},
            {"tenant_name": "other-tenant.onmicrosoft.com", "client_id": "other-client-id"},
        ]

        result_id, result_resource = await azure_integration.import_resource(
            _id="my-tenant.onmicrosoft.com:12345678-1234-1234-1234-123456789012"
        )

        assert result_id == "my-tenant.onmicrosoft.com:12345678-1234-1234-1234-123456789012"
        assert result_resource["tenant_name"] == "my-tenant.onmicrosoft.com"


class TestPreApplyHook:
    """Tests for the pre_apply_hook method."""

    @pytest.mark.asyncio
    async def test_pre_apply_hook(self, azure_integration):
        """Test that pre_apply_hook caches destination integrations."""
        azure_integration.config.destination_client = AsyncMock()
        azure_integration.config.destination_client.get.return_value = [
            {"tenant_name": "existing-tenant.onmicrosoft.com", "client_id": "existing-client-id"},
        ]

        await azure_integration.pre_apply_hook()

        assert "existing-tenant.onmicrosoft.com:existing-client-id" in azure_integration.destination_integrations
        assert (
            azure_integration.destination_integrations["existing-tenant.onmicrosoft.com:existing-client-id"][
                "tenant_name"
            ]
            == "existing-tenant.onmicrosoft.com"
        )


class TestCreateResource:
    """Tests for the create_resource method."""

    @pytest.mark.asyncio
    async def test_create_new_resource(self, azure_integration):
        """Test creating a new Azure integration."""
        azure_integration.destination_integrations = {}
        azure_integration.config.destination_client = AsyncMock()
        azure_integration.config.destination_client.post.return_value = {}

        resource = {
            "tenant_name": "my-tenant.onmicrosoft.com",
            "client_id": "12345678-1234-1234-1234-123456789012",
            "client_secret": "secret-value",
            "host_filters": "tag:env:production",
        }

        result_id, result_resource = await azure_integration.create_resource(
            "my-tenant.onmicrosoft.com:12345678-1234-1234-1234-123456789012", resource
        )

        azure_integration.config.destination_client.post.assert_called_once_with("/api/v1/integration/azure", resource)
        assert result_id == "my-tenant.onmicrosoft.com:12345678-1234-1234-1234-123456789012"
        assert result_resource == resource

    @pytest.mark.asyncio
    async def test_create_existing_resource_updates(self, azure_integration):
        """Test that creating an existing resource triggers an update."""
        existing_resource = {
            "tenant_name": "my-tenant.onmicrosoft.com",
            "client_id": "12345678-1234-1234-1234-123456789012",
        }
        azure_integration.destination_integrations = {
            "my-tenant.onmicrosoft.com:12345678-1234-1234-1234-123456789012": existing_resource
        }
        azure_integration.config.destination_client = AsyncMock()
        azure_integration.config.destination_client.put.return_value = {}
        azure_integration.config.state.destination["azure_integration"] = {}

        resource = {
            "tenant_name": "my-tenant.onmicrosoft.com",
            "client_id": "12345678-1234-1234-1234-123456789012",
            "host_filters": "tag:env:staging",
        }

        result_id, _ = await azure_integration.create_resource(
            "my-tenant.onmicrosoft.com:12345678-1234-1234-1234-123456789012", resource
        )

        # Should call put (update) instead of post (create)
        azure_integration.config.destination_client.put.assert_called_once()
        assert result_id == "my-tenant.onmicrosoft.com:12345678-1234-1234-1234-123456789012"


class TestUpdateResource:
    """Tests for the update_resource method."""

    @pytest.mark.asyncio
    async def test_update_resource(self, azure_integration):
        """Test updating an Azure integration."""
        azure_integration.config.destination_client = AsyncMock()
        azure_integration.config.destination_client.put.return_value = {}
        azure_integration.config.state.destination["azure_integration"] = {
            "my-tenant.onmicrosoft.com:12345678-1234-1234-1234-123456789012": {
                "tenant_name": "my-tenant.onmicrosoft.com",
                "client_id": "12345678-1234-1234-1234-123456789012",
            }
        }

        resource = {
            "tenant_name": "my-tenant.onmicrosoft.com",
            "client_id": "12345678-1234-1234-1234-123456789012",
            "host_filters": "tag:env:production",
        }

        result_id, result_resource = await azure_integration.update_resource(
            "my-tenant.onmicrosoft.com:12345678-1234-1234-1234-123456789012", resource
        )

        azure_integration.config.destination_client.put.assert_called_once_with("/api/v1/integration/azure", resource)
        assert result_id == "my-tenant.onmicrosoft.com:12345678-1234-1234-1234-123456789012"
        assert result_resource == resource


class TestDeleteResource:
    """Tests for the delete_resource method."""

    @pytest.mark.asyncio
    async def test_delete_resource(self, azure_integration):
        """Test deleting an Azure integration."""
        azure_integration.config.destination_client = AsyncMock()
        azure_integration.config.state.destination["azure_integration"] = {
            "my-tenant.onmicrosoft.com:12345678-1234-1234-1234-123456789012": {
                "tenant_name": "my-tenant.onmicrosoft.com",
                "client_id": "12345678-1234-1234-1234-123456789012",
            }
        }

        await azure_integration.delete_resource("my-tenant.onmicrosoft.com:12345678-1234-1234-1234-123456789012")

        azure_integration.config.destination_client.delete.assert_called_once()
        call_args = azure_integration.config.destination_client.delete.call_args
        assert call_args[0][0] == "/api/v1/integration/azure"
        assert call_args[1]["body"]["tenant_name"] == "my-tenant.onmicrosoft.com"
        assert call_args[1]["body"]["client_id"] == "12345678-1234-1234-1234-123456789012"

    @pytest.mark.asyncio
    async def test_delete_resource_missing_from_state(self, azure_integration):
        """Test deleting a resource not in destination state."""
        azure_integration.config.destination_client = AsyncMock()
        azure_integration.config.state.destination["azure_integration"] = {}

        await azure_integration.delete_resource("nonexistent:resource")

        azure_integration.config.destination_client.delete.assert_called_once()
        call_args = azure_integration.config.destination_client.delete.call_args
        assert call_args[1]["body"]["tenant_name"] is None
        assert call_args[1]["body"]["client_id"] is None
