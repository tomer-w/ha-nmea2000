import datetime
import logging
import pprint

from . import NMEA2000Sensor

_LOGGER = logging.getLogger(__name__)

def process_fast_packet(pgn, hass, instance_name, data64, data64_hex):
    
    fast_packet_key = f"{instance_name}_fast_packet_key"
    
    # Check if this PGN already has a storage structure; if not, create one
    if pgn not in hass.data[fast_packet_key]:
        hass.data[fast_packet_key][pgn] = {'frames': {}, 'payload_length': 0, 'bytes_stored': 0}
        
    pgn_data = hass.data[fast_packet_key][pgn]
               
    # Convert the last two characters to an integer to get the sequence and frame counters
    last_byte = int(data64_hex[-2:], 16)  # Convert the last two hex digits to an integer
    
    # Extract the sequence counter (high 3 bits) and frame counter (low 5 bits) from the last byte
    sequence_counter = (last_byte >> 5) & 0b111  # Extract high 3 bits
    frame_counter = last_byte & 0b11111  # Extract low 5 bits
    
    total_bytes = None
    
    if frame_counter == 0 and not can_process(hass, instance_name, pgn):
        return

    if frame_counter != 0 and pgn_data['payload_length'] == 0:
        _LOGGER.debug(f"Ignoring frame {frame_counter} for PGN {pgn} as first frame has not been received.")
        return
       
    # Calculate data payload
    if frame_counter == 0:
        
        # Extract the total number of frames from the second-to-last byte
        total_bytes_hex = data64_hex[-4:-2]  # Get the second-to-last byte in hex
        total_bytes = int(total_bytes_hex, 16)  # Convert hex to int
        
        # Start a new pgn hass structure 
      
        pgn_data['payload_length'] = total_bytes
        pgn_data['sequence_counter'] = sequence_counter
        pgn_data['bytes_stored'] = 0  # Reset bytes stored for a new message
        pgn_data['frames'].clear()  # Clear previous frames
                
        # For the first frame, exclude the last 4 hex characters (2 bytes) from the payload
        data_payload_hex = data64_hex[:-4]
        
    else:       
        if sequence_counter != pgn_data['sequence_counter']:
            _LOGGER.debug(f"Ignoring frame {sequence_counter} for PGN {pgn} as it does not match current sequence.")
            return
        elif frame_counter in pgn_data['frames']:
            _LOGGER.debug(f"Frame {frame_counter} for PGN {pgn} is already stored.")
            return
        else:
            # For subsequent frames, exclude the last 2 hex characters (1 byte) from the payload
            data_payload_hex = data64_hex[:-2]
    
    byte_length = len(data_payload_hex) // 2

    # Store the frame data
    pgn_data['frames'][frame_counter] = data_payload_hex
    pgn_data['bytes_stored'] += byte_length  # Update the count of bytes stored
     
    # Log the extracted values
    _LOGGER.debug(f"Sequence Counter: {sequence_counter}")
    _LOGGER.debug(f"Frame Counter: {frame_counter}")
    
    if total_bytes is not None:
        _LOGGER.debug(f"Total Payload Bytes: {total_bytes}")

    _LOGGER.debug(f"Orig Payload (hex): {data64_hex}")
    _LOGGER.debug(f"Data Payload (hex): {data_payload_hex}")
    
    formatted_data = pprint.pformat(hass.data[fast_packet_key])
    _LOGGER.debug("HASS PGN Data: %s", formatted_data)
    
    # Check if all expected bytes have been stored
    if pgn_data['bytes_stored'] >= pgn_data['payload_length']:
        
        _LOGGER.debug("All Fast packet frames collected for PGN: %d", pgn)

        # All data for this PGN has been received, proceed to publish
        combined_payload_hex = combine_pgn_frames(hass, pgn, instance_name)
        combined_payload_int = int(combined_payload_hex, 16)
        
        if combined_payload_int is not None:
            _LOGGER.debug(f"Combined Payload (hex): {combined_payload_hex})")
            _LOGGER.debug(f"Combined Payload (hex): (hex: {combined_payload_int:x})")

            call_process_function(pgn, hass, instance_name, combined_payload_int)

        # Reset the structure for this PGN
        del hass.data[fast_packet_key][pgn]

        
def can_process(hass, instance_name, pgn_id):

    smart2000timestamp_key = f"{instance_name}_smart2000timestamp_key"
    
    now = datetime.now()
    last_processed = hass.data[smart2000timestamp_key]["last_processed"]
    min_interval = hass.data[smart2000timestamp_key]["min_interval"]
    
    if pgn_id not in last_processed or now - last_processed[pgn_id] >= min_interval:
        hass.data[smart2000timestamp_key]["last_processed"][pgn_id] = now  
        return True
    else:
        _LOGGER.debug(f"Throttling activated for PGN {pgn_id} in instance {instance_name}.")
        return False


