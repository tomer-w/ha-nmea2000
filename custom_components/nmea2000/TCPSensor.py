import asyncio
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
        # Extract the type byte and data length from the type byte
        type_byte = packet[0]
        data_length = type_byte & 0x0F  # last 4 bits represent the data length

        # Extract and reverse the frame ID
        frame_id = packet[1:5][::-1]

        # Convert frame_id bytes to an integer
        frame_id_int = int.from_bytes(frame_id, byteorder="big")

        # Extracting Source ID from the frame ID
        source_id = frame_id_int & 0xFF
        source_id_hex = "{:02X}".format(source_id)

        # Extracting PGN ID from the frame ID
        pgn_id = (
            frame_id_int >> 8
        ) & 0x3FFFF  # Shift right by 8 bits and mask to 18 bits
        pgn_id_hex = "{:06X}".format(pgn_id)  # Format PGN as a hex string with 6 digits

        # Extract and reverse the CAN data
        can_data = packet[5 : 5 + data_length][::-1]
        can_data_hex = binascii.hexlify(can_data).decode("ascii")

        # Prepare combined string in the format "PGN:Source_ID:CAN_Data"
        combined_hex = f"{pgn_id_hex}:{source_id_hex}:{can_data_hex}"

        # Log the extracted information including the combined string
        _LOGGER.debug(
            "TCP %s PGN ID: %s, Frame ID: %s, CAN Data: %s, Source ID: %s, Combined: %s",
            self.name,
            pgn_id_hex,
            binascii.hexlify(frame_id).decode("ascii"),
            can_data_hex,
            source_id_hex,
            combined_hex,
        )

        super().process_frame(combined_hex)

    @callback
    def stop(self, event):
        """Close resources for the TCP connection."""
        if self._connection_loop_task:
            self._connection_loop_task.cancel()
