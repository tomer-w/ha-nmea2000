from __future__ import annotations
import logging
import asyncio
import hashlib
import contextlib
from typing import Dict
from datetime import timedelta

from .const import DOMAIN, CONF_MODE, CONF_PGN_INCLUDE, CONF_PGN_EXCLUDE, CONF_MODE_USB, CONF_MODE_TCP, CONF_SERIAL_PORT, CONF_BAUDRATE, CONF_IP, CONF_PORT
from .config_flow import parse_and_validate_comma_separated_integers
from .NMEA2000Sensor import NMEA2000Sensor

from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, EVENT_HOMEASSISTANT_START
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.exceptions import ConfigValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback


from nmea2000 import NMEA2000Message, TcpNmea2000Gateway, UsbNmea2000Gateway, FieldTypes, State

_LOGGER = logging.getLogger(__name__)

async def event_wait(evt, timeout):
    # suppress TimeoutError because we'll return False in case of timeout
    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(evt.wait(), timeout)
    return evt.is_set()


class Hub:

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """NMEA2000 Hub. Set up the NMEA2000 sensor platform from a config entry."""
        self.hass = hass
        self.entry = entry
        self.stop_event = asyncio.Event()
        self.state = "Initializing"
        self.async_add_entities = None
        self.sensors = {}

        # Retrieve configuration from entry
        self.name = entry.data[CONF_NAME]
        mode = entry.data[CONF_MODE]
        self.device_name = f"NMEA 2000 {mode} Gateway"

        self.state_sensor = NMEA2000Sensor("state", "State", self.state, None, self.device_name, None)
        self.msg_per_minute_sensor = NMEA2000Sensor("messages_per_minute", "Messages per minute", 0, None, self.device_name, None)

        pgn_include = parse_and_validate_comma_separated_integers(
            entry.data.get(CONF_PGN_INCLUDE, "")
        )
        pgn_exclude = parse_and_validate_comma_separated_integers(
            entry.data.get(CONF_PGN_EXCLUDE, "")
        )

        _LOGGER.info(
            "Configuring sensor with name: %s, mode: %s, PGN Include: %s, PGN Exclude: %s",
            self.name,
            mode,
            pgn_include,
            pgn_exclude,
        )

        if mode == CONF_MODE_USB:
            serial_port = entry.data[CONF_SERIAL_PORT]
            baudrate = entry.data[CONF_BAUDRATE]
            _LOGGER.info(
                "USB sensor with name: %s, serial_port: %s, baudrate: %s",
                self.name,
                serial_port,
                baudrate,
            )
            self.gateway = UsbNmea2000Gateway(serial_port, exclude_pgns=pgn_exclude, include_pgns=pgn_include)
            url = f"usb://{serial_port}"
        elif mode == "TCP":
            ip = entry.data[CONF_IP]
            port = entry.data[CONF_PORT]
            _LOGGER.info("TCP sensor with name: %s, IP: %s, port: %s", name, ip, port)
            self.gateway = TcpNmea2000Gateway(ip, port, exclude_pgns=pgn_exclude, include_pgns=pgn_include)
            url = f"tcp://{ip}:{port}"
        else:
            raise ConfigValidationError(f"mode {mode} not supported")

        self.gateway.set_receive_callback(self.receive_callback)
        self.gateway.set_status_callback(self.status_callback)

        if hass.is_running:
           entry.async_create_task(self.hass, self.start(None))
        else:
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, self.start)
        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.stop)

    def register_async_add_entities(self, async_add_entities: AddEntitiesCallback) -> None:
        _LOGGER.debug("async_add_entities registered for %s", self.name)
        self.async_add_entities = async_add_entities
        self.async_add_entities([self.state_sensor, self.msg_per_minute_sensor])

    async def update_sensor_availability(self) -> None:
        """Update the availability of all sensors every 5 minutes."""
        
        while not await event_wait(self.stop_event, 300):
            _LOGGER.debug("Running update_sensor_availability for %s", self.name)
            for sensor in self.sensors.values():
                sensor.update_availability()

        _LOGGER.debug("Stopping update_sensor_availability for %s", self.name)

    async def status_callback(self, state: State) -> None:
        if state == State.CONNECTED:
            self.state = "Running"
        elif state == State.DISCONNECTED:
            self.state = "Disconnected"
        else:
            self.state = ""
        _LOGGER.debug("Got new state: %s. sensor state will be: %s", state, self.state)
        self.state_sensor.set_state(self.state)

    async def receive_callback(self, message: NMEA2000Message) -> None:
        """Process a received NMEA 2000 message."""
        _LOGGER.debug("Processing message: %s", message)
        if self.async_add_entities is None:
            _LOGGER.debug("Cant handle messages as async_add_entities is missing")
            return
            
        # BUild primary key for the sensor
        primary_key_prefix = ""
        for field in message.fields:
            if field.part_of_primary_key:
                primary_key_prefix += "_" + str(field.value)
        #Using MD% as we dont need secure hashing and speed matters.
        primary_key_prefix_hash = hashlib.md5(primary_key_prefix.encode()).hexdigest()
        sensor_name_prefix = f"{self.name}_{message.id}_{primary_key_prefix_hash}_"

        for field in message.fields:
            # Skip undefined fields
            if field.type in [FieldTypes.RESERVED, FieldTypes.SPARE, FieldTypes.BINARY, FieldTypes.VARIABLE, FieldTypes.FIELD_INDEX]:
                _LOGGER.debug(
                    "Skipping field with name: %s and type: %s", field.name, field.type
                )
                continue

            # Construct unique sensor name
            sensor_name = sensor_name_prefix + field.id
            # Check for sensor existence and create/update accordingly
            sensor = self.sensors.get(field.id)
            value = field.value if field.value is not None else field.raw_value
            if sensor is None:
                _LOGGER.info("Creating new sensor for %s", sensor_name)
                # If sensor does not exist, create and add it
                sensor = NMEA2000Sensor(
                    sensor_name,
                    field.name,
                    value,
                    field.unit_of_measurement,
                    message.description,
                    self.device_name,
                )

                self.async_add_entities([sensor])
                self.sensors[field.id] = sensor
            else:
                # If sensor exists, update its state
                _LOGGER.debug(
                    "Updating existing sensor %s with new value: %s",
                    sensor.name,
                    value,
                )
                sensor.set_state(value)

    @callback
    async def start(self, _event: Event) -> None:
        """Connect to the NMEA2000 gateway."""
        _LOGGER.debug("NMEA2000 %s starting", self.name)
        await self.gateway.connect()
        # Start the task that updates the sensor availability every 5 minutes
        self.entry.async_create_background_task(self.hass, self.update_sensor_availability(), "update_sensor_availability")
        _LOGGER.debug("NMEA2000 %s connected", self.name)

    @callback
    async def stop(self, event: Event) -> None:
        """Close resources for the TCP connection."""
        _LOGGER.debug("Sensor %s closed", self.name)
        self.stop_event.set()
        await self.gateway.close()
