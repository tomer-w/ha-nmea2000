from datetime import datetime
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorStateClass

import logging

_LOGGER = logging.getLogger(__name__)


# SmartSensor class representing a basic sensor entity with state
class NMEA2000Sensor(Entity):
    def __init__(
        self,
        name,
        friendly_name,
        initial_state,
        group=None,
        unit_of_measurement=None,
        device_name=None,
        sentence_type=None,
        instance_name=None,
    ):
        """Initialize the sensor."""
        _LOGGER.debug(f"Initializing sensor: {name} with state: {initial_state}")

        self._unique_id = name.lower().replace(" ", "_")
        self.entity_id = f"sensor.{self._unique_id}"
        self._name = friendly_name if friendly_name else self._unique_id
        self._state = initial_state
        self._group = group if group is not None else "Other"
        self._device_name = device_name
        self._sentence_type = sentence_type
        self._instance_name = instance_name
        self._unit_of_measurement = unit_of_measurement
        self._state_class = SensorStateClass.MEASUREMENT
        self._last_updated = datetime.now()
        if initial_state is None or initial_state == "":
            self._available = False
            _LOGGER.debug(f"Setting sensor: '{self._name}' with unavailable")
        else:
            self._available = True

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def device_info(self):
        """Return device information about this sensor."""
        return {
            "identifiers": {
                ("smart2000usb", f"{self._instance_name}_{self._device_name}")
            },
            "name": self._device_name,
            "manufacturer": self._group,
            "model": self._sentence_type,
        }

    @property
    def state_class(self):
        """Return the state class of the sensor."""
        return self._state_class

    @property
    def last_updated(self):
        """Return the last updated timestamp of the sensor."""
        return self._last_updated

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        return self._available

    @property
    def should_poll(self) -> bool:
        """Return the polling requirement for this sensor."""
        return False

    def update_availability(self):
        """Update the availability status of the sensor."""

        new_availability = (datetime.now() - self._last_updated) < datetime.timedelta(
            minutes=4
        )

        self._available = new_availability

        try:
            self.async_schedule_update_ha_state()
        except RuntimeError as re:
            if "Attribute hass is None" in str(re):
                pass  # Ignore this specific error
            else:
                _LOGGER.warning(
                    f"Could not update state for sensor '{self._name}': {re}"
                )
        except Exception as e:  # Catch all other exception types
            _LOGGER.warning(f"Could not update state for sensor '{self._name}': {e}")

    def set_state(self, new_state):
        """Set the state of the sensor."""

        if new_state is not None and new_state != "":
            # Since the state is valid, update the sensor's state and the last updated timestamp
            self._state = new_state
            self._available = True
            self._last_updated = datetime.now()
            _LOGGER.debug(f"Setting state for sensor: '{self._name}' to {new_state}")
        else:
            # For None or empty string, check the time since last valid update
            if self._last_updated and (
                datetime.now() - self._last_updated > datetime.timedelta(minutes=1)
            ):
                # It's been more than 1 minute since the last valid update
                self._available = False
                _LOGGER.debug(
                    f"Setting sensor:'{self._name}' as unavailable due to no valid update for over 1 minute"
                )
            else:
                # It's been less than 1 minute since the last valid update, keep the sensor available
                _LOGGER.debug(
                    f"Sensor:'{self._name}' remains available as it's less than 1 minute since last valid state"
                )

        try:
            self.async_schedule_update_ha_state()
        except RuntimeError as re:
            if "Attribute hass is None" in str(re):
                pass  # Ignore this specific error
            else:
                _LOGGER.warning(
                    f"Could not update state for sensor '{self._name}': {re}"
                )
        except Exception as e:  # Catch all other exception types
            _LOGGER.warning(f"Could not update state for sensor '{self._name}': {e}")
