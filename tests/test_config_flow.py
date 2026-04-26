"""Tests for the NMEA2000 config flow."""
import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nmea2000.const import (
    DOMAIN,
    CONF_CAN_INTERFACE,
    CONF_CAN_CHANNEL,
    CONF_CAN_BITRATE,
    CONF_SERIAL_PORT,
    CONF_BAUDRATE,
    CONF_IP,
    CONF_PORT,
    CONF_PGN_INCLUDE,
    CONF_PGN_EXCLUDE,
)
from custom_components.nmea2000.config_flow import (
    CONF_GATEWAY_TYPE,
    GatewayType,
    NMEA2000ConfigFlow,
    _build_options_schema,
    _resolve_gateway_type,
    parse_and_validate_comma_separated_integers,
)


# --- parse_and_validate_comma_separated_integers tests ---

async def test_parse_valid_integers():
    result = parse_and_validate_comma_separated_integers("127250, 127489, 130306")
    assert result == [127250, 127489, 130306]


async def test_parse_single_integer():
    result = parse_and_validate_comma_separated_integers("60928")
    assert result == [60928]


async def test_parse_empty_string():
    result = parse_and_validate_comma_separated_integers("")
    assert result == []


async def test_parse_whitespace_string():
    result = parse_and_validate_comma_separated_integers("   ")
    assert result == []


async def test_parse_invalid_value_raises():
    with pytest.raises(ValueError, match="Invalid pgn value"):
        parse_and_validate_comma_separated_integers("127250, abc, 130306")


# --- Schema field presence tests ---

async def test_serial_schema_has_serial_fields():
    schema = _build_options_schema(GatewayType.WAVESHARE)
    keys = [str(k) for k in schema.schema]
    assert CONF_SERIAL_PORT in keys
    assert CONF_BAUDRATE in keys
    assert CONF_CAN_INTERFACE not in keys
    assert CONF_IP not in keys


async def test_tcp_schema_has_ip_port():
    for gt in (GatewayType.EBYTE, GatewayType.TEXT, GatewayType.ACTISENSE_BST):
        schema = _build_options_schema(gt)
        keys = [str(k) for k in schema.schema]
        assert CONF_IP in keys, f"{gt} missing ip"
        assert CONF_PORT in keys, f"{gt} missing port"
        assert CONF_SERIAL_PORT not in keys, f"{gt} has serial_port"
        assert CONF_CAN_INTERFACE not in keys, f"{gt} has can_interface"


async def test_can_schema_has_can_fields():
    schema = _build_options_schema(GatewayType.PYTHON_CAN)
    keys = [str(k) for k in schema.schema]
    assert CONF_CAN_INTERFACE in keys
    assert CONF_CAN_CHANNEL in keys
    assert CONF_CAN_BITRATE in keys
    assert CONF_IP not in keys
    assert CONF_SERIAL_PORT not in keys


async def test_all_schemas_have_common_fields():
    for gt in GatewayType:
        schema = _build_options_schema(gt)
        keys = [str(k) for k in schema.schema]
        assert CONF_PGN_INCLUDE in keys, f"{gt} missing pgn_include"
        assert CONF_PGN_EXCLUDE in keys, f"{gt} missing pgn_exclude"


async def test_can_schema_validates_valid_input():
    schema = _build_options_schema(GatewayType.PYTHON_CAN)
    result = schema({
        CONF_CAN_INTERFACE: "slcan",
        CONF_CAN_CHANNEL: "/dev/ttyUSB0",
        CONF_CAN_BITRATE: 250000,
    })
    assert result[CONF_CAN_INTERFACE] == "slcan"
    assert result[CONF_CAN_CHANNEL] == "/dev/ttyUSB0"
    assert result[CONF_CAN_BITRATE] == 250000


async def test_can_schema_defaults():
    schema = _build_options_schema(GatewayType.PYTHON_CAN)
    result = schema({})
    assert result[CONF_CAN_INTERFACE] == "slcan"
    assert result[CONF_CAN_CHANNEL] == "/dev/ttyUSB0"
    assert result[CONF_CAN_BITRATE] == 250000


# --- _resolve_gateway_type tests ---

async def test_resolve_new_config():
    for gt in GatewayType:
        assert _resolve_gateway_type({CONF_GATEWAY_TYPE: gt.value}) == gt


# --- Config flow integration tests ---

async def test_user_step_shows_form(hass):
    """Test that the first step shows a form with name and gateway_type fields."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


@pytest.mark.parametrize("gateway_type", [gt.value for gt in GatewayType])
async def test_user_step_proceeds_to_options(hass, gateway_type):
    """Test selecting any gateway type proceeds to the options step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": f"Test {gateway_type}", CONF_GATEWAY_TYPE: gateway_type},
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "options"


async def test_full_can_flow_creates_entry(hass):
    """Test completing the full CAN config flow creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "CAN Gateway", CONF_GATEWAY_TYPE: GatewayType.PYTHON_CAN.value},
    )
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {
            CONF_CAN_INTERFACE: "socketcan",
            CONF_CAN_CHANNEL: "can0",
            CONF_CAN_BITRATE: 250000,
        },
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert result3["title"] == "CAN Gateway"
    assert result3["data"][CONF_GATEWAY_TYPE] == GatewayType.PYTHON_CAN.value
    assert result3["data"][CONF_CAN_INTERFACE] == "socketcan"
    assert result3["data"][CONF_CAN_CHANNEL] == "can0"
    assert result3["data"][CONF_CAN_BITRATE] == 250000


async def test_full_usb_flow_creates_entry(hass):
    """Test completing the full USB config flow creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "USB Gateway", CONF_GATEWAY_TYPE: GatewayType.WAVESHARE.value},
    )
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            CONF_BAUDRATE: 2000000,
        },
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert result3["title"] == "USB Gateway"
    assert result3["data"][CONF_GATEWAY_TYPE] == GatewayType.WAVESHARE.value


