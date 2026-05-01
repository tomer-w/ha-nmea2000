"""Tests for the NMEA2000 Hub."""
import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry
from nmea2000 import State, NMEA2000Message, NMEA2000Field, FieldTypes

from custom_components.nmea2000.const import (
    DOMAIN,
    CONF_CAN_INTERFACE,
    CONF_CAN_CHANNEL,
    CONF_CAN_BITRATE,
    CONF_SERIAL_PORT,
    CONF_BAUDRATE,
    CONF_IP,
    CONF_PORT,
)
from custom_components.nmea2000.config_flow import CONF_GATEWAY_TYPE, GatewayType
from custom_components.nmea2000.hub import Hub


def _make_gateway_mock():
    """Create a gateway mock with async methods properly mocked."""
    mock = MagicMock()
    mock.connect = AsyncMock()
    mock.close = AsyncMock()
    return mock


def _make_entry(hass, gateway_type: GatewayType, extra_data=None):
    """Create a MockConfigEntry with the given gateway type and extra data."""
    data = {"name": "Test", CONF_GATEWAY_TYPE: gateway_type.value}
    if extra_data:
        data.update(extra_data)
    entry = MockConfigEntry(domain=DOMAIN, data=data)
    entry.add_to_hass(hass)
    return entry


@patch("custom_components.nmea2000.hub.PythonCanAsyncIOClient")
async def test_hub_creates_can_gateway(mock_can_cls, hass):
    """Test Hub creates PythonCanAsyncIOClient for python_can gateway type."""
    mock_can_cls.return_value = _make_gateway_mock()

    entry = _make_entry(hass, GatewayType.PYTHON_CAN, {
        CONF_CAN_INTERFACE: "socketcan",
        CONF_CAN_CHANNEL: "can0",
        CONF_CAN_BITRATE: 250000,
    })
    Hub(hass, entry)

    mock_can_cls.assert_called_once()
    call_kwargs = mock_can_cls.call_args.kwargs
    assert call_kwargs["interface"] == "socketcan"
    assert call_kwargs["channel"] == "can0"
    assert call_kwargs["bitrate"] == 250000


@patch("custom_components.nmea2000.hub.WaveShareNmea2000Gateway")
async def test_hub_creates_usb_gateway(mock_usb_cls, hass):
    """Test Hub creates WaveShareNmea2000Gateway for waveshare gateway type."""
    mock_usb_cls.return_value = _make_gateway_mock()

    entry = _make_entry(hass, GatewayType.WAVESHARE, {
        CONF_SERIAL_PORT: "/dev/ttyUSB0",
        CONF_BAUDRATE: 2000000,
    })
    Hub(hass, entry)

    mock_usb_cls.assert_called_once()
    assert mock_usb_cls.call_args.kwargs["port"] == "/dev/ttyUSB0"


@patch("custom_components.nmea2000.hub.EByteNmea2000Gateway")
async def test_hub_creates_tcp_ebyte_gateway(mock_tcp_cls, hass):
    """Test Hub creates EByteNmea2000Gateway for ebyte gateway type."""
    mock_tcp_cls.return_value = _make_gateway_mock()

    entry = _make_entry(hass, GatewayType.EBYTE, {
        CONF_IP: "192.168.1.100",
        CONF_PORT: 8881,
    })
    Hub(hass, entry)

    mock_tcp_cls.assert_called_once()
    assert mock_tcp_cls.call_args.kwargs["host"] == "192.168.1.100"
    assert mock_tcp_cls.call_args.kwargs["port"] == 8881


@patch("custom_components.nmea2000.hub.TextNmea2000Gateway")
async def test_hub_creates_text_gateway(mock_text_cls, hass):
    """Test Hub creates TextNmea2000Gateway for text gateway type."""
    mock_text_cls.return_value = _make_gateway_mock()

    entry = _make_entry(hass, GatewayType.TEXT, {
        CONF_IP: "192.168.1.100",
        CONF_PORT: 2000,
    })
    Hub(hass, entry)

    mock_text_cls.assert_called_once()
    assert mock_text_cls.call_args.kwargs["host"] == "192.168.1.100"
    assert mock_text_cls.call_args.kwargs["port"] == 2000


@patch("custom_components.nmea2000.hub.ActisenseBstNmea2000Gateway")
async def test_hub_creates_actisense_bst_gateway(mock_bst_cls, hass):
    """Test Hub creates ActisenseBstNmea2000Gateway for actisense_bst gateway type."""
    mock_bst_cls.return_value = _make_gateway_mock()

    entry = _make_entry(hass, GatewayType.ACTISENSE_BST, {
        CONF_IP: "192.168.1.200",
        CONF_PORT: 3000,
    })
    Hub(hass, entry)

    mock_bst_cls.assert_called_once()
    assert mock_bst_cls.call_args.kwargs["host"] == "192.168.1.200"
    assert mock_bst_cls.call_args.kwargs["port"] == 3000


