from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.device_registry import DeviceInfo
import logging
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_UPDATE_INTERVAL = timedelta(minutes=5)
INFINITE_DURATION = timedelta(days=10**6)
UNAVAILABLE_FACTOR = 3

# SmartSensor class representing a basic sensor entity with state
class NMEA2000Sensor(SensorEntity):
    """Representation of a NMEA2000 sensor."""
    _attr_should_poll = False

    def __init__(
        self,
        id: str,
        friendly_name: str,
        initial_state,
        unit_of_measurement: str | None = None,
        device_name: str | None = None,
        via_device: str | None = None,
        update_frequncy: timedelta | None = None,
        ttl: timedelta | None = None,
        manufacturer: str | None = None
    ) -> None:
        """Initialize the sensor."""
        _LOGGER.info("Initializing NMEA2000Sensor: name=%s, friendly_name=%s, initial_state: %s, unit_of_measurement=%s, device_name=%s, via_device=%s, update_frequncy=%s, ttl=%s",
                      id, friendly_name, initial_state, unit_of_measurement, device_name, via_device, update_frequncy, ttl)
        self._attr_unique_id = id.lower().replace(" ", "_")
        self.entity_id = f"sensor.{self._attr_unique_id}"
        self._attr_name = friendly_name
        self._device_name = device_name
        self._attr_native_value = initial_state
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_name)},
            manufacturer=manufacturer if manufacturer is not None else "NMEA 2000",
            model=device_name,
            name=device_name,
            via_device=((DOMAIN, via_device) if via_device is not None else None))
        self._last_updated = self._last_seen = datetime.now()
        self.update_frequncy = DEFAULT_UPDATE_INTERVAL if update_frequncy is None else update_frequncy
        self.ttl = INFINITE_DURATION if ttl is None else ttl*UNAVAILABLE_FACTOR
            
        if initial_state is None or initial_state == "":
            self._available = False
            _LOGGER.info("Creating sensor: '%s' as unavailable", self._attr_name)
        else:
            self._available = True

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._attr_native_value

    @property
    def last_updated(self):
        """Return the last updated timestamp of the sensor."""
        return self._last_updated

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        return self._available

    def update_availability(self):
        """Update the availability status of the sensor."""
        
        new_availability = (datetime.now() - self._last_seen) < self.ttl

        if self._available != new_availability:
            _LOGGER.warning("Setting sensor:'%s' as unavailable", self._attr_name)
            self._available = new_availability
            self.async_schedule_update_ha_state()

    def set_state(self, new_state, ignore_tracing = False):
        """Set the state of the sensor."""
        should_update = False
        now = datetime.now()
        old_state = self._attr_native_value
        self._attr_native_value = new_state
        self._last_seen = now

        if not self._available:
            self._available = True
            should_update = True
            if not ignore_tracing:
                _LOGGER.info("Setting sensor:'%s' as available", self._attr_name)

        if (not should_update) and (now - self._last_updated) < self.update_frequncy:
            # If the update frequency is not met, bail out without any changes
            _LOGGER.debug("Skipping update for sensor:'%s' as of update frequency", self._attr_name)
            return
        
        if new_state != old_state:
            # Since the state is valid, update the sensor's state
            if not ignore_tracing:
                _LOGGER.info("Setting state for sensor: '%s' to %s", self._attr_name, new_state)
            should_update = True

        if should_update:
            self._last_updated = now
            self.async_schedule_update_ha_state()
