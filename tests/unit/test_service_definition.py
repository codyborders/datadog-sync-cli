# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""Unit tests for ServiceDefinition resource."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from datadog_sync.model.service_definition import ServiceDefinition, _remaining_func


class TestRemainingFunc:
    """Tests for the pagination remaining function."""

    def test_remaining_func_with_more_pages(self):
        """Test remaining calculation when more pages exist."""
        resp = {"meta": {"page": {"total_count": 250}}}
        result = _remaining_func(idx=0, resp=resp, page_size=100, page_number=0)
        assert result == 150

    def test_remaining_func_last_page(self):
        """Test remaining calculation on last page."""
        resp = {"meta": {"page": {"total_count": 250}}}
        result = _remaining_func(idx=2, resp=resp, page_size=100, page_number=2)
        assert result == 0

    def test_remaining_func_empty_response(self):
        """Test remaining calculation with empty metadata."""
        resp = {}
        result = _remaining_func(idx=0, resp=resp, page_size=100, page_number=0)
        assert result == 0

    def test_remaining_func_exact_page_boundary(self):
        """Test remaining calculation at exact page boundary."""
        resp = {"meta": {"page": {"total_count": 200}}}
        result = _remaining_func(idx=1, resp=resp, page_size=100, page_number=1)
        assert result == 0


class TestServiceDefinition:
    """Tests for ServiceDefinition resource class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration object."""
        config = MagicMock()
        config.source_client = AsyncMock()
        config.destination_client = AsyncMock()
        config.state = MagicMock()
        config.state.source = {"service_definition": {}}
        config.state.destination = {"service_definition": {}}
        config.logger = MagicMock()
        return config

    @pytest.fixture
    def service_definition(self, mock_config):
        """Create a ServiceDefinition instance with mock config."""
        sd = ServiceDefinition(mock_config)
        return sd

    def test_resource_type(self, service_definition):
        """Test resource_type is set correctly."""
        assert service_definition.resource_type == "service_definition"

    def test_base_path(self, service_definition):
        """Test API base path is correct."""
        assert (
            service_definition.resource_config.base_path
            == "/api/v2/services/definitions"
        )

    def test_get_service_name_v2_schema(self, service_definition):
        """Test extracting service name from v2/v2.1/v2.2 schema format."""
        resource = {
            "attributes": {"schema": {"dd-service": "my-service", "team": "my-team"}}
        }
        result = service_definition._get_service_name(resource)
        assert result == "my-service"

    def test_get_service_name_v3_schema(self, service_definition):
        """Test extracting service name from v3 schema format."""
        resource = {
            "attributes": {"schema": {"name": "my-service-v3", "kind": "service"}}
        }
        result = service_definition._get_service_name(resource)
        assert result == "my-service-v3"

    def test_get_service_name_direct_schema(self, service_definition):
        """Test extracting service name from direct schema format."""
        resource = {"dd-service": "direct-service", "team": "my-team"}
        result = service_definition._get_service_name(resource)
        assert result == "direct-service"

    def test_get_service_name_fallback_to_id(self, service_definition):
        """Test falling back to id when service name not found."""
        resource = {"id": "fallback-id", "type": "service-definition"}
        result = service_definition._get_service_name(resource)
        assert result == "fallback-id"

    def test_extract_schema_data_from_wrapped_response(self, service_definition):
        """Test extracting schema from wrapped API response format."""
        resource = {
            "attributes": {
                "schema": {
                    "dd-service": "my-service",
                    "team": "my-team",
                    "contacts": [],
                }
            },
            "type": "service-definition",
        }
        result = service_definition._extract_schema_data(resource)
        assert result == {"dd-service": "my-service", "team": "my-team", "contacts": []}

    def test_extract_schema_data_from_direct_schema(self, service_definition):
        """Test extracting schema when resource is already a schema."""
        resource = {"dd-service": "my-service", "team": "my-team"}
        result = service_definition._extract_schema_data(resource)
        assert result == resource

    @pytest.mark.asyncio
    async def test_import_resource_with_id(self, service_definition, mock_config):
        """Test importing resource by service name."""
        mock_response = {
            "data": {
                "attributes": {
                    "schema": {"dd-service": "test-service", "team": "backend"}
                }
            }
        }
        mock_config.source_client.get.return_value = mock_response

        service_name, resource = await service_definition.import_resource(
            _id="test-service"
        )

        assert service_name == "test-service"
        assert resource == mock_response["data"]
        mock_config.source_client.get.assert_called_once_with(
            "/api/v2/services/definitions/test-service"
        )

    @pytest.mark.asyncio
    async def test_import_resource_with_resource(self, service_definition):
        """Test importing resource with pre-fetched data."""
        resource = {
            "attributes": {
                "schema": {"dd-service": "prefetched-service", "team": "platform"}
            }
        }

        service_name, result = await service_definition.import_resource(
            resource=resource
        )

        assert service_name == "prefetched-service"
        assert result == resource

    @pytest.mark.asyncio
    async def test_create_resource_new(self, service_definition, mock_config):
        """Test creating a new service definition."""
        service_definition.destination_service_definitions = {}

        resource = {
            "attributes": {"schema": {"dd-service": "new-service", "team": "frontend"}}
        }

        mock_response = {"data": [resource]}
        mock_config.destination_client.post.return_value = mock_response

        service_name, result = await service_definition.create_resource(
            "new-service", resource
        )

        assert service_name == "new-service"
        mock_config.destination_client.post.assert_called_once_with(
            "/api/v2/services/definitions",
            {"dd-service": "new-service", "team": "frontend"},
        )

    @pytest.mark.asyncio
    async def test_create_resource_existing_triggers_update(
        self, service_definition, mock_config
    ):
        """Test creating resource that exists at destination triggers update."""
        existing_resource = {
            "attributes": {
                "schema": {"dd-service": "existing-service", "team": "old-team"}
            }
        }
        service_definition.destination_service_definitions = {
            "existing-service": existing_resource
        }

        resource = {
            "attributes": {
                "schema": {"dd-service": "existing-service", "team": "new-team"}
            }
        }

        mock_response = {"data": resource}
        mock_config.destination_client.post.return_value = mock_response

        service_name, result = await service_definition.create_resource(
            "existing-service", resource
        )

        assert service_name == "existing-service"
        # Verify state was updated with existing resource
        assert (
            mock_config.state.destination["service_definition"]["existing-service"]
            == existing_resource
        )

    @pytest.mark.asyncio
    async def test_update_resource(self, service_definition, mock_config):
        """Test updating an existing service definition."""
        resource = {
            "attributes": {
                "schema": {
                    "dd-service": "update-service",
                    "team": "updated-team",
                    "contacts": [{"type": "email", "contact": "test@example.com"}],
                }
            }
        }

        mock_response = {"data": resource}
        mock_config.destination_client.post.return_value = mock_response

        service_name, result = await service_definition.update_resource(
            "update-service", resource
        )

        assert service_name == "update-service"
        assert result == resource
        mock_config.destination_client.post.assert_called_once_with(
            "/api/v2/services/definitions",
            {
                "dd-service": "update-service",
                "team": "updated-team",
                "contacts": [{"type": "email", "contact": "test@example.com"}],
            },
        )

    @pytest.mark.asyncio
    async def test_delete_resource(self, service_definition, mock_config):
        """Test deleting a service definition."""
        mock_config.destination_client.delete.return_value = None

        await service_definition.delete_resource("delete-service")

        mock_config.destination_client.delete.assert_called_once_with(
            "/api/v2/services/definitions/delete-service"
        )

    @pytest.mark.asyncio
    async def test_pre_apply_hook_caches_destination(
        self, service_definition, mock_config
    ):
        """Test that pre_apply_hook caches destination service definitions."""
        mock_services = [
            {"attributes": {"schema": {"dd-service": "service-1"}}},
            {"attributes": {"schema": {"dd-service": "service-2"}}},
        ]

        # Mock the paginated_request to return a callable that returns mock services
        async def mock_paginated_get(*args, **kwargs):
            return mock_services

        mock_config.destination_client.paginated_request.return_value = (
            mock_paginated_get
        )

        await service_definition.pre_apply_hook()

        assert "service-1" in service_definition.destination_service_definitions
        assert "service-2" in service_definition.destination_service_definitions

    @pytest.mark.asyncio
    async def test_pre_resource_action_hook_does_nothing(self, service_definition):
        """Test that pre_resource_action_hook is a no-op."""
        # Should not raise any exceptions
        await service_definition.pre_resource_action_hook("test-id", {"test": "data"})

    def test_pagination_config(self, service_definition):
        """Test pagination configuration is set correctly."""
        assert service_definition.pagination_config.page_size == 100
        assert service_definition.pagination_config.remaining_func == _remaining_func


