import asyncio
import serial_asyncio
from serial import SerialException
import binascii
from homeassistant.components.sensor import  SensorEntity
from homeassistant.core import callback
from .sensorCommon import set_pgn_entity

import logging
_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Serial Sensor"
DEFAULT_BAUDRATE = 2000000
DEFAULT_BYTESIZE = serial_asyncio.serial.EIGHTBITS
DEFAULT_PARITY = serial_asyncio.serial.PARITY_NONE
DEFAULT_STOPBITS = serial_asyncio.serial.STOPBITS_ONE
DEFAULT_XONXOFF = False
DEFAULT_RTSCTS = False
DEFAULT_DSRDTR = False

# SerialSensor class representing a sensor entity interacting with a serial device
class SerialSensor(SensorEntity):
    """Representation of a Serial sensor."""

    _attr_should_poll = False
    

    def __init__(
        self,
        name,
        port,
        baudrate,
    ):
        """Initialize the Serial sensor."""
        self._name = name
        self._state = None
        self._port = port
        self._baudrate = baudrate
        self._bytesize = DEFAULT_BYTESIZE
        self._parity = DEFAULT_PARITY
        self._stopbits = DEFAULT_STOPBITS
        self._xonxoff = DEFAULT_XONXOFF
        self._rtscts = DEFAULT_RTSCTS
        self._dsrdtr = DEFAULT_DSRDTR
        self._serial_loop_task = None
        self._attributes = None
        
        self._retry_delay = 5  # Reconnection tart with 5 seconds
        self._max_delay = 60  # Reconnection maximum delay of 1 minutes



    async def async_added_to_hass(self) -> None:
        """Handle when an entity is about to be added to Home Assistant."""
        self._serial_loop_task = self.hass.loop.create_task(self.serial_read())


    async def read_loop(self, reader):
        """Continuously read data from the serial port."""

        buffer = bytearray()
        try:
            while True:
                # Read chunks of data from the serial port
                data = await reader.read(100)
                if not data:
                    # If no data and buffer is not empty, process remaining data
                    if buffer:
                        self.process_packet(buffer)
                        buffer = bytearray()
                    break
                buffer.extend(data)
    
                # Continue processing as long as there's data in the buffer
                while True:
                    # Find the packet start and end delimiters
                    start = buffer.find(b'\xaa')
                    end = buffer.find(b'\x55', start)
                    
                    if start == -1 or end == -1:
                        # If start or end not found, wait for more data
                        break
    
                    # Extract the complete packet, including the end delimiter
                    packet = buffer[start:end+1]
    
                    # Process the packet
                    if len(packet) > 2:  # Make sure it's not just the header and end code
                        self.process_packet(packet)
    
                    # Remove the processed packet from the buffer
                    buffer = buffer[end+1:]
    
        except Exception as exc:
            _LOGGER.exception("Error while reading from serial port: %s", exc)
        finally:
            _LOGGER.debug("Finished reading data")


    async def serial_read(self):
        
        """Read the data from the port."""
        while True:
            try:
                reader, _ = await serial_asyncio.open_serial_connection(
                    url=self._port,
                    baudrate=self._baudrate,
                    bytesize=self._bytesize,
                    parity=self._parity,
                    stopbits=self._stopbits,
                    xonxoff=self._xonxoff,
                    rtscts=self._rtscts,
                    dsrdtr=self._dsrdtr,
                )
                
                _LOGGER.debug("Serial connection established")
                await self.read_loop(reader)
                
                
            except SerialException as exc:
                _LOGGER.exception("Serial connection failed: %s. Retrying in %d seconds...", exc, self._retry_delay)
                await self._handle_error()
            except asyncio.CancelledError:
                _LOGGER.debug("Serial read task was cancelled")
                break
            except Exception as exc:
                _LOGGER.exception("Unexpected error: %s. Retrying in %d seconds...", exc, self._retry_delay)
                await self._handle_error()


    def process_packet(self, packet):
        
        if len(packet) < 7:  # AA + E8 + Frame ID (4 bytes min) + 55
            _LOGGER.error("Invalid packet length: %s", binascii.hexlify(packet))
            return

        packet = packet[1:-1]  # Remove the start and end delimiters
        parse_frame(packet)

        # Extract the type byte and data length from the type byte
        type_byte = packet[1]
        data_length = type_byte & 0x0F  # last 4 bits represent the data length
        
        # Extract and reverse the frame ID
        frame_id = packet[2:6][::-1]
        
        # Convert frame_id bytes to an integer
        frame_id_int = int.from_bytes(frame_id, byteorder='big')
        
        # Extracting Source ID from the frame ID
        source_id = frame_id_int & 0xFF
        source_id_hex = '{:02X}'.format(source_id)
        
        # Extracting PGN ID from the frame ID
        pgn_id = (frame_id_int >> 8) & 0x3FFFF  # Shift right by 8 bits and mask to 18 bits
        pgn_id_hex = '{:06X}'.format(pgn_id)  # Format PGN as a hex string with 6 digits
        
        # Extract and reverse the CAN data
        can_data = packet[6:6 + data_length][::-1]
        can_data_hex = binascii.hexlify(can_data).decode('ascii')
        
        # Prepare combined string in the format "PGN:Source_ID:CAN_Data"
        combined_hex = f"{pgn_id_hex}:{source_id_hex}:{can_data_hex}"
        
        # Log the extracted information including the combined string
        _LOGGER.debug("USB %s PGN ID: %s, Frame ID: %s, CAN Data: %s, Source ID: %s, Combined: %s",
            self.name,
            pgn_id_hex,
            binascii.hexlify(frame_id).decode('ascii'),
            can_data_hex,
            source_id_hex,
            combined_hex)
        
        set_pgn_entity(self.hass, self.name, combined_hex)
        

    async def _handle_error(self):
        """Handle error for serial connection."""
        self._state = None
        self._attributes = None
        self.async_write_ha_state()
        await asyncio.sleep(5)
        await asyncio.sleep(self._retry_delay)
        self._retry_delay = min(self._retry_delay * 2, self._max_delay)  # Double the delay, up to a maximum

    @callback
    def stop(self, event):
        """Close resources."""
        if self._serial_loop_task:
            self._serial_loop_task.cancel()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def extra_state_attributes(self):
        """Return the attributes of the entity (if any JSON present)."""
        return self._attributes

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state
