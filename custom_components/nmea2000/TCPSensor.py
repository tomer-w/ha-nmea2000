import asyncio
from .SensorBase import SensorBase
import binascii
from datetime import timedelta
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import HomeAssistant, callback

import logging

_LOGGER = logging.getLogger(__name__)


# TCPSensor class representing a sensor entity interacting with a TCP device
class TCPSensor(SensorBase):
    """Representation of a TCP sensor."""

    _attr_should_poll = False

    def __init__(
        self,
        name,
        hass: HomeAssistant,
        async_add_entities: AddEntitiesCallback,
        host,
        port,
    ):
        """Initialize the TCP sensor."""
        super().__init__(name, hass, async_add_entities)
        self._name = name
        self._state = None
        self._host = host
        self._port = int(port)
        self._connection_loop_task = None
        self._attributes = None

    async def async_added_to_hass(self) -> None:
        """Handle when an entity is about to be added to Home Assistant."""
        self._connection_loop_task = self.hass.loop.create_task(
            self.tcp_read(self._host, self._port)
        )

    async def read_loop(self, reader):
        """Continuously read data from the TCP port."""

        buffer = bytearray()
        try:
            while True:
                # Read chunks of data from the serial port
                data = await reader.read(100)
                if not data:
                    _LOGGER.debug(f"No data to read, aborting connection")
                    break
                buffer.extend(data)
                _LOGGER.debug(
                    f"Reading {len(data)} bytes. new buffer size: {len(buffer)}"
                )

                # Continue processing as long as there's data in the buffer
                while len(buffer) >= 13:
                    # each packet is 13 bytes
                    # Extract the complete packet
                    packet = buffer[0:13]
                    # Process the packet
                    self.process_packet(packet)

                    # Remove the processed packet from the buffer
                    buffer = buffer[14:]
                    _LOGGER.debug(f"Packet proccessed. new buffer size: {len(buffer)}")

        except Exception as exc:
            _LOGGER.exception("Error while reading from serial port: %s", exc)
        finally:
            _LOGGER.debug("Finished reading data")

    async def tcp_read(self, host, port):
        """Read the data from the TCP connection with improved error handling."""
        retry_delay = 1  # Start with a 1-second delay
        max_retry_delay = 60  # Maximum delay of 60 seconds between retries
        writer = None

        last_processed = {}  # Dictionary to store last processed timestamp for each sentence type
        min_interval = timedelta(
            seconds=5
        )  # Minimum time interval between processing each sentence type

        data_timeout = 60  # 60 seconds timeout for data reception

        while True:
            try:
                # Variable to track the current operation
                current_operation = "connecting"

                _LOGGER.info(f"Attempting to connect to TCP device {host}:{port} ")

                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=10
                )

                _LOGGER.info(f"Connected to TCP device {host}:{port}")
                retry_delay = 1  # Reset retry delay after a successful connection

                current_operation = "receiving data"
                await self.read_loop(reader)

            # Handling connection errors more gracefully
            except asyncio.TimeoutError:
                if current_operation == "connecting":
                    _LOGGER.error(
                        f"Timeout occurred while trying to connect to TCP device at {host}:{port}."
                    )
                else:  # current_operation == "receiving data"
                    _LOGGER.error(
                        f"No data received in the last {data_timeout} seconds from {host}:{port}."
                    )

            except asyncio.CancelledError:
                _LOGGER.info("Connection attempt to TCP device was cancelled.")
                raise

            except Exception as exc:
                _LOGGER.exception(
                    f"Unexpected error with TCP device {host}:{port}: {exc}"
                )

            finally:
                try:
                    if writer:
                        writer.close()
                        await writer.wait_closed()
                except Exception as e:
                    _LOGGER.error(f"Error closing writer: {e}")
                _LOGGER.info(f"Will retry in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)

    def process_packet(self, packet):
        """Process the received packet."""
        if len(packet) != 13:  # Always 13 bytes in the ECAN family
            _LOGGER.error(
                "Invalid packet length: %d. packet: %s",
                len(packet),
                binascii.hexlify(packet),
            )
            return

        super().process_frame(packet)

    @callback
    def stop(self, event):
        """Close resources for the TCP connection."""
        if self._connection_loop_task:
            self._connection_loop_task.cancel()