async def test_hub_rejects_unknown_gateway_type(hass):
    """Test Hub raises an exception for unknown gateway type."""
    data = {"name": "Test", CONF_GATEWAY_TYPE: "unknown_type"}
    entry = MockConfigEntry(domain=DOMAIN, data=data)
    entry.add_to_hass(hass)
    with pytest.raises((Exception, ValueError)):
        Hub(hass, entry)


@patch("custom_components.nmea2000.hub.PythonCanAsyncIOClient")
async def test_hub_can_gateway_receives_pgn_filters(mock_can_cls, hass):
    """Test CAN gateway receives PGN include/exclude lists."""
    mock_can_cls.return_value = _make_gateway_mock()

    entry = _make_entry(hass, GatewayType.PYTHON_CAN, {
        CONF_CAN_INTERFACE: "slcan",
        CONF_CAN_CHANNEL: "/dev/ttyUSB0",
        CONF_CAN_BITRATE: 250000,
        "pgn_include": "127250,130306",
    })
    Hub(hass, entry)

    call_kwargs = mock_can_cls.call_args.kwargs
    assert 127250 in call_kwargs["include_pgns"]
    assert 130306 in call_kwargs["include_pgns"]


@patch("custom_components.nmea2000.hub.PythonCanAsyncIOClient")
async def test_hub_can_sets_callbacks(mock_can_cls, hass):
    """Test CAN gateway gets receive and status callbacks set."""
    mock_instance = _make_gateway_mock()
    mock_can_cls.return_value = mock_instance

    entry = _make_entry(hass, GatewayType.PYTHON_CAN, {
        CONF_CAN_INTERFACE: "slcan",
        CONF_CAN_CHANNEL: "/dev/ttyUSB0",
        CONF_CAN_BITRATE: 250000,
    })
    Hub(hass, entry)

    mock_instance.set_receive_callback.assert_called_once()
    mock_instance.set_status_callback.assert_called_once()


@patch("custom_components.nmea2000.hub.PythonCanAsyncIOClient")
async def test_hub_status_callback_connected(mock_can_cls, hass):
    """Test status callback sets Running state on CONNECTED."""
    mock_can_cls.return_value = _make_gateway_mock()

    entry = _make_entry(hass, GatewayType.PYTHON_CAN, {
        CONF_CAN_INTERFACE: "slcan",
        CONF_CAN_CHANNEL: "/dev/ttyUSB0",
        CONF_CAN_BITRATE: 250000,
    })
    hub = Hub(hass, entry)
    hub.state_sensor = MagicMock()

    await hub.status_callback(State.CONNECTED)
    assert hub.state == "Running"
    hub.state_sensor.set_state.assert_called_once_with("Running")


@patch("custom_components.nmea2000.hub.PythonCanAsyncIOClient")
async def test_hub_status_callback_disconnected(mock_can_cls, hass):
    """Test status callback sets Disconnected state on DISCONNECTED."""
    mock_can_cls.return_value = _make_gateway_mock()

    entry = _make_entry(hass, GatewayType.PYTHON_CAN, {
        CONF_CAN_INTERFACE: "slcan",
        CONF_CAN_CHANNEL: "/dev/ttyUSB0",
        CONF_CAN_BITRATE: 250000,
    })
    hub = Hub(hass, entry)
    hub.state_sensor = MagicMock()

    await hub.status_callback(State.DISCONNECTED)
    assert hub.state == "Disconnected"


@patch("custom_components.nmea2000.hub.PythonCanAsyncIOClient")
async def test_hub_hyphenated_name_creates_valid_sensors(mock_can_cls, hass):
    """Test Hub with hyphenated name creates sensors with sanitized unique IDs."""
    mock_can_cls.return_value = _make_gateway_mock()

    entry = _make_entry(hass, GatewayType.PYTHON_CAN, {
        "name": "YDEN-02",
        CONF_CAN_INTERFACE: "socketcan",
        CONF_CAN_CHANNEL: "can0",
        CONF_CAN_BITRATE: 250000,
    })
    hub = Hub(hass, entry)

    assert hub.name == "YDEN-02"
    assert "-" not in hub.state_sensor._attr_unique_id
    assert "-" not in hub.total_messages_sensor._attr_unique_id
    assert "-" not in hub.msg_per_minute_sensor._attr_unique_id


