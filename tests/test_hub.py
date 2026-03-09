"""Tests for the NMEA2000 Hub."""
import pytest
from unittest.mock import patch, MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry
from nmea2000 import State

from custom_components.nmea2000.const import (
    DOMAIN,
    CONF_MODE,
    CONF_MODE_CAN,
    CONF_MODE_USB,
    CONF_MODE_TCP,
    CONF_CAN_INTERFACE,
    CONF_CAN_CHANNEL,
    CONF_CAN_BITRATE,
    CONF_SERIAL_PORT,
    CONF_BAUDRATE,
    CONF_IP,
    CONF_PORT,
    CONF_DEVICE_TYPE,
)
from custom_components.nmea2000.hub import Hub


def _make_entry(hass, mode, extra_data=None):
    """Create a MockConfigEntry with the given mode and extra data."""
    data = {"name": "Test", CONF_MODE: mode}
    if extra_data:
        data.update(extra_data)
    entry = MockConfigEntry(domain=DOMAIN, data=data)
    entry.add_to_hass(hass)
    return entry


@patch("custom_components.nmea2000.hub.PythonCanAsyncIOClient")
async def test_hub_creates_can_gateway(mock_can_cls, hass):
    """Test Hub creates PythonCanAsyncIOClient for CAN mode."""
    mock_can_cls.return_value = MagicMock()
    mock_can_cls.return_value.set_receive_callback = MagicMock()
    mock_can_cls.return_value.set_status_callback = MagicMock()

    entry = _make_entry(hass, CONF_MODE_CAN, {
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
    """Test Hub creates WaveShareNmea2000Gateway for USB mode."""
    mock_usb_cls.return_value = MagicMock()
    mock_usb_cls.return_value.set_receive_callback = MagicMock()
    mock_usb_cls.return_value.set_status_callback = MagicMock()

    entry = _make_entry(hass, CONF_MODE_USB, {
        CONF_SERIAL_PORT: "/dev/ttyUSB0",
        CONF_BAUDRATE: 2000000,
    })
    Hub(hass, entry)

    mock_usb_cls.assert_called_once()
    assert mock_usb_cls.call_args.kwargs["port"] == "/dev/ttyUSB0"


@patch("custom_components.nmea2000.hub.EByteNmea2000Gateway")
async def test_hub_creates_tcp_ebyte_gateway(mock_tcp_cls, hass):
    """Test Hub creates EByteNmea2000Gateway for TCP/EBYTE mode."""
    mock_tcp_cls.return_value = MagicMock()
    mock_tcp_cls.return_value.set_receive_callback = MagicMock()
    mock_tcp_cls.return_value.set_status_callback = MagicMock()

    entry = _make_entry(hass, CONF_MODE_TCP, {
        CONF_DEVICE_TYPE: "EBYTE",
        CONF_IP: "192.168.1.100",
        CONF_PORT: 8881,
    })
    Hub(hass, entry)

    mock_tcp_cls.assert_called_once()
    assert mock_tcp_cls.call_args.kwargs["host"] == "192.168.1.100"
    assert mock_tcp_cls.call_args.kwargs["port"] == 8881


async def test_hub_rejects_unknown_mode(hass):
    """Test Hub raises an exception for unknown mode."""
    entry = _make_entry(hass, "UNKNOWN_MODE")
    with pytest.raises(Exception, match="not supported"):
        Hub(hass, entry)


@patch("custom_components.nmea2000.hub.PythonCanAsyncIOClient")
async def test_hub_can_gateway_receives_pgn_filters(mock_can_cls, hass):
    """Test CAN gateway receives PGN include/exclude lists."""
    mock_can_cls.return_value = MagicMock()
    mock_can_cls.return_value.set_receive_callback = MagicMock()
    mock_can_cls.return_value.set_status_callback = MagicMock()

    entry = _make_entry(hass, CONF_MODE_CAN, {
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
    mock_instance = MagicMock()
    mock_can_cls.return_value = mock_instance

    entry = _make_entry(hass, CONF_MODE_CAN, {
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
    mock_can_cls.return_value = MagicMock()
    mock_can_cls.return_value.set_receive_callback = MagicMock()
    mock_can_cls.return_value.set_status_callback = MagicMock()

    entry = _make_entry(hass, CONF_MODE_CAN, {
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
    mock_can_cls.return_value = MagicMock()
    mock_can_cls.return_value.set_receive_callback = MagicMock()
    mock_can_cls.return_value.set_status_callback = MagicMock()

    entry = _make_entry(hass, CONF_MODE_CAN, {
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
    mock_can_cls.return_value = MagicMock()
    mock_can_cls.return_value.set_receive_callback = MagicMock()
    mock_can_cls.return_value.set_status_callback = MagicMock()

    entry = _make_entry(hass, CONF_MODE_CAN, {
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

