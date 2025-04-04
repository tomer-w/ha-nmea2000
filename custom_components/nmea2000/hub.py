"""
NMEA 2000 Hub Component for Home Assistant.

This module handles communication with NMEA 2000 networks via USB or TCP gateways
and creates/updates Home Assistant sensors based on received data.
"""

from __future__ import annotations
import logging
import asyncio
import hashlib
import contextlib
import time
from typing import Dict
from datetime import timedelta

# Local imports
from .const import (
    CONF_MODE,
    CONF_PGN_INCLUDE,
    CONF_PGN_EXCLUDE,
    CONF_MODE_USB,
    CONF_SERIAL_PORT,
    CONF_BAUDRATE,
    CONF_IP,
    CONF_PORT,
)
from .config_flow import parse_and_validate_comma_separated_integers
from .NMEA2000Sensor import NMEA2000Sensor

# Home Assistant imports
from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, EVENT_HOMEASSISTANT_START
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.exceptions import ConfigValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

# NMEA 2000 package imports
from nmea2000 import NMEA2000Message, TcpNmea2000Gateway, UsbNmea2000Gateway, FieldTypes, State

_LOGGER = logging.getLogger(__name__)


async def event_wait(evt, timeout):
    """
    Wait for an event with timeout without raising TimeoutError.
    
    Args:
        evt: Event to wait for
        timeout: Maximum time to wait in seconds
        
    Returns:
        True if event is set, False if timeout occurred
    """
    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(evt.wait(), timeout)
    return evt.is_set()


