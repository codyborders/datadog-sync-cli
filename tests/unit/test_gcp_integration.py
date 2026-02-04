# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""Unit tests for GCP Integration resource."""

import pytest
from unittest.mock import AsyncMock

from datadog_sync.model.gcp_integration import GCPIntegration


@pytest.fixture
def gcp_integration(config):
    """Create a GCPIntegration instance for testing."""
    return GCPIntegration(config)


@pytest.fixture
def sample_gcp_account():
    """Sample GCP account resource data."""
    return {
        "id": "test-account-id-123",
        "type": "gcp_service_account",
        "attributes": {
            "client_email": "test-service-account@test-project.iam.gserviceaccount.com",
            "account_tags": ["env:test", "team:platform"],
            "automute": True,
            "is_cspm_enabled": False,
            "resource_collection_enabled": True,
        },
    }


class TestGCPIntegrationResourceConfig:
    """Tests for GCPIntegration resource configuration."""

    def test_resource_type(self, gcp_integration):
        """Test that resource_type is correctly set."""
        assert gcp_integration.resource_type == "gcp_integration"

    def test_base_path(self, gcp_integration):
        """Test that base_path is correctly configured."""
        assert gcp_integration.resource_config.base_path == "/api/v2/integration/gcp/accounts"

    def test_excluded_attributes(self, gcp_integration):
        """Test that excluded_attributes are correctly configured."""
        # Excluded attributes are transformed to deepdiff paths
        expected_excluded = ["root['id']"]
        assert gcp_integration.resource_config.excluded_attributes == expected_excluded