def is_pgn_allowed_based_on_lists(pgn, pgn_include_list, pgn_exclude_list):
    """
    Determines whether a given PGN should be processed based on whitelist and blacklist rules.

    :param pgn: The PGN to check.
    :param pgn_include_list: A list of PGNs to include (whitelist).
    :param pgn_exclude_list: A list of PGNs to exclude (blacklist).
    :return: True if the PGN should be processed, False otherwise.
    """
    # If the include list is not empty, process only if PGN is in the include list
    if pgn_include_list:
        return pgn in pgn_include_list

    # If the include list is empty but the exclude list is not, process only if PGN is not in the exclude list
    elif pgn_exclude_list:
        return pgn not in pgn_exclude_list

    # If both lists are empty, process all PGNs
    return True


def publish_field(hass, instance_name, field_name, field_description, field_value, pgn_description, unit, pgn_id):
    _LOGGER.debug(f"Publishing field for PGN {pgn_id} and field {field_name} with value {field_value}")

    add_entities_key = f"{instance_name}_add_entities"
    created_sensors_key = f"{instance_name}_created_sensors"

    # Construct unique sensor name
    sensor_name = f"{instance_name}_{pgn_id}_{field_name}"
    
    # Define sensor characteristics
    group = "Smart2000"
    
    unit_of_measurement = unit  # Determine based on field_name if applicable
    
    device_name = pgn_description

    # Access keys for created sensors and entity addition
    created_sensors_key = f"{instance_name}_created_sensors"
    add_entities_key = f"{instance_name}_add_entities"

    # Check for sensor existence and create/update accordingly
    if sensor_name not in hass.data[created_sensors_key]:
        #_LOGGER.debug(f"Creating new sensor for {sensor_name}")
        # If sensor does not exist, create and add it
        sensor = NMEA2000Sensor(
            sensor_name, 
            field_description, 
            field_value, 
            group, 
            unit_of_measurement, 
            device_name, 
            pgn_id,
            instance_name
        )
        
        hass.data[add_entities_key]([sensor])
        hass.data[created_sensors_key][sensor_name] = sensor
    else:
        # If sensor exists, update its state
        _LOGGER.debug(f"Updating existing sensor {sensor_name} with new value: {field_value}")
        sensor = hass.data[created_sensors_key][sensor_name]
        sensor.set_state(field_value)

def combine_pgn_frames(hass, pgn, instance_name):
    """Combine stored frame data for a PGN into a single hex string, preserving the original byte lengths."""
    
    fast_packet_key = f"{instance_name}_fast_packet_key"
    
    if pgn not in hass.data[fast_packet_key]:
        _LOGGER.debug(f"No fast packet data available for PGN {pgn}")
        return None

    pgn_data = hass.data[fast_packet_key][pgn]
    combined_payload_hex = ""  # Start with an empty string

    for frame_counter in sorted(pgn_data['frames']):
        frame_data_hex = pgn_data['frames'][frame_counter]
        combined_payload_hex = frame_data_hex + combined_payload_hex


    return combined_payload_hex



def process_packet(self, packet):
    
    # Extract the type byte and data length from the type byte
    type_byte = packet[0]
    data_length = type_byte & 0x0F  # last 4 bits represent the data length
    
    # Extract and reverse the frame ID
    frame_id = packet[1:5][::-1]
    
    # Convert frame_id bytes to an integer
    frame_id_int = int.from_bytes(frame_id, byteorder='big')
    
    # Extracting Source ID from the frame ID
    source_id = frame_id_int & 0xFF
    source_id_hex = '{:02X}'.format(source_id)
    
    # Extracting PGN ID from the frame ID
    pgn_id = (frame_id_int >> 8) & 0x3FFFF  # Shift right by 8 bits and mask to 18 bits
    pgn_id_hex = '{:06X}'.format(pgn_id)  # Format PGN as a hex string with 6 digits
    
    # Extract and reverse the CAN data
    can_data = packet[5:5 + data_length][::-1]
    can_data_hex = binascii.hexlify(can_data).decode('ascii')
    
    # Prepare combined string in the format "PGN:Source_ID:CAN_Data"
    combined_hex = f"{pgn_id_hex}:{source_id_hex}:{can_data_hex}"
    
    # Log the extracted information including the combined string
    _LOGGER.debug("TCP %s PGN ID: %s, Frame ID: %s, CAN Data: %s, Source ID: %s, Combined: %s",
        self.name,
        pgn_id_hex,
        binascii.hexlify(frame_id).decode('ascii'),
        can_data_hex,
        source_id_hex,
        combined_hex)
    
    set_pgn_entity(self.hass, self.name, combined_hex)