class TestServiceDefinitionIntegrationScenarios:
    """Tests for common integration scenarios."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration object."""
        config = MagicMock()
        config.source_client = AsyncMock()
        config.destination_client = AsyncMock()
        config.state = MagicMock()
        config.state.source = {"service_definition": {}}
        config.state.destination = {"service_definition": {}}
        config.logger = MagicMock()
        return config

    @pytest.fixture
    def service_definition(self, mock_config):
        """Create a ServiceDefinition instance with mock config."""
        return ServiceDefinition(mock_config)

    @pytest.mark.asyncio
    async def test_full_sync_flow_new_service(self, service_definition, mock_config):
        """Test full sync flow for a new service definition."""
        # Setup: service doesn't exist at destination
        service_definition.destination_service_definitions = {}

        source_resource = {
            "attributes": {
                "schema": {
                    "schema-version": "v2.1",
                    "dd-service": "new-api-service",
                    "team": "platform",
                    "contacts": [
                        {"type": "slack", "contact": "https://slack.com/channel"}
                    ],
                    "links": [
                        {
                            "name": "Runbook",
                            "type": "runbook",
                            "url": "https://example.com",
                        }
                    ],
                }
            },
            "type": "service-definition",
        }

        mock_response = {"data": [source_resource]}
        mock_config.destination_client.post.return_value = mock_response

        # Execute
        service_name, result = await service_definition.create_resource(
            "new-api-service", source_resource
        )

        # Verify
        assert service_name == "new-api-service"
        mock_config.destination_client.post.assert_called_once()
        call_args = mock_config.destination_client.post.call_args
        assert call_args[0][0] == "/api/v2/services/definitions"
        # Verify schema was extracted properly
        posted_schema = call_args[0][1]
        assert posted_schema["dd-service"] == "new-api-service"
        assert posted_schema["team"] == "platform"

    @pytest.mark.asyncio
    async def test_v3_schema_support(self, service_definition):
        """Test support for v3 schema format which uses 'name' instead of 'dd-service'."""
        v3_resource = {
            "attributes": {
                "schema": {
                    "apiVersion": "v3",
                    "kind": "service",
                    "metadata": {"name": "v3-service-name"},
                    "name": "v3-service-name",
                }
            }
        }

        service_name = service_definition._get_service_name(v3_resource)
        assert service_name == "v3-service-name"
