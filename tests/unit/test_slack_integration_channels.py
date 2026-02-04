# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""Unit tests for the Slack Integration Channels resource."""

import pytest

from datadog_sync.model.slack_integration_channels import SlackIntegrationChannels
from datadog_sync.utils.filter import process_filters


class TestSlackIntegrationChannelsResource:
    """Tests for SlackIntegrationChannels resource class."""

    def test_resource_type(self, config):
        """Test that resource_type is correctly set."""
        resource = SlackIntegrationChannels(config)
        assert resource.resource_type == "slack_integration_channels"

    def test_resource_config_base_path(self, config):
        """Test that base_path is correctly configured."""
        resource = SlackIntegrationChannels(config)
        assert resource.resource_config.base_path == "/api/v1/integration/slack/configuration/accounts"

    def test_resource_config_concurrent_default(self, config):
        """Test that concurrent is True by default."""
        resource = SlackIntegrationChannels(config)
        assert resource.resource_config.concurrent is True

    def test_get_composite_id(self, config):
        """Test composite ID generation from resource."""
        resource = SlackIntegrationChannels(config)
        channel = {
            "_account_name": "my-workspace",
            "channel_name": "#alerts",
            "display": {"message": True, "notified": True},
        }
        composite_id = resource._get_composite_id(channel)
        assert composite_id == "my-workspace:#alerts"

    def test_get_composite_id_with_name_field(self, config):
        """Test composite ID generation when channel uses 'name' instead of 'channel_name'."""
        resource = SlackIntegrationChannels(config)
        channel = {
            "_account_name": "my-workspace",
            "name": "#alerts",
            "display": {"message": True},
        }
        composite_id = resource._get_composite_id(channel)
        assert composite_id == "my-workspace:#alerts"

    def test_parse_composite_id(self, config):
        """Test parsing composite ID into account_name and channel_name."""
        resource = SlackIntegrationChannels(config)
        account_name, channel_name = resource._parse_composite_id("my-workspace:#alerts")
        assert account_name == "my-workspace"
        assert channel_name == "#alerts"

    def test_parse_composite_id_with_colon_in_channel(self, config):
        """Test parsing composite ID when channel name contains colon."""
        resource = SlackIntegrationChannels(config)
        account_name, channel_name = resource._parse_composite_id("workspace:#channel:with:colons")
        assert account_name == "workspace"
        assert channel_name == "#channel:with:colons"

    def test_parse_composite_id_no_colon(self, config):
        """Test parsing composite ID when no colon present (edge case)."""
        resource = SlackIntegrationChannels(config)
        account_name, channel_name = resource._parse_composite_id("just-channel-name")
        assert account_name == ""
        assert channel_name == "just-channel-name"

    def test_prepare_payload_removes_account_name(self, config):
        """Test that _prepare_payload removes the internal _account_name field."""
        resource = SlackIntegrationChannels(config)
        channel = {
            "_account_name": "my-workspace",
            "channel_name": "#alerts",
            "display": {"message": True, "notified": True},
        }
        payload = resource._prepare_payload(channel)
        assert "_account_name" not in payload
        assert payload["channel_name"] == "#alerts"
        assert payload["display"]["message"] is True


class TestSlackIntegrationChannelsFilters:
    """Tests for SlackIntegrationChannels filter functionality."""

    @pytest.mark.parametrize(
        "_filter, r_obj, expected",
        [
            # Filter by channel_name - exact match
            (
                ["Type=slack_integration_channels;Name=channel_name;Value=#alerts"],
                {"_account_name": "workspace", "channel_name": "#alerts", "display": {"message": True}},
                True,
            ),
            # Filter by channel_name - no match
            (
                ["Type=slack_integration_channels;Name=channel_name;Value=#alerts"],
                {"_account_name": "workspace", "channel_name": "#general", "display": {"message": True}},
                False,
            ),
            # Filter by channel_name - substring match
            (
                ["Type=slack_integration_channels;Name=channel_name;Value=alert;Operator=SubString"],
                {"_account_name": "workspace", "channel_name": "#alerts-critical", "display": {"message": True}},
                True,
            ),
            # Filter by account name
            (
                ["Type=slack_integration_channels;Name=_account_name;Value=production-workspace"],
                {"_account_name": "production-workspace", "channel_name": "#alerts", "display": {"message": True}},
                True,
            ),
            # Filter by account name - no match
            (
                ["Type=slack_integration_channels;Name=_account_name;Value=production-workspace"],
                {"_account_name": "staging-workspace", "channel_name": "#alerts", "display": {"message": True}},
                False,
            ),
            # Filter by display.message setting
            (
                ["Type=slack_integration_channels;Name=display.message;Value=True"],
                {"_account_name": "workspace", "channel_name": "#alerts", "display": {"message": True}},
                True,
            ),
            # Filter by channel_name - Not operator (inverse)
            (
                ["Type=slack_integration_channels;Name=channel_name;Value=#general;Operator=Not"],
                {"_account_name": "workspace", "channel_name": "#alerts", "display": {"message": True}},
                True,
            ),
        ],
    )
    def test_slack_integration_channels_filters(self, config, _filter, r_obj, expected):
        """Test filter functionality for slack_integration_channels resources."""
        config.filters = process_filters(_filter)
        config.filter_operator = "OR"
        resource = SlackIntegrationChannels(config)

        assert resource.filter(r_obj) == expected

    @pytest.mark.parametrize(
        "_filter, r_obj, expected",
        [
            # Multiple filters with AND operator - both match
            (
                [
                    "Type=slack_integration_channels;Name=_account_name;Value=production;Operator=SubString",
                    "Type=slack_integration_channels;Name=channel_name;Value=#alerts",
                ],
                {"_account_name": "production-workspace", "channel_name": "#alerts", "display": {"message": True}},
                True,
            ),
            # Multiple filters with AND operator - only one matches
            (
                [
                    "Type=slack_integration_channels;Name=_account_name;Value=production;Operator=SubString",
                    "Type=slack_integration_channels;Name=channel_name;Value=#general",
                ],
                {"_account_name": "production-workspace", "channel_name": "#alerts", "display": {"message": True}},
                False,
            ),
            # Multiple filters with AND operator - filter by account and display settings
            (
                [
                    "Type=slack_integration_channels;Name=_account_name;Value=workspace",
                    "Type=slack_integration_channels;Name=display.notified;Value=True",
                ],
                {
                    "_account_name": "workspace",
                    "channel_name": "#alerts",
                    "display": {"message": True, "notified": True},
                },
                True,
            ),
        ],
    )
    def test_slack_integration_channels_filters_and_operator(self, config, _filter, r_obj, expected):
        """Test filter functionality with AND operator."""
        config.filters = process_filters(_filter)
        config.filter_operator = "AND"
        resource = SlackIntegrationChannels(config)

        assert resource.filter(r_obj) == expected