async def test_full_tcp_text_flow_creates_entry(hass):
    """Test completing the full Text TCP config flow creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Text Gateway", CONF_GATEWAY_TYPE: GatewayType.TEXT.value},
    )
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {
            CONF_IP: "192.168.1.100",
            CONF_PORT: 2000,
        },
    )
    assert result3["type"] == FlowResultType.CREATE_ENTRY
    assert result3["title"] == "Text Gateway"
    assert result3["data"][CONF_GATEWAY_TYPE] == GatewayType.TEXT.value
    assert result3["data"][CONF_IP] == "192.168.1.100"
    assert result3["data"][CONF_PORT] == 2000


async def test_duplicate_name_rejected(hass):
    """Test that a duplicate name is rejected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "My NMEA", CONF_GATEWAY_TYPE: GatewayType.WAVESHARE.value},
    )
    await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {CONF_SERIAL_PORT: "/dev/ttyUSB0", CONF_BAUDRATE: 2000000},
    )

    result4 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result5 = await hass.config_entries.flow.async_configure(
        result4["flow_id"],
        {"name": "My NMEA", CONF_GATEWAY_TYPE: GatewayType.WAVESHARE.value},
    )
    assert result5["type"] == FlowResultType.FORM
    assert result5["errors"]["name"] == "name_exists"


async def test_invalid_pgn_include_rejected(hass):
    """Test that invalid PGN include value shows error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Test", CONF_GATEWAY_TYPE: GatewayType.WAVESHARE.value},
    )
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            CONF_BAUDRATE: 2000000,
            CONF_PGN_INCLUDE: "abc",
        },
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["errors"][CONF_PGN_INCLUDE] == "pgn_not_valid"


async def test_both_pgn_include_and_exclude_rejected(hass):
    """Test that providing both PGN include and exclude shows error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "Test", CONF_GATEWAY_TYPE: GatewayType.WAVESHARE.value},
    )
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            CONF_BAUDRATE: 2000000,
            CONF_PGN_INCLUDE: "127250",
            CONF_PGN_EXCLUDE: "130306",
        },
    )
    assert result3["type"] == FlowResultType.FORM
    assert result3["errors"][CONF_PGN_EXCLUDE] == "include_exclude_only_one"


# --- Options flow tests ---

async def test_options_flow_shows_form(hass):
    """Test that the options flow shows a form for existing entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "name": "Test",
            CONF_GATEWAY_TYPE: GatewayType.WAVESHARE.value,
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            CONF_BAUDRATE: 2000000,
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_updates_entry(hass):
    """Test that the options flow updates the config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "name": "Test",
            CONF_GATEWAY_TYPE: GatewayType.WAVESHARE.value,
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            CONF_BAUDRATE: 2000000,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SERIAL_PORT: "/dev/ttyUSB1",
            CONF_BAUDRATE: 115200,
        },
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY


async def test_options_flow_rejects_invalid_pgn(hass):
    """Test that the options flow rejects invalid PGN values."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            "name": "Test",
            CONF_GATEWAY_TYPE: GatewayType.WAVESHARE.value,
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            CONF_BAUDRATE: 2000000,
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            CONF_BAUDRATE: 2000000,
            CONF_PGN_INCLUDE: "not_a_number",
        },
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"][CONF_PGN_INCLUDE] == "pgn_not_valid"


# --- Migration tests ---

async def test_migration_usb_to_waveshare(hass):
    """Test v1 USB config migrates to v2 waveshare gateway_type."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={
            "name": "USB Device",
            "mode": "USB",
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            CONF_BAUDRATE: 2000000,
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.data[CONF_GATEWAY_TYPE] == "waveshare"
    assert "mode" not in entry.data
    assert CONF_SERIAL_PORT in entry.data


async def test_migration_tcp_ebyte(hass):
    """Test v1 TCP/EBYTE config migrates to v2 ebyte gateway_type."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={
            "name": "EByte",
            "mode": "TCP",
            "device_type": "EBYTE",
            CONF_IP: "192.168.1.100",
            CONF_PORT: 8881,
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.data[CONF_GATEWAY_TYPE] == "ebyte"
    assert "mode" not in entry.data
    assert "device_type" not in entry.data


@pytest.mark.parametrize("device_type", ["Actisense", "Yacht Devices", "TCP"])
async def test_migration_tcp_text_variants(hass, device_type):
    """Test v1 TCP text-based configs migrate to v2 text gateway_type."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={
            "name": f"Test {device_type}",
            "mode": "TCP",
            "device_type": device_type,
            CONF_IP: "192.168.1.100",
            CONF_PORT: 2000,
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.data[CONF_GATEWAY_TYPE] == "text"
    assert "mode" not in entry.data
    assert "device_type" not in entry.data


async def test_migration_can_to_python_can(hass):
    """Test v1 CAN config migrates to v2 python_can gateway_type."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={
            "name": "CAN Device",
            "mode": "CAN",
            CONF_CAN_INTERFACE: "socketcan",
            CONF_CAN_CHANNEL: "can0",
            CONF_CAN_BITRATE: 250000,
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 2
    assert entry.data[CONF_GATEWAY_TYPE] == "python_can"
    assert "mode" not in entry.data