class TestGCPIntegrationGetResources:
    """Tests for get_resources method."""

    @pytest.mark.asyncio
    async def test_get_resources_returns_data(self, gcp_integration, sample_gcp_account):
        """Test that get_resources returns the data array from response."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value={"data": [sample_gcp_account]})

        result = await gcp_integration.get_resources(mock_client)

        mock_client.get.assert_called_once_with("/api/v2/integration/gcp/accounts")
        assert result == [sample_gcp_account]

    @pytest.mark.asyncio
    async def test_get_resources_empty_response(self, gcp_integration):
        """Test that get_resources handles empty response."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value={"data": []})

        result = await gcp_integration.get_resources(mock_client)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_resources_missing_data_key(self, gcp_integration):
        """Test that get_resources handles missing data key."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value={})

        result = await gcp_integration.get_resources(mock_client)

        assert result == []


class TestGCPIntegrationImportResource:
    """Tests for import_resource method."""

    @pytest.mark.asyncio
    async def test_import_resource_with_resource(self, gcp_integration, sample_gcp_account):
        """Test importing a resource when resource dict is provided."""
        _id, resource = await gcp_integration.import_resource(resource=sample_gcp_account)

        assert _id == "test-account-id-123"
        assert resource == sample_gcp_account

    @pytest.mark.asyncio
    async def test_import_resource_with_id(self, gcp_integration, config, sample_gcp_account):
        """Test importing a resource by fetching with ID."""
        config.source_client.get = AsyncMock(return_value={"data": sample_gcp_account})

        _id, resource = await gcp_integration.import_resource(_id="test-account-id-123")

        config.source_client.get.assert_called_once_with("/api/v2/integration/gcp/accounts/test-account-id-123")
        assert _id == "test-account-id-123"
        assert resource == sample_gcp_account


class TestGCPIntegrationCreateResource:
    """Tests for create_resource method."""

    @pytest.mark.asyncio
    async def test_create_resource_new_account(self, gcp_integration, config, sample_gcp_account):
        """Test creating a new GCP account."""
        config.destination_client.post = AsyncMock(return_value={"data": sample_gcp_account})
        gcp_integration.destination_gcp_accounts = {}

        _id, resource = await gcp_integration.create_resource("test-id", sample_gcp_account)

        config.destination_client.post.assert_called_once_with(
            "/api/v2/integration/gcp/accounts", {"data": sample_gcp_account}
        )
        assert _id == "test-id"
        assert resource == sample_gcp_account

    @pytest.mark.asyncio
    async def test_create_resource_existing_account_updates(self, gcp_integration, config, sample_gcp_account):
        """Test that creating an existing account (by client_email) triggers update."""
        client_email = sample_gcp_account["attributes"]["client_email"]
        existing_account = {**sample_gcp_account, "id": "dest-account-id"}

        gcp_integration.destination_gcp_accounts = {client_email: existing_account}
        config.state.destination["gcp_integration"] = {"test-id": existing_account}
        config.destination_client.patch = AsyncMock(return_value={"data": sample_gcp_account})

        _id, resource = await gcp_integration.create_resource("test-id", sample_gcp_account)

        # Should call patch (update) instead of post (create)
        config.destination_client.patch.assert_called_once()
        assert _id == "test-id"


class TestGCPIntegrationUpdateResource:
    """Tests for update_resource method."""

    @pytest.mark.asyncio
    async def test_update_resource(self, gcp_integration, config, sample_gcp_account):
        """Test updating an existing GCP account."""
        dest_account = {**sample_gcp_account, "id": "dest-account-id"}
        config.state.destination["gcp_integration"] = {"test-id": dest_account}
        config.destination_client.patch = AsyncMock(return_value={"data": sample_gcp_account})

        _id, resource = await gcp_integration.update_resource("test-id", sample_gcp_account)

        config.destination_client.patch.assert_called_once_with(
            "/api/v2/integration/gcp/accounts/dest-account-id", {"data": sample_gcp_account}
        )
        assert _id == "test-id"
        assert resource == sample_gcp_account


class TestGCPIntegrationDeleteResource:
    """Tests for delete_resource method."""

    @pytest.mark.asyncio
    async def test_delete_resource(self, gcp_integration, config, sample_gcp_account):
        """Test deleting a GCP account."""
        dest_account = {**sample_gcp_account, "id": "dest-account-id"}
        config.state.destination["gcp_integration"] = {"test-id": dest_account}
        config.destination_client.delete = AsyncMock(return_value=None)

        await gcp_integration.delete_resource("test-id")

        config.destination_client.delete.assert_called_once_with("/api/v2/integration/gcp/accounts/dest-account-id")


class TestGCPIntegrationPreApplyHook:
    """Tests for pre_apply_hook method."""

    @pytest.mark.asyncio
    async def test_pre_apply_hook_loads_destination_accounts(self, gcp_integration, config, sample_gcp_account):
        """Test that pre_apply_hook loads destination accounts."""
        config.destination_client.get = AsyncMock(return_value={"data": [sample_gcp_account]})

        await gcp_integration.pre_apply_hook()

        client_email = sample_gcp_account["attributes"]["client_email"]
        assert client_email in gcp_integration.destination_gcp_accounts
        assert gcp_integration.destination_gcp_accounts[client_email] == sample_gcp_account


class TestGCPIntegrationGetDestinationGCPAccounts:
    """Tests for get_destination_gcp_accounts method."""

    @pytest.mark.asyncio
    async def test_get_destination_gcp_accounts(self, gcp_integration, config, sample_gcp_account):
        """Test retrieving destination accounts indexed by client_email."""
        config.destination_client.get = AsyncMock(return_value={"data": [sample_gcp_account]})

        result = await gcp_integration.get_destination_gcp_accounts()

        client_email = sample_gcp_account["attributes"]["client_email"]
        assert client_email in result
        assert result[client_email] == sample_gcp_account

    @pytest.mark.asyncio
    async def test_get_destination_gcp_accounts_handles_missing_email(self, gcp_integration, config):
        """Test handling accounts without client_email attribute."""
        account_without_email = {
            "id": "test-id",
            "type": "gcp_service_account",
            "attributes": {},
        }
        config.destination_client.get = AsyncMock(return_value={"data": [account_without_email]})

        result = await gcp_integration.get_destination_gcp_accounts()

        assert result == {}
