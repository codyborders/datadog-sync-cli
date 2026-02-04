# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""Unit tests for the AWSIntegration resource."""

import pytest
from unittest.mock import AsyncMock

from datadog_sync.model.aws_integration import AWSIntegration


@pytest.fixture
def aws_integration(config):
    """Create an AWSIntegration instance for testing."""
    return AWSIntegration(config)


class TestGetResourceId:
    """Tests for the _get_resource_id method."""

    def test_get_resource_id_with_role_name(self, aws_integration):
        """Test resource ID generation with role-based auth."""
        resource = {
            "account_id": "123456789012",
            "role_name": "DatadogIntegrationRole",
        }
        result = aws_integration._get_resource_id(resource)
        assert result == "123456789012:DatadogIntegrationRole"

    def test_get_resource_id_with_access_key(self, aws_integration):
        """Test resource ID generation with access key auth."""
        resource = {
            "account_id": "123456789012",
            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
        }
        result = aws_integration._get_resource_id(resource)
        assert result == "123456789012:AKIAIOSFODNN7EXAMPLE"

    def test_get_resource_id_prefers_access_key(self, aws_integration):
        """Test that access_key_id takes precedence when both are present."""
        resource = {
            "account_id": "123456789012",
            "role_name": "DatadogIntegrationRole",
            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
        }
        result = aws_integration._get_resource_id(resource)
        assert result == "123456789012:AKIAIOSFODNN7EXAMPLE"

    def test_get_resource_id_empty_values(self, aws_integration):
        """Test resource ID generation with empty values."""
        resource = {}
        result = aws_integration._get_resource_id(resource)
        assert result == ":"


class TestResourceConfig:
    """Tests for the resource configuration."""

    def test_resource_type(self, aws_integration):
        """Test that resource_type is correctly set."""
        assert aws_integration.resource_type == "aws_integration"

    def test_base_path(self, aws_integration):
        """Test that base_path is correctly set."""
        assert aws_integration.resource_config.base_path == "/api/v1/integration/aws"

    def test_excluded_attributes(self, aws_integration):
        """Test that excluded_attributes are correctly set."""
        # The attributes are transformed in build_excluded_attributes
        # Check that external_id and errors were in the original list
        config = aws_integration.resource_config
        # After transformation, they become deepdiff paths
        assert any("external_id" in attr for attr in config.excluded_attributes)
        assert any("errors" in attr for attr in config.excluded_attributes)


