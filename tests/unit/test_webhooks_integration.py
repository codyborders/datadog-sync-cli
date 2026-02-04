# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""Unit tests for WebhooksIntegration resource."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from datadog_sync.model.webhooks_integration import WebhooksIntegration
from datadog_sync.utils.resource_utils import CustomClientHTTPError


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = MagicMock()
    config.source_client = AsyncMock()
    config.destination_client = AsyncMock()
    config.logger = MagicMock()
    config.state = MagicMock()
    config.state.source = {"webhooks_integration": {}}
    config.state.destination = {"webhooks_integration": {}}
    return config


@pytest.fixture
def webhooks_integration(mock_config):
    """Create a WebhooksIntegration instance for testing."""
    return WebhooksIntegration(mock_config)


@pytest.fixture
def sample_webhook():
    """Create a sample webhook resource."""
    return {
        "name": "test-webhook",
        "url": "https://example.com/webhook",
        "custom_headers": '{"Authorization": "Bearer token"}',
        "payload": '{"event": "$EVENT_TITLE"}',
        "encode_as": "json",
    }


class TestWebhooksIntegration:
    """Tests for WebhooksIntegration class."""

    def test_resource_type(self, webhooks_integration):
        """Test that resource_type is correctly set."""
        assert webhooks_integration.resource_type == "webhooks_integration"

    def test_resource_config_base_path(self, webhooks_integration):
        """Test that base_path is correctly configured."""
        assert webhooks_integration.resource_config.base_path == "/api/v1/integration/webhooks/configuration/webhooks"

    @pytest.mark.asyncio
    async def test_get_resources_returns_empty_list(self, webhooks_integration, mock_config):
        """Test that get_resources returns an empty list since API doesn't support listing."""
        result = await webhooks_integration.get_resources(mock_config.source_client)
        assert result == []
        mock_config.logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_resource_with_id(self, webhooks_integration, mock_config, sample_webhook):
        """Test importing a webhook by ID (name)."""
        mock_config.source_client.get.return_value = sample_webhook

        result = await webhooks_integration.import_resource(_id="test-webhook")

        assert result == ("test-webhook", sample_webhook)
        mock_config.source_client.get.assert_called_once_with(
            "/api/v1/integration/webhooks/configuration/webhooks/test-webhook"
        )

    @pytest.mark.asyncio
    async def test_import_resource_with_resource(self, webhooks_integration, sample_webhook):
        """Test importing a webhook with pre-fetched resource data."""
        result = await webhooks_integration.import_resource(resource=sample_webhook)

        assert result == ("test-webhook", sample_webhook)

    @pytest.mark.asyncio
    async def test_create_resource_new_webhook(self, webhooks_integration, mock_config, sample_webhook):
        """Test creating a new webhook at the destination."""
        webhooks_integration.destination_webhooks = {}
        mock_config.destination_client.post.return_value = sample_webhook

        result = await webhooks_integration.create_resource("test-webhook", sample_webhook)

        assert result == ("test-webhook", sample_webhook)
        mock_config.destination_client.post.assert_called_once_with(
            "/api/v1/integration/webhooks/configuration/webhooks",
            sample_webhook,
        )

    @pytest.mark.asyncio
    async def test_create_resource_existing_webhook(self, webhooks_integration, mock_config, sample_webhook):
        """Test that creating an existing webhook triggers an update."""
        webhooks_integration.destination_webhooks = {"test-webhook": sample_webhook}
        mock_config.state.destination = {"webhooks_integration": {"test-webhook": sample_webhook}}
        mock_config.destination_client.put.return_value = sample_webhook

        result = await webhooks_integration.create_resource("test-webhook", sample_webhook)

        assert result == ("test-webhook", sample_webhook)
        mock_config.destination_client.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_resource(self, webhooks_integration, mock_config, sample_webhook):
        """Test updating an existing webhook."""
        mock_config.state.destination = {"webhooks_integration": {"test-webhook": sample_webhook}}
        updated_webhook = {**sample_webhook, "url": "https://example.com/updated"}
        mock_config.destination_client.put.return_value = updated_webhook

        result = await webhooks_integration.update_resource("test-webhook", sample_webhook)

        assert result == ("test-webhook", updated_webhook)
        mock_config.destination_client.put.assert_called_once_with(
            "/api/v1/integration/webhooks/configuration/webhooks/test-webhook",
            sample_webhook,
        )

    @pytest.mark.asyncio
    async def test_delete_resource(self, webhooks_integration, mock_config, sample_webhook):
        """Test deleting a webhook."""
        mock_config.state.destination = {"webhooks_integration": {"test-webhook": sample_webhook}}
        mock_config.destination_client.delete.return_value = None

        await webhooks_integration.delete_resource("test-webhook")

        mock_config.destination_client.delete.assert_called_once_with(
            "/api/v1/integration/webhooks/configuration/webhooks/test-webhook"
        )

    @pytest.mark.asyncio
    async def test_pre_resource_action_hook(self, webhooks_integration, sample_webhook):
        """Test that pre_resource_action_hook completes without error."""
        # Should not raise any exceptions
        await webhooks_integration.pre_resource_action_hook("test-webhook", sample_webhook)

    @pytest.mark.asyncio
    async def test_pre_apply_hook(self, webhooks_integration, mock_config, sample_webhook):
        """Test that pre_apply_hook fetches destination webhooks."""
        mock_config.state.destination = {"webhooks_integration": {"test-webhook": sample_webhook}}
        mock_config.state.source = {"webhooks_integration": {}}
        mock_config.destination_client.get.return_value = sample_webhook

        await webhooks_integration.pre_apply_hook()

        assert "test-webhook" in webhooks_integration.destination_webhooks

    @pytest.mark.asyncio
    async def test_private_get_destination_webhooks_not_found(self, webhooks_integration, mock_config, sample_webhook):
        """Test _get_destination_webhooks handles 404 errors gracefully."""
        mock_config.state.destination = {"webhooks_integration": {"test-webhook": sample_webhook}}
        mock_config.state.source = {"webhooks_integration": {}}

        # Create a mock exception with status_code attribute
        mock_error = MagicMock(spec=CustomClientHTTPError)
        mock_error.status_code = 404
        mock_config.destination_client.get.side_effect = mock_error

        result = await webhooks_integration._get_destination_webhooks()

        assert result == {}
        mock_config.logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_private_get_destination_webhooks_other_error(
        self, webhooks_integration, mock_config, sample_webhook
    ):
        """Test _get_destination_webhooks logs warnings for non-404 errors."""
        mock_config.state.destination = {"webhooks_integration": {"test-webhook": sample_webhook}}
        mock_config.state.source = {"webhooks_integration": {}}

        # Create a mock exception with status_code attribute
        mock_error = MagicMock(spec=CustomClientHTTPError)
        mock_error.status_code = 500
        mock_config.destination_client.get.side_effect = mock_error

        result = await webhooks_integration._get_destination_webhooks()

        assert result == {}
        mock_config.logger.warning.assert_called()


class TestWebhooksIntegrationResourceConfig:
    """Tests for WebhooksIntegration ResourceConfig."""

    def test_excluded_attributes_empty(self, webhooks_integration):
        """Test that excluded_attributes is properly configured."""
        # excluded_attributes may be None or empty list after processing
        assert (
            webhooks_integration.resource_config.excluded_attributes is None
            or webhooks_integration.resource_config.excluded_attributes == []
        )

    def test_concurrent_default(self, webhooks_integration):
        """Test that concurrent is set to default True."""
        assert webhooks_integration.resource_config.concurrent is True