class Hub:
    """NMEA 2000 Hub for managing communication and sensors."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """
        Initialize NMEA2000 Hub.
        
        Sets up the NMEA2000 sensor platform from a config entry.
        
        Args:
            hass: Home Assistant instance
            entry: ConfigEntry containing configuration
        """
        self.hass = hass
        self.entry = entry
        self.stop_event = asyncio.Event()
        self.state = "Initializing"
        self.async_add_entities = None
        self.sensors = {}
        
        # Initialize message counting variables
        self.message_count_per_interval = 0
        self.last_count_time = time.time()
        self.messages_per_minute = 0

        # Retrieve configuration from entry
        self.name = entry.data[CONF_NAME]
        mode = entry.data[CONF_MODE]
        self.device_name = f"NMEA 2000 {mode} Gateway"

        # Create system sensors
        self.state_sensor = NMEA2000Sensor(
            "state", 
            "State", 
            self.state, 
            None, 
            self.device_name, 
            None
        )
        self.total_messages_sensor = NMEA2000Sensor(
            "total_messages", 
            "Total message count", 
            0, 
            "messages", 
            self.device_name, 
            None
        )
        self.msg_per_minute_sensor = NMEA2000Sensor(
            "messages_per_minute", 
            "Messages per minute", 
            0, 
            "msg/min", 
            self.device_name, 
            None
        )

        # Parse PGN include/exclude lists
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

        # Configure the appropriate gateway based on mode
        if mode == CONF_MODE_USB:
            serial_port = entry.data[CONF_SERIAL_PORT]
            baudrate = entry.data[CONF_BAUDRATE]
            _LOGGER.info(
                "USB sensor with name: %s, serial_port: %s, baudrate: %s",
                self.name,
                serial_port,
                baudrate,
            )
            self.gateway = UsbNmea2000Gateway(
                serial_port, 
                exclude_pgns=pgn_exclude, 
                include_pgns=pgn_include
            )
            url = f"usb://{serial_port}"
        elif mode == "TCP":
            ip = entry.data[CONF_IP]
            port = entry.data[CONF_PORT]
            _LOGGER.info(
                "TCP sensor with name: %s, IP: %s, port: %s", 
                self.name, 
                ip, 
                port
            )
            self.gateway = TcpNmea2000Gateway(
                ip, 
                port, 
                exclude_pgns=pgn_exclude, 
                include_pgns=pgn_include
            )
            url = f"tcp://{ip}:{port}"
        else:
            raise ConfigValidationError(f"mode {mode} not supported")

        # Set up callbacks for gateway events
        self.gateway.set_receive_callback(self.receive_callback)
        self.gateway.set_status_callback(self.status_callback)

        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self.stop)

    async def register_async_add_entities(self, async_add_entities: AddEntitiesCallback) -> None:
        """
        Register the callback for adding entities to Home Assistant.
        
        Args:
            async_add_entities: Callback to add entities to Home Assistant
        """
        _LOGGER.debug("async_add_entities registered for %s", self.name)
        self.async_add_entities = async_add_entities
        
        # Add the system sensors
        self.async_add_entities([
            self.state_sensor, 
            self.total_messages_sensor, 
            self.msg_per_minute_sensor
        ])
        await self.start()

    async def update_tasks(self) -> None:
        """
        Combined background task for periodic updates.
        
        Handles:
        1. Message rate calculation (every 10 seconds)
        2. Sensor availability updates (every 5 minutes)
        """
        availability_interval = 300  # 5 minutes in seconds
        message_rate_interval = 10   # 10 seconds
        
        last_availability_update = time.time()
        
        while not await event_wait(self.stop_event, message_rate_interval):
            current_time = time.time()
            
            # Update message rate (every 10 seconds)
            elapsed_time = current_time - self.last_count_time
            if elapsed_time > 0:
                # Calculate messages per minute based on count and elapsed time
                self.messages_per_minute = int(self.message_count_per_interval * (60 / elapsed_time))
                _LOGGER.debug(
                    "Updating messages per minute: %d messages in %.2f seconds = %d msg/min",
                    self.message_count_per_interval, elapsed_time, self.messages_per_minute
                )
                
                # Update the sensor
                self.msg_per_minute_sensor.set_state(self.messages_per_minute)
                
                # Reset for next interval
                self.message_count_per_interval = 0
                self.last_count_time = current_time
            
            # Update sensor availability (every 5 minutes)
            if current_time - last_availability_update >= availability_interval:
                _LOGGER.debug("Running update_sensor_availability for %s", self.name)
                for sensor in self.sensors.values():
                    sensor.update_availability()
                last_availability_update = current_time
        
        _LOGGER.debug("Stopping update tasks for %s", self.name)

    async def status_callback(self, state: State) -> None:
        """
        Process changes in gateway connection status.
        
        Args:
            state: New gateway connection state
        """
        if state == State.CONNECTED:
            self.state = "Running"
        elif state == State.DISCONNECTED:
            self.state = "Disconnected"
        else:
            self.state = "Unknown"
        
        _LOGGER.debug("Got new state: %s. sensor state will be: %s", state, self.state)
        self.state_sensor.set_state(self.state)

    async def receive_callback(self, message: NMEA2000Message) -> None:
        """
        Process a received NMEA 2000 message.
        
        Handles:
        1. Message counting and statistics
        2. Creating/updating PGN message count sensors
        3. Creating/updating individual field sensors
        
        Args:
            message: Received NMEA 2000 message
        """
        _LOGGER.debug("Processing message: %s", message)
        
        if self.async_add_entities is None:
            _LOGGER.debug("Can't handle messages as async_add_entities is not registered yet")
            return

        # Increment message counters
        self.message_count_per_interval += 1
        self.total_messages_sensor.set_state(self.total_messages_sensor.native_value + 1)

        # Build primary key for the sensor
        primary_key_prefix = ""
        for field in message.fields:
            if field.part_of_primary_key:
                primary_key_prefix += "_" + str(field.value)
        
        # Using MD5 as we don't need secure hashing and speed matters
        primary_key_prefix_hash = hashlib.md5(primary_key_prefix.encode()).hexdigest()
        sensor_name_prefix = f"{self.name}_{message.id}_{primary_key_prefix_hash}_"

        # Create or update PGN message count sensors
        pgn_sensor = self.sensors.get(message.PGN)
        if pgn_sensor is None:
            _LOGGER.info("Creating new sensor for PGN %d", message.PGN)
            sensor = NMEA2000Sensor(
                message.id,
                f"PGN {message.PGN} message count",
                1,
                "count",
                self.device_name,
                None
            )
            self.async_add_entities([sensor])
            self.sensors[message.PGN] = sensor
        else:
            # If sensor exists, increment counter
            new_value = pgn_sensor.native_value + 1
            _LOGGER.debug(
                "Updating existing PGN sensor %s with new value: %d",
                pgn_sensor.name,
                new_value,
            )
            pgn_sensor.set_state(new_value)
            
        # Process individual fields in the message
        for field in message.fields:
            # Skip undefined or unusable field types
            if field.type in [
                FieldTypes.RESERVED, 
                FieldTypes.SPARE, 
                FieldTypes.BINARY, 
                FieldTypes.VARIABLE, 
                FieldTypes.FIELD_INDEX
            ]:
                _LOGGER.debug(
                    "Skipping field with name: %s and type: %s", 
                    field.name, 
                    field.type
                )
                continue

            # Construct unique sensor name
            sensor_name = sensor_name_prefix + field.id
            
            # Use the field value if available, otherwise use raw value
            value = field.value if field.value is not None else field.raw_value
            
            # Check for sensor existence and create/update accordingly
            sensor = self.sensors.get(field.id)
            if sensor is None:
                _LOGGER.info("Creating new sensor for %s", sensor_name)
                # Create new sensor
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
                # Update existing sensor
                _LOGGER.debug(
                    "Updating existing sensor %s with new value: %s",
                    sensor.name,
                    value,
                )
                sensor.set_state(value)

    async def start(self) -> None:
        """
        Connect to the NMEA2000 gateway and start background tasks.
        """
        _LOGGER.debug("NMEA2000 %s starting", self.name)
        await self.gateway.connect()
        
        # Start the periodic update task for message rates and sensor availability
        self.entry.async_create_background_task(
            self.hass, 
            self.update_tasks(), 
            "update_tasks"
        )
        
        _LOGGER.debug("NMEA2000 %s connected", self.name)

    @callback
    async def stop(self, event: Event) -> None:
        """
        Close resources and disconnect from the gateway.
        
        Args:
            event: HomeAssistant stop event
        """
        _LOGGER.debug("NMEA2000 Hub %s closing", self.name)
        self.stop_event.set()
        await self.gateway.close()
        _LOGGER.info("NMEA2000 Hub %s closed", self.name)