class TestGetResources:
    """Tests for the get_resources method."""

    @pytest.mark.asyncio
    async def test_get_resources(self, aws_integration):
        """Test fetching all AWS integrations."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {
            "accounts": [
                {"account_id": "123456789012", "role_name": "DatadogIntegrationRole"},
                {"account_id": "987654321098", "role_name": "DatadogRole"},
            ]
        }

        result = await aws_integration.get_resources(mock_client)

        mock_client.get.assert_called_once_with("/api/v1/integration/aws")
        assert len(result) == 2
        assert result[0]["account_id"] == "123456789012"

    @pytest.mark.asyncio
    async def test_get_resources_empty(self, aws_integration):
        """Test fetching when no AWS integrations exist."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {"accounts": []}

        result = await aws_integration.get_resources(mock_client)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_resources_missing_accounts_key(self, aws_integration):
        """Test fetching when response has no accounts key."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {}

        result = await aws_integration.get_resources(mock_client)

        assert result == []


class TestImportResource:
    """Tests for the import_resource method."""

    @pytest.mark.asyncio
    async def test_import_resource_with_resource(self, aws_integration):
        """Test importing with a provided resource."""
        resource = {
            "account_id": "123456789012",
            "role_name": "DatadogIntegrationRole",
            "host_tags": ["env:production"],
        }

        result_id, result_resource = await aws_integration.import_resource(resource=resource)

        assert result_id == "123456789012:DatadogIntegrationRole"
        assert result_resource == resource

    @pytest.mark.asyncio
    async def test_import_resource_with_id(self, aws_integration):
        """Test importing by fetching a specific resource ID."""
        aws_integration.config.source_client = AsyncMock()
        aws_integration.config.source_client.get.return_value = {
            "accounts": [
                {"account_id": "123456789012", "role_name": "DatadogIntegrationRole"},
                {"account_id": "987654321098", "role_name": "OtherRole"},
            ]
        }

        result_id, result_resource = await aws_integration.import_resource(_id="123456789012:DatadogIntegrationRole")

        assert result_id == "123456789012:DatadogIntegrationRole"
        assert result_resource["account_id"] == "123456789012"


class TestPreApplyHook:
    """Tests for the pre_apply_hook method."""

    @pytest.mark.asyncio
    async def test_pre_apply_hook(self, aws_integration):
        """Test that pre_apply_hook caches destination integrations."""
        aws_integration.config.destination_client = AsyncMock()
        aws_integration.config.destination_client.get.return_value = {
            "accounts": [
                {"account_id": "111111111111", "role_name": "ExistingRole"},
            ]
        }

        await aws_integration.pre_apply_hook()

        assert "111111111111:ExistingRole" in aws_integration.destination_integrations
        assert aws_integration.destination_integrations["111111111111:ExistingRole"]["account_id"] == "111111111111"


class TestCreateResource:
    """Tests for the create_resource method."""

    @pytest.mark.asyncio
    async def test_create_new_resource(self, aws_integration):
        """Test creating a new AWS integration."""
        aws_integration.destination_integrations = {}
        aws_integration.config.destination_client = AsyncMock()
        aws_integration.config.destination_client.post.return_value = {"external_id": "abc123def456"}

        resource = {
            "account_id": "123456789012",
            "role_name": "DatadogIntegrationRole",
            "host_tags": ["env:production"],
        }

        result_id, result_resource = await aws_integration.create_resource(
            "123456789012:DatadogIntegrationRole", resource
        )

        aws_integration.config.destination_client.post.assert_called_once_with("/api/v1/integration/aws", resource)
        assert result_id == "123456789012:DatadogIntegrationRole"
        assert result_resource["external_id"] == "abc123def456"

    @pytest.mark.asyncio
    async def test_create_existing_resource_updates(self, aws_integration):
        """Test that creating an existing resource triggers an update."""
        existing_resource = {
            "account_id": "123456789012",
            "role_name": "DatadogIntegrationRole",
        }
        aws_integration.destination_integrations = {"123456789012:DatadogIntegrationRole": existing_resource}
        aws_integration.config.destination_client = AsyncMock()
        aws_integration.config.destination_client.put.return_value = {}
        aws_integration.config.state.destination["aws_integration"] = {}

        resource = {
            "account_id": "123456789012",
            "role_name": "DatadogIntegrationRole",
            "host_tags": ["env:staging"],
        }

        result_id, _ = await aws_integration.create_resource("123456789012:DatadogIntegrationRole", resource)

        # Should call put (update) instead of post (create)
        aws_integration.config.destination_client.put.assert_called_once()
        assert result_id == "123456789012:DatadogIntegrationRole"


class TestUpdateResource:
    """Tests for the update_resource method."""

    @pytest.mark.asyncio
    async def test_update_resource_with_role(self, aws_integration):
        """Test updating an AWS integration with role-based auth."""
        aws_integration.config.destination_client = AsyncMock()
        aws_integration.config.destination_client.put.return_value = {}
        aws_integration.config.state.destination["aws_integration"] = {
            "123456789012:DatadogIntegrationRole": {
                "account_id": "123456789012",
                "role_name": "DatadogIntegrationRole",
            }
        }

        resource = {
            "account_id": "123456789012",
            "role_name": "DatadogIntegrationRole",
            "host_tags": ["env:production"],
        }

        result_id, _ = await aws_integration.update_resource("123456789012:DatadogIntegrationRole", resource)

        aws_integration.config.destination_client.put.assert_called_once()
        call_args = aws_integration.config.destination_client.put.call_args
        assert call_args[0][0] == "/api/v1/integration/aws"
        assert call_args[1]["params"]["account_id"] == "123456789012"
        assert call_args[1]["params"]["role_name"] == "DatadogIntegrationRole"

    @pytest.mark.asyncio
    async def test_update_resource_with_access_key(self, aws_integration):
        """Test updating an AWS integration with access key auth."""
        aws_integration.config.destination_client = AsyncMock()
        aws_integration.config.destination_client.put.return_value = {}
        aws_integration.config.state.destination["aws_integration"] = {
            "123456789012:AKIAIOSFODNN7EXAMPLE": {
                "account_id": "123456789012",
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
            }
        }

        resource = {
            "account_id": "123456789012",
            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "host_tags": ["env:govcloud"],
        }

        result_id, _ = await aws_integration.update_resource("123456789012:AKIAIOSFODNN7EXAMPLE", resource)

        call_args = aws_integration.config.destination_client.put.call_args
        assert call_args[1]["params"]["account_id"] == "123456789012"
        assert call_args[1]["params"]["access_key_id"] == "AKIAIOSFODNN7EXAMPLE"


class TestDeleteResource:
    """Tests for the delete_resource method."""

    @pytest.mark.asyncio
    async def test_delete_resource_with_role(self, aws_integration):
        """Test deleting an AWS integration with role-based auth."""
        aws_integration.config.destination_client = AsyncMock()
        aws_integration.config.state.destination["aws_integration"] = {
            "123456789012:DatadogIntegrationRole": {
                "account_id": "123456789012",
                "role_name": "DatadogIntegrationRole",
            }
        }

        await aws_integration.delete_resource("123456789012:DatadogIntegrationRole")

        aws_integration.config.destination_client.delete.assert_called_once()
        call_args = aws_integration.config.destination_client.delete.call_args
        assert call_args[0][0] == "/api/v1/integration/aws"
        assert call_args[1]["body"]["account_id"] == "123456789012"
        assert call_args[1]["body"]["role_name"] == "DatadogIntegrationRole"

    @pytest.mark.asyncio
    async def test_delete_resource_with_access_key(self, aws_integration):
        """Test deleting an AWS integration with access key auth."""
        aws_integration.config.destination_client = AsyncMock()
        aws_integration.config.state.destination["aws_integration"] = {
            "123456789012:AKIAIOSFODNN7EXAMPLE": {
                "account_id": "123456789012",
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
            }
        }

        await aws_integration.delete_resource("123456789012:AKIAIOSFODNN7EXAMPLE")

        call_args = aws_integration.config.destination_client.delete.call_args
        assert call_args[1]["body"]["account_id"] == "123456789012"
        assert call_args[1]["body"]["access_key_id"] == "AKIAIOSFODNN7EXAMPLE"
