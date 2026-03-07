"""Fixtures for ha-nmea2000 tests."""
import pytest
from unittest.mock import patch

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield


@pytest.fixture(autouse=True)
def bypass_setup_entry():
    """Prevent async_setup_entry from running during config flow tests."""
    with patch(
        "custom_components.nmea2000.async_setup_entry", return_value=True
    ):
        yield

