"""Tests for the NMEA2000Sensor entity."""
from datetime import timedelta
from unittest.mock import patch, MagicMock

from custom_components.nmea2000.NMEA2000Sensor import NMEA2000Sensor


async def test_sensor_init_numeric(hass):
    """Test sensor initialization with numeric state."""
    sensor = NMEA2000Sensor(
        id="test_sensor",
        friendly_name="Temperature",
        initial_state=25.5,
        unit_of_measurement="°C",
        device_name="Test Device",
    )
    assert sensor.native_value == 25.5
    assert sensor._attr_name == "Temperature"
    assert sensor._attr_unique_id == "test_sensor"
    assert sensor.available is True


async def test_sensor_init_string(hass):
    """Test sensor initialization with string state."""
    sensor = NMEA2000Sensor(
        id="test_state",
        friendly_name="Status",
        initial_state="Running",
        device_name="Test Device",
    )
    assert sensor.native_value == "Running"
    assert sensor.available is True


async def test_sensor_init_none_unavailable(hass):
    """Test sensor with None initial state is unavailable."""
    sensor = NMEA2000Sensor(
        id="test_null",
        friendly_name="Empty",
        initial_state=None,
        device_name="Test Device",
    )
    assert sensor.available is False


async def test_sensor_str_repr(hass):
    """Test sensor string representation."""
    sensor = NMEA2000Sensor(
        id="test_repr",
        friendly_name="Wind Speed",
        initial_state=12.3,
        unit_of_measurement="kts",
        device_name="Gateway",
    )
    s = str(sensor)
    assert "Wind Speed" in s
    assert "12.3" in s


async def test_sensor_set_state_not_ready(hass):
    """Test set_state does nothing when sensor is not ready."""
    sensor = NMEA2000Sensor(
        id="test_not_ready",
        friendly_name="Test",
        initial_state=0,
        device_name="Device",
    )
    sensor.set_state(42)
    # Should not update because _ready is False (never added to hass)
    assert sensor.native_value == 0


async def test_sensor_set_state_ready(hass):
    """Test set_state updates value when sensor is ready."""
    sensor = NMEA2000Sensor(
        id="test_ready",
        friendly_name="Test",
        initial_state=0,
        device_name="Device",
    )
    sensor._ready = True
    sensor.async_schedule_update_ha_state = MagicMock()
    sensor.set_state(42)
    assert sensor.native_value == 42


async def test_sensor_update_availability_not_ready(hass):
    """Test update_availability does nothing when not ready."""
    sensor = NMEA2000Sensor(
        id="test_avail",
        friendly_name="Test",
        initial_state=0,
        device_name="Device",
    )
    # Should not crash
    sensor.update_availability()


async def test_sensor_via_device(hass):
    """Test sensor with via_device creates proper device info."""
    sensor = NMEA2000Sensor(
        id="test_via",
        friendly_name="Test",
        initial_state=0,
        device_name="SubDevice",
        via_device="MainGateway",
    )
    assert sensor._attr_device_info is not None


async def test_sensor_custom_update_frequency(hass):
    """Test sensor with custom update frequency."""
    freq = timedelta(seconds=10)
    sensor = NMEA2000Sensor(
        id="test_freq",
        friendly_name="Test",
        initial_state=0,
        device_name="Device",
        update_frequncy=freq,
    )
    assert sensor.update_frequncy == freq


async def test_sensor_custom_ttl(hass):
    """Test sensor with custom TTL."""
    ttl = timedelta(seconds=30)
    sensor = NMEA2000Sensor(
        id="test_ttl",
        friendly_name="Test",
        initial_state=0,
        device_name="Device",
        ttl=ttl,
    )
    # TTL is multiplied by UNAVAILABLE_FACTOR (10)
    assert sensor.ttl == ttl * 10
