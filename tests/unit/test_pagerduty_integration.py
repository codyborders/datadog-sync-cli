# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""Unit tests for PagerDutyIntegration resource class."""

import pytest
from unittest.mock import AsyncMock

from datadog_sync.model.pagerduty_integration import PagerDutyIntegration


@pytest.fixture
def pagerduty_resource(config):
    """Create a PagerDutyIntegration instance for testing."""
    return PagerDutyIntegration(config)


@pytest.fixture
def sample_service():
    """Sample PagerDuty service object."""
    return {
        "service_name": "test-service",
        "service_key": "test-key-12345",
    }


@pytest.fixture
def sample_service_list(sample_service):
    """Sample list of PagerDuty service objects."""
    return [
        sample_service,
        {
            "service_name": "another-service",
            "service_key": "another-key-67890",
        },
    ]


class TestPagerDutyIntegrationConfig:
    """Tests for PagerDutyIntegration configuration."""

    def test_resource_type(self, pagerduty_resource):
        """Test resource_type is set correctly."""
        assert pagerduty_resource.resource_type == "pagerduty_integration"

    def test_base_path(self, pagerduty_resource):
        """Test base_path is set correctly."""
        expected_path = "/api/v1/integration/pagerduty/configuration/services"
        assert pagerduty_resource.resource_config.base_path == expected_path

    def test_excluded_attributes_contains_service_key(self, pagerduty_resource):
        """Test service_key is excluded from diffs."""
        # excluded_attributes are transformed in __post_init__ to deepdiff format
        excluded = pagerduty_resource.resource_config.excluded_attributes
        assert any("service_key" in attr for attr in excluded)


class TestGetResources:
    """Tests for get_resources method."""

    @pytest.mark.asyncio
    async def test_get_resources_returns_services(self, pagerduty_resource, sample_service_list):
        """Test get_resources returns list of services."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {"services": sample_service_list}

        result = await pagerduty_resource.get_resources(mock_client)

        assert result == sample_service_list
        mock_client.get.assert_called_once_with("/api/v1/integration/pagerduty/configuration/services")

    @pytest.mark.asyncio
    async def test_get_resources_empty_response(self, pagerduty_resource):
        """Test get_resources handles empty response."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {"services": []}

        result = await pagerduty_resource.get_resources(mock_client)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_resources_missing_services_key(self, pagerduty_resource):
        """Test get_resources handles response without services key."""
        mock_client = AsyncMock()
        mock_client.get.return_value = {}

        result = await pagerduty_resource.get_resources(mock_client)

        assert result == []


class TestImportResource:
    """Tests for import_resource method."""

    @pytest.mark.asyncio
    async def test_import_resource_with_id(self, pagerduty_resource, sample_service):
        """Test import_resource fetches by service_name."""
        pagerduty_resource.config.source_client = AsyncMock()
        pagerduty_resource.config.source_client.get.return_value = sample_service

        _id, resource = await pagerduty_resource.import_resource(_id="test-service")

        assert _id == "test-service"
        assert resource == sample_service
        pagerduty_resource.config.source_client.get.assert_called_once_with(
            "/api/v1/integration/pagerduty/configuration/services/test-service"
        )

    @pytest.mark.asyncio
    async def test_import_resource_with_resource(self, pagerduty_resource, sample_service):
        """Test import_resource with provided resource."""
        _id, resource = await pagerduty_resource.import_resource(resource=sample_service)

        assert _id == "test-service"
        assert resource == sample_service


class TestPreApplyHook:
    """Tests for pre_apply_hook method."""

    @pytest.mark.asyncio
    async def test_pre_apply_hook_caches_destination_services(self, pagerduty_resource, sample_service_list):
        """Test pre_apply_hook fetches and caches destination services."""
        pagerduty_resource.config.destination_client = AsyncMock()
        pagerduty_resource.config.destination_client.get.return_value = {"services": sample_service_list}

        await pagerduty_resource.pre_apply_hook()

        assert "test-service" in pagerduty_resource.destination_services
        assert "another-service" in pagerduty_resource.destination_services
        assert pagerduty_resource.destination_services["test-service"] == sample_service_list[0]


class TestCreateResource:
    """Tests for create_resource method."""

    @pytest.mark.asyncio
    async def test_create_resource_new_service(self, pagerduty_resource, sample_service):
        """Test create_resource creates new service."""
        pagerduty_resource.destination_services = {}
        pagerduty_resource.config.destination_client = AsyncMock()
        pagerduty_resource.config.destination_client.post.return_value = sample_service

        _id, result = await pagerduty_resource.create_resource("test-service", sample_service)

        assert _id == "test-service"
        assert result == sample_service
        pagerduty_resource.config.destination_client.post.assert_called_once_with(
            "/api/v1/integration/pagerduty/configuration/services",
            sample_service,
        )

    @pytest.mark.asyncio
    async def test_create_resource_existing_service_updates(self, pagerduty_resource, sample_service):
        """Test create_resource updates when service already exists."""
        existing_service = {"service_name": "test-service", "service_key": "old-key"}
        pagerduty_resource.destination_services = {"test-service": existing_service}
        pagerduty_resource.config.state.destination["pagerduty_integration"] = {}
        pagerduty_resource.config.destination_client = AsyncMock()
        pagerduty_resource.config.destination_client.put.return_value = sample_service

        _id, result = await pagerduty_resource.create_resource("test-service", sample_service)

        assert _id == "test-service"
        # Should have called PUT (update) instead of POST (create)
        pagerduty_resource.config.destination_client.post.assert_not_called()
        pagerduty_resource.config.destination_client.put.assert_called_once()


class TestUpdateResource:
    """Tests for update_resource method."""

    @pytest.mark.asyncio
    async def test_update_resource(self, pagerduty_resource, sample_service):
        """Test update_resource updates existing service."""
        pagerduty_resource.config.state.destination["pagerduty_integration"] = {
            "test-service": {"service_name": "test-service"}
        }
        pagerduty_resource.config.destination_client = AsyncMock()
        pagerduty_resource.config.destination_client.put.return_value = sample_service

        _id, result = await pagerduty_resource.update_resource("test-service", sample_service)

        assert _id == "test-service"
        assert result == sample_service
        pagerduty_resource.config.destination_client.put.assert_called_once_with(
            "/api/v1/integration/pagerduty/configuration/services/test-service",
            sample_service,
        )


class TestDeleteResource:
    """Tests for delete_resource method."""

    @pytest.mark.asyncio
    async def test_delete_resource(self, pagerduty_resource):
        """Test delete_resource deletes service."""
        pagerduty_resource.config.state.destination["pagerduty_integration"] = {
            "test-service": {"service_name": "test-service"}
        }
        pagerduty_resource.config.destination_client = AsyncMock()

        await pagerduty_resource.delete_resource("test-service")

        pagerduty_resource.config.destination_client.delete.assert_called_once_with(
            "/api/v1/integration/pagerduty/configuration/services/test-service"
        )


class TestPrivateGetDestinationServices:
    """Tests for _get_destination_services method."""

    @pytest.mark.asyncio
    async def test_private_get_destination_services(self, pagerduty_resource, sample_service_list):
        """Test _get_destination_services returns dict keyed by service_name."""
        pagerduty_resource.config.destination_client = AsyncMock()
        pagerduty_resource.config.destination_client.get.return_value = {"services": sample_service_list}

        result = await pagerduty_resource._get_destination_services()

        assert len(result) == 2
        assert "test-service" in result
        assert "another-service" in result
        assert result["test-service"]["service_key"] == "test-key-12345"
