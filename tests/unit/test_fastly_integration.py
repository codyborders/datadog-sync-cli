# Unless explicitly stated otherwise all files in this repository are licensed
# under the 3-clause BSD style license (see LICENSE).
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2019 Datadog, Inc.

"""Unit tests for the Fastly Integration resource."""

import pytest

from datadog_sync.model.fastly_integration import FastlyIntegration
from datadog_sync.utils.filter import process_filters


class TestFastlyIntegrationResource:
    """Tests for FastlyIntegration resource class."""

    def test_resource_type(self, config):
        """Test that resource_type is correctly set."""
        resource = FastlyIntegration(config)
        assert resource.resource_type == "fastly_integration"

    def test_resource_config_base_path(self, config):
        """Test that base_path is correctly configured."""
        resource = FastlyIntegration(config)
        assert resource.resource_config.base_path == "/api/v2/integrations/fastly/accounts"

    def test_resource_config_excluded_attributes(self, config):
        """Test that excluded_attributes contains id."""
        resource = FastlyIntegration(config)
        # The excluded_attributes are converted to deepdiff format in __post_init__
        assert "root['id']" in resource.resource_config.excluded_attributes

    def test_resource_config_concurrent_default(self, config):
        """Test that concurrent is True by default."""
        resource = FastlyIntegration(config)
        assert resource.resource_config.concurrent is True


class TestFastlyIntegrationFilters:
    """Tests for FastlyIntegration filter functionality."""

    @pytest.mark.parametrize(
        "_filter, r_obj, expected",
        [
            # Filter by account name - exact match
            (
                ["Type=fastly_integration;Name=attributes.name;Value=my-fastly-account"],
                {"attributes": {"name": "my-fastly-account", "api_key": "test-key"}},
                True,
            ),
            # Filter by account name - no match
            (
                ["Type=fastly_integration;Name=attributes.name;Value=my-fastly-account"],
                {"attributes": {"name": "other-account", "api_key": "test-key"}},
                False,
            ),
            # Filter by account name - substring match
            (
                ["Type=fastly_integration;Name=attributes.name;Value=fastly;Operator=SubString"],
                {"attributes": {"name": "my-fastly-account", "api_key": "test-key"}},
                True,
            ),
            # Filter by account name - Not operator (inverse)
            (
                ["Type=fastly_integration;Name=attributes.name;Value=other-account;Operator=Not"],
                {"attributes": {"name": "my-fastly-account", "api_key": "test-key"}},
                True,
            ),
            # Filter on nested services list
            (
                ["Type=fastly_integration;Name=attributes.services;Value=service-123"],
                {"attributes": {"name": "my-account", "services": ["service-123", "service-456"]}},
                True,
            ),
            # Filter on nested services list - no match
            (
                ["Type=fastly_integration;Name=attributes.services;Value=service-789"],
                {"attributes": {"name": "my-account", "services": ["service-123", "service-456"]}},
                False,
            ),
        ],
    )
    def test_fastly_integration_filters(self, config, _filter, r_obj, expected):
        """Test filter functionality for fastly_integration resources."""
        config.filters = process_filters(_filter)
        config.filter_operator = "OR"
        resource = FastlyIntegration(config)

        assert resource.filter(r_obj) == expected

    @pytest.mark.parametrize(
        "_filter, r_obj, expected",
        [
            # Multiple filters with AND operator - both match
            (
                [
                    "Type=fastly_integration;Name=attributes.name;Value=my-fastly;Operator=SubString",
                    "Type=fastly_integration;Name=attributes.services;Value=service-123",
                ],
                {"attributes": {"name": "my-fastly-account", "services": ["service-123"]}},
                True,
            ),
            # Multiple filters with AND operator - only one matches
            (
                [
                    "Type=fastly_integration;Name=attributes.name;Value=my-fastly;Operator=SubString",
                    "Type=fastly_integration;Name=attributes.services;Value=service-999",
                ],
                {"attributes": {"name": "my-fastly-account", "services": ["service-123"]}},
                False,
            ),
        ],
    )
    def test_fastly_integration_filters_and_operator(self, config, _filter, r_obj, expected):
        """Test filter functionality with AND operator."""
        config.filters = process_filters(_filter)
        config.filter_operator = "AND"
        resource = FastlyIntegration(config)

        assert resource.filter(r_obj) == expected