def _make_hub_for_receive(hass, mock_can_cls):
    """Create a Hub wired up for receive_callback testing."""
    mock_can_cls.return_value = _make_gateway_mock()
    entry = _make_entry(hass, GatewayType.PYTHON_CAN, {
        CONF_CAN_INTERFACE: "socketcan",
        CONF_CAN_CHANNEL: "can0",
        CONF_CAN_BITRATE: 250000,
    })
    hub = Hub(hass, entry)

    added_entities = []
    hub.async_add_entities = lambda entities: added_entities.extend(entities)
    hub.state_sensor = MagicMock()
    hub.total_messages_sensor = MagicMock()
    hub.total_messages_sensor.native_value = 0
    return hub, added_entities


def _make_message(fields, pgn=127503, msg_id="acInputStatus", description="AC Input Status"):
    """Build a minimal NMEA2000Message with the given fields."""
    msg = NMEA2000Message(PGN=pgn, id=msg_id, description=description, ttl=timedelta(seconds=1.5))
    msg.fields = fields
    msg.hash = "testhash"
    msg.source = 0
    msg.destination = 255
    msg.source_iso_name = None
    return msg


@patch("custom_components.nmea2000.hub.PythonCanAsyncIOClient")
async def test_receive_callback_creates_sensors_for_flat_fields(mock_can_cls, hass):
    """Test that flat NUMBER/LOOKUP fields still create sensors."""
    hub, added = _make_hub_for_receive(hass, mock_can_cls)

    msg = _make_message([
        NMEA2000Field("voltage", "Voltage", None, "V", 230.5, 23050, None, FieldTypes.NUMBER, False),
        NMEA2000Field("current", "Current", None, "A", 5.2, 52, None, FieldTypes.NUMBER, False),
    ])
    await hub.receive_callback(msg)

    sensor_ids = [s._attr_unique_id for s in added if hasattr(s, '_attr_unique_id')]
    assert any("voltage" in sid for sid in sensor_ids)
    assert any("current" in sid for sid in sensor_ids)


@patch("custom_components.nmea2000.hub.PythonCanAsyncIOClient")
async def test_receive_callback_expands_list_field(mock_can_cls, hass):
    """Test that a VARIABLE list field with NMEA2000Field values creates sensors per entry."""
    hub, added = _make_hub_for_receive(hass, mock_can_cls)

    list_entries = [
        {
            "voltage": NMEA2000Field("voltage", "Voltage", None, "V", 230.5, 23050, None, FieldTypes.NUMBER, False),
            "current": NMEA2000Field("current", "Current", None, "A", 5.2, 52, None, FieldTypes.NUMBER, False),
            "frequency": NMEA2000Field("frequency", "Frequency", None, "Hz", 50.01, 5001, None, FieldTypes.NUMBER, False),
        },
    ]
    msg = _make_message([
        NMEA2000Field("instance", "Instance", None, None, 0, 0, None, FieldTypes.NUMBER, True),
        NMEA2000Field("list", "List", None, None, list_entries, None, None, FieldTypes.VARIABLE, False),
    ])
    await hub.receive_callback(msg)

    sensor_ids = {s._attr_unique_id: s for s in added if hasattr(s, '_attr_unique_id')}
    voltage_sensors = [s for sid, s in sensor_ids.items() if sid.endswith("_voltage")]
    assert len(voltage_sensors) == 1
    assert voltage_sensors[0]._attr_native_value == 230.5
    assert voltage_sensors[0]._attr_native_unit_of_measurement == "V"
    assert voltage_sensors[0]._attr_name == "Voltage"

    assert any(sid.endswith("_current") for sid in sensor_ids)
    assert any(sid.endswith("_frequency") for sid in sensor_ids)


@patch("custom_components.nmea2000.hub.PythonCanAsyncIOClient")
async def test_receive_callback_list_field_none_value(mock_can_cls, hass):
    """Test that list entries with None value (unavailable field) create sensors correctly."""
    hub, added = _make_hub_for_receive(hass, mock_can_cls)

    list_entries = [
        {
            "acceptability": NMEA2000Field("acceptability", "Acceptability", None, None, "Good", 0, None, FieldTypes.LOOKUP, False),
            "voltage": NMEA2000Field("voltage", "Voltage", None, "V", None, 65534, None, FieldTypes.NUMBER, False),
        },
    ]
    msg = _make_message([
        NMEA2000Field("list", "List", None, None, list_entries, None, None, FieldTypes.VARIABLE, False),
    ])
    await hub.receive_callback(msg)

    sensor_ids = {s._attr_unique_id: s for s in added if hasattr(s, '_attr_unique_id')}
    voltage_sensors = [s for sid, s in sensor_ids.items() if sid.endswith("_voltage")]
    assert len(voltage_sensors) == 1
    assert voltage_sensors[0]._attr_native_value is None

    accept_sensors = [s for sid, s in sensor_ids.items() if sid.endswith("_acceptability")]
    assert len(accept_sensors) == 1
    assert accept_sensors[0]._attr_native_value == "Good"


