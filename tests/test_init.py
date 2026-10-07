"""Tests for NMEA 2000 integration setup."""

from unittest.mock import MagicMock

from custom_components.nmea2000 import async_remove_config_entry_device


async def test_remove_config_entry_device(hass):
    """Integration devices can be removed."""
    assert await async_remove_config_entry_device(hass, MagicMock(), MagicMock())
