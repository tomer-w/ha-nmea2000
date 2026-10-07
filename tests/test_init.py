"""Tests for NMEA 2000 integration setup."""

from homeassistant.const import EntityCategory
from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nmea2000 import async_remove_config_entry_device
from custom_components.nmea2000.const import DOMAIN


def _create_device(hass, entry, name: str) -> dr.DeviceEntry:
    """Create a device owned by the test config entry."""
    return dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, name)},
        name=name,
    )


async def test_remove_device_without_active_entities(hass):
    """A discovered device without active entities can be removed."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    device = _create_device(hass, entry, "Stale NMEA device")

    assert await async_remove_config_entry_device(hass, entry, device)


async def test_keep_device_with_active_entity(hass):
    """A discovered device with an active entity cannot be removed."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    device = _create_device(hass, entry, "Active NMEA device")
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        "active_sensor",
        config_entry=entry,
        device_id=device.id,
    )

    assert not await async_remove_config_entry_device(hass, entry, device)


async def test_remove_device_with_only_disabled_entities(hass):
    """A discovered device with only disabled entities can be removed."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    device = _create_device(hass, entry, "Disabled NMEA device")
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        "disabled_sensor",
        config_entry=entry,
        device_id=device.id,
        disabled_by=er.RegistryEntryDisabler.USER,
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    assert await async_remove_config_entry_device(hass, entry, device)


async def test_keep_gateway_without_active_entities(hass):
    """The integration gateway cannot be removed independently."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    device = _create_device(hass, entry, "NMEA 2000 Gateway")

    assert not await async_remove_config_entry_device(hass, entry, device)
