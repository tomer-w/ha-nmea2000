"""Tests for the NMEA2000 config flow."""
import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nmea2000.const import (
    DOMAIN,
    CONF_MODE,
    CONF_MODE_CAN,
    CONF_MODE_TCP,
    CONF_MODE_USB,
    CONF_CAN_INTERFACE,
    CONF_CAN_CHANNEL,
    CONF_CAN_BITRATE,
    CONF_SERIAL_PORT,
    CONF_BAUDRATE,
    CONF_IP,
    CONF_PORT,
    CONF_DEVICE_TYPE,
    CONF_PGN_INCLUDE,
    CONF_PGN_EXCLUDE,
)
from custom_components.nmea2000.config_flow import (
    USB_DATA_SCHEMA,
    TCP_DATA_SCHEMA,
    CAN_DATA_SCHEMA,
    NMEA2000ConfigFlow,
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

async def test_usb_schema_has_serial_port():
    assert CONF_SERIAL_PORT in USB_DATA_SCHEMA.schema
    assert CONF_BAUDRATE in USB_DATA_SCHEMA.schema


async def test_usb_schema_has_no_can_fields():
    keys = [str(k) for k in USB_DATA_SCHEMA.schema]
    assert CONF_CAN_INTERFACE not in keys
    assert CONF_CAN_CHANNEL not in keys
    assert CONF_CAN_BITRATE not in keys


async def test_tcp_schema_has_ip_port():
    assert CONF_IP in TCP_DATA_SCHEMA.schema
    assert CONF_PORT in TCP_DATA_SCHEMA.schema
    assert CONF_DEVICE_TYPE in TCP_DATA_SCHEMA.schema


async def test_tcp_schema_has_no_can_fields():
    keys = [str(k) for k in TCP_DATA_SCHEMA.schema]
    assert CONF_CAN_INTERFACE not in keys
    assert CONF_CAN_CHANNEL not in keys
    assert CONF_CAN_BITRATE not in keys


async def test_can_schema_has_can_fields():
    assert CONF_CAN_INTERFACE in CAN_DATA_SCHEMA.schema
    assert CONF_CAN_CHANNEL in CAN_DATA_SCHEMA.schema
    assert CONF_CAN_BITRATE in CAN_DATA_SCHEMA.schema


async def test_can_schema_has_no_tcp_fields():
    keys = [str(k) for k in CAN_DATA_SCHEMA.schema]
    assert CONF_IP not in keys
    assert CONF_PORT not in keys
    assert CONF_DEVICE_TYPE not in keys


async def test_can_schema_has_no_usb_fields():
    keys = [str(k) for k in CAN_DATA_SCHEMA.schema]
    assert CONF_SERIAL_PORT not in keys
    assert CONF_BAUDRATE not in keys


async def test_can_schema_has_common_fields():
    """CAN schema should have the shared PGN include/exclude fields."""
    keys = [str(k) for k in CAN_DATA_SCHEMA.schema]
    assert CONF_PGN_INCLUDE in keys
    assert CONF_PGN_EXCLUDE in keys


async def test_can_schema_validates_valid_input():
    """CAN schema should accept valid CAN configuration."""
    result = CAN_DATA_SCHEMA({
        CONF_CAN_INTERFACE: "slcan",
        CONF_CAN_CHANNEL: "/dev/ttyUSB0",
        CONF_CAN_BITRATE: 250000,
    })
    assert result[CONF_CAN_INTERFACE] == "slcan"
    assert result[CONF_CAN_CHANNEL] == "/dev/ttyUSB0"
    assert result[CONF_CAN_BITRATE] == 250000


async def test_can_schema_defaults():
    """CAN schema should use correct defaults."""
    result = CAN_DATA_SCHEMA({})
    assert result[CONF_CAN_INTERFACE] == "slcan"
    assert result[CONF_CAN_CHANNEL] == "/dev/ttyUSB0"
    assert result[CONF_CAN_BITRATE] == 250000


# --- _get_schema_for_mode tests ---

async def test_get_schema_for_usb_mode():
    schema = NMEA2000ConfigFlow._get_schema_for_mode(CONF_MODE_USB)
    assert schema is USB_DATA_SCHEMA


async def test_get_schema_for_tcp_mode():
    schema = NMEA2000ConfigFlow._get_schema_for_mode(CONF_MODE_TCP)
    assert schema is TCP_DATA_SCHEMA


async def test_get_schema_for_can_mode():
    schema = NMEA2000ConfigFlow._get_schema_for_mode(CONF_MODE_CAN)
    assert schema is CAN_DATA_SCHEMA


# --- Config flow integration tests ---

async def test_user_step_shows_form(hass):
    """Test that the first step shows a form with name and mode fields."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_user_step_usb_proceeds_to_options(hass):
    """Test selecting USB mode proceeds to the options step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "My NMEA", CONF_MODE: CONF_MODE_USB},
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "options"


async def test_user_step_can_proceeds_to_options(hass):
    """Test selecting CAN mode proceeds to the options step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "My CAN", CONF_MODE: CONF_MODE_CAN},
    )
    assert result2["type"] == FlowResultType.FORM
    assert result2["step_id"] == "options"


async def test_user_step_tcp_proceeds_to_options(hass):
    """Test selecting TCP mode proceeds to the options step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "My TCP", CONF_MODE: CONF_MODE_TCP},
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
        {"name": "CAN Gateway", CONF_MODE: CONF_MODE_CAN},
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
    assert result3["data"][CONF_MODE] == CONF_MODE_CAN
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
        {"name": "USB Gateway", CONF_MODE: CONF_MODE_USB},
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
    assert result3["data"][CONF_MODE] == CONF_MODE_USB


async def test_duplicate_name_rejected(hass):
    """Test that a duplicate name is rejected."""
    # Create first entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"name": "My NMEA", CONF_MODE: CONF_MODE_USB},
    )
    await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        {CONF_SERIAL_PORT: "/dev/ttyUSB0", CONF_BAUDRATE: 2000000},
    )

    # Try creating second entry with same name
    result4 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result5 = await hass.config_entries.flow.async_configure(
        result4["flow_id"],
        {"name": "My NMEA", CONF_MODE: CONF_MODE_USB},
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
        {"name": "Test", CONF_MODE: CONF_MODE_USB},
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
        {"name": "Test", CONF_MODE: CONF_MODE_USB},
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
        data={
            "name": "Test",
            CONF_MODE: CONF_MODE_USB,
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
        data={
            "name": "Test",
            CONF_MODE: CONF_MODE_USB,
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
        data={
            "name": "Test",
            CONF_MODE: CONF_MODE_USB,
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

