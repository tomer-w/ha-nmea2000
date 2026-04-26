"""Tests for the NMEA2000 Hub."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry
from nmea2000 import State

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