@patch("custom_components.nmea2000.hub.PythonCanAsyncIOClient")
async def test_receive_callback_list_field_skips_reserved(mock_can_cls, hass):
    """Test that reserved fields in list entries are skipped."""
    hub, added = _make_hub_for_receive(hass, mock_can_cls)

    list_entries = [
        {
            "voltage": NMEA2000Field("voltage", "Voltage", None, "V", 230.5, 23050, None, FieldTypes.NUMBER, False),
            "reserved_20": NMEA2000Field("reserved_20", "Reserved", None, None, 0, 0, None, FieldTypes.RESERVED, False),
            "current": NMEA2000Field("current", "Current", None, "A", 5.2, 52, None, FieldTypes.NUMBER, False),
        },
    ]
    msg = _make_message([
        NMEA2000Field("list", "List", None, None, list_entries, None, None, FieldTypes.VARIABLE, False),
    ])
    await hub.receive_callback(msg)

    sensor_ids = [s._attr_unique_id for s in added if hasattr(s, '_attr_unique_id')]
    assert not any("reserved" in sid for sid in sensor_ids)
    assert any(sid.endswith("_voltage") for sid in sensor_ids)


@patch("custom_components.nmea2000.hub.PythonCanAsyncIOClient")
async def test_receive_callback_list_field_multiple_entries(mock_can_cls, hass):
    """Test that multiple list entries create sensors with distinct indices."""
    hub, added = _make_hub_for_receive(hass, mock_can_cls)

    list_entries = [
        {
            "voltage": NMEA2000Field("voltage", "Voltage", None, "V", 230.5, 23050, None, FieldTypes.NUMBER, False),
            "current": NMEA2000Field("current", "Current", None, "A", 5.2, 52, None, FieldTypes.NUMBER, False),
        },
        {
            "voltage": NMEA2000Field("voltage", "Voltage", None, "V", 120.0, 12000, None, FieldTypes.NUMBER, False),
            "current": NMEA2000Field("current", "Current", None, "A", 10.1, 101, None, FieldTypes.NUMBER, False),
        },
    ]
    msg = _make_message([
        NMEA2000Field("list", "List", None, None, list_entries, None, None, FieldTypes.VARIABLE, False),
    ])
    await hub.receive_callback(msg)

    sensor_ids = [s._attr_unique_id for s in added if hasattr(s, '_attr_unique_id')]
    # First entry has no suffix, second entry has _1
    assert any(sid.endswith("_voltage") for sid in sensor_ids)
    assert any("voltage_1" in sid for sid in sensor_ids)
    assert any(sid.endswith("_current") for sid in sensor_ids)
    assert any("current_1" in sid for sid in sensor_ids)


@patch("custom_components.nmea2000.hub.PythonCanAsyncIOClient")
async def test_receive_callback_list_field_updates_existing_sensors(mock_can_cls, hass):
    """Test that a second message updates existing list-derived sensors."""
    hub, added = _make_hub_for_receive(hass, mock_can_cls)

    list_entries = [
        {"voltage": NMEA2000Field("voltage", "Voltage", None, "V", 230.5, 23050, None, FieldTypes.NUMBER, False)},
    ]
    msg = _make_message([
        NMEA2000Field("list", "List", None, None, list_entries, None, None, FieldTypes.VARIABLE, False),
    ])
    await hub.receive_callback(msg)

    voltage_sensor = next(s for s in added if s._attr_unique_id.endswith("_voltage"))
    voltage_sensor._ready = True
    voltage_sensor.async_schedule_update_ha_state = MagicMock()

    list_entries2 = [
        {"voltage": NMEA2000Field("voltage", "Voltage", None, "V", 231.0, 23100, None, FieldTypes.NUMBER, False)},
    ]
    msg2 = _make_message([
        NMEA2000Field("list", "List", None, None, list_entries2, None, None, FieldTypes.VARIABLE, False),
    ])
    await hub.receive_callback(msg2)

    assert voltage_sensor._attr_native_value == 231.0


@patch("custom_components.nmea2000.hub.PythonCanAsyncIOClient")
async def test_receive_callback_non_list_variable_still_skipped(mock_can_cls, hass):
    """Test that non-list VARIABLE fields are still skipped."""
    hub, added = _make_hub_for_receive(hass, mock_can_cls)

    msg = _make_message([
        NMEA2000Field("data", "Data", None, None, b"\x01\x02", b"\x01\x02", None, FieldTypes.VARIABLE, False),
    ])
    await hub.receive_callback(msg)

    sensor_ids = [s._attr_unique_id for s in added if hasattr(s, '_attr_unique_id')]
    assert not any("data" in sid for sid in sensor_ids)

