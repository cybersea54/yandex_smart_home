from homeassistant.components import binary_sensor, input_text, sensor
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS, STATE_OFF, STATE_ON
from homeassistant.core import State
import pytest

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.schema import EventPropertyInstance, PropertyType

from . import BASIC_ENTRY_DATA, MockConfigEntryData
from .test_property import assert_no_properties, get_exact_one_property


@pytest.mark.parametrize(
    "device_class,supported",
    [
        (BinarySensorDeviceClass.DOOR, True),
        (BinarySensorDeviceClass.GARAGE_DOOR, True),
        (BinarySensorDeviceClass.WINDOW, True),
        (BinarySensorDeviceClass.OPENING, True),
        (BinarySensorDeviceClass.BATTERY, False),
    ],
)
async def test_state_property_event_open(hass, device_class, supported):
    state = State("binary_sensor.test", binary_sensor.STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.OPEN)
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.OPEN)
        return

    assert prop.retrievable is True
    assert prop.parameters == {"events": [{"value": "opened"}, {"value": "closed"}], "instance": "open"}
    assert prop.get_value() == "opened"
    prop.state.state = STATE_OFF
    assert prop.get_value() == "closed"


@pytest.mark.parametrize(
    "device_class,supported",
    [
        (BinarySensorDeviceClass.MOTION, True),
        (BinarySensorDeviceClass.OCCUPANCY, True),
        (BinarySensorDeviceClass.PRESENCE, True),
        (BinarySensorDeviceClass.BATTERY, False),
    ],
)
async def test_state_property_event_motion(hass, device_class, supported):
    state = State("binary_sensor.test", binary_sensor.STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.MOTION)
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.OPEN)
        return

    assert prop.retrievable is True
    assert prop.parameters == {"events": [{"value": "detected"}, {"value": "not_detected"}], "instance": "motion"}
    assert prop.get_value() == "detected"
    prop.state.state = STATE_OFF
    assert prop.get_value() == "not_detected"


@pytest.mark.parametrize(
    "device_class,supported",
    [
        (BinarySensorDeviceClass.GAS, True),
        (BinarySensorDeviceClass.BATTERY, False),
    ],
)
async def test_state_property_event_gas(hass, device_class, supported):
    state = State("binary_sensor.test", binary_sensor.STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.GAS)
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.GAS)
        return

    assert prop.retrievable is True
    assert prop.parameters == {
        "events": [{"value": "detected"}, {"value": "not_detected"}, {"value": "high"}],
        "instance": "gas",
    }
    assert prop.get_value() == "detected"
    prop.state.state = STATE_OFF
    assert prop.get_value() == "not_detected"
    prop.state.state = "high"
    assert prop.get_value() == "high"


@pytest.mark.parametrize(
    "device_class,supported",
    [
        (BinarySensorDeviceClass.SMOKE, True),
        (BinarySensorDeviceClass.BATTERY, False),
    ],
)
async def test_state_property_event_smoke(hass, device_class, supported):
    state = State("binary_sensor.test", binary_sensor.STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.SMOKE)
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.SMOKE)
        return

    assert prop.retrievable is True
    assert prop.parameters == {
        "events": [{"value": "detected"}, {"value": "not_detected"}, {"value": "high"}],
        "instance": "smoke",
    }
    assert prop.get_value() == "detected"
    prop.state.state = STATE_OFF
    assert prop.get_value() == "not_detected"
    prop.state.state = "high"
    assert prop.get_value() == "high"


@pytest.mark.parametrize(
    "device_class,supported",
    [
        (BinarySensorDeviceClass.BATTERY, True),
        (BinarySensorDeviceClass.SMOKE, False),
    ],
)
async def test_state_property_event_battery(hass, device_class, supported):
    state = State("binary_sensor.test", binary_sensor.STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(
            hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.BATTERY_LEVEL
        )
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.BATTERY_LEVEL)
        return

    assert prop.retrievable is True
    assert prop.parameters == {
        "events": [{"value": "low"}, {"value": "normal"}, {"value": "high"}],
        "instance": "battery_level",
    }
    assert prop.get_value() == "low"
    prop.state.state = STATE_OFF
    assert prop.get_value() == "normal"


@pytest.mark.parametrize(
    "device_class,supported",
    [
        ("water_level", True),
        (BinarySensorDeviceClass.SMOKE, False),
    ],
)
async def test_state_property_event_water_level(hass, device_class, supported):
    state = State("binary_sensor.test", binary_sensor.STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.FLOAT, EventPropertyInstance.WATER_LEVEL)
    if supported:
        prop = get_exact_one_property(
            hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.WATER_LEVEL
        )
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.WATER_LEVEL)
        return

    assert prop.retrievable is True
    assert prop.parameters == {
        "events": [{"value": "empty"}, {"value": "low"}, {"value": "normal"}],
        "instance": "water_level",
    }
    assert prop.get_value() == "low"
    prop.state.state = STATE_OFF
    assert prop.get_value() == "normal"


@pytest.mark.parametrize(
    "device_class,supported",
    [
        (BinarySensorDeviceClass.MOISTURE, True),
        (BinarySensorDeviceClass.SMOKE, False),
    ],
)
async def test_state_property_event_water_leak(hass, device_class, supported):
    state = State("binary_sensor.test", binary_sensor.STATE_ON, {ATTR_DEVICE_CLASS: device_class})
    if supported:
        prop = get_exact_one_property(
            hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.WATER_LEAK
        )
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.WATER_LEAK)
        return

    assert prop.retrievable
    assert prop.parameters == {"events": [{"value": "dry"}, {"value": "leak"}], "instance": "water_leak"}
    assert prop.get_value() == "leak"
    prop.state.state = STATE_OFF
    assert prop.get_value() == "dry"


@pytest.mark.parametrize(
    "domain,attribute,device_class,supported",
    [
        (binary_sensor.DOMAIN, "last_action", None, True),
        (binary_sensor.DOMAIN, "none", None, False),
        (sensor.DOMAIN, "action", None, True),
    ],
)
async def test_state_property_event_button_sensor_attribute(hass, domain, attribute, device_class, supported):
    entity_id = f"{domain}.test"

    state = State(entity_id, STATE_ON, {attribute: "single", ATTR_DEVICE_CLASS: device_class})
    assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.VIBRATION)
    if supported:
        prop = get_exact_one_property(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)
        return

    assert prop.retrievable is False
    assert prop.parameters == {
        "events": [{"value": "click"}, {"value": "double_click"}, {"value": "long_press"}],
        "instance": "button",
    }
    assert prop.get_value() == "click"

    prop.state = State(entity_id, STATE_ON, {attribute: "double"})
    assert prop.get_value() == "double_click"

    prop.state = State(entity_id, STATE_ON, {attribute: "hold"})
    assert prop.get_value() == "long_press"

    prop.state = State(entity_id, STATE_ON, {attribute: "invalid"})
    assert prop.get_value() is None

    prop.state = State(entity_id, "click")
    assert prop.get_value() == "click"


@pytest.mark.parametrize("domain", [sensor.DOMAIN, input_text.DOMAIN])
@pytest.mark.parametrize(
    "device_class,mock_entry_data,supported",
    [
        (None, False, False),
        (None, True, True),
        ("button", False, True),
    ],
)
async def test_state_property_event_button_sensor_state(hass, domain, device_class, mock_entry_data, supported):
    entity_id = f"{domain}.test"
    entry_data = BASIC_ENTRY_DATA
    if mock_entry_data:
        entry_data = MockConfigEntryData(
            entity_config={entity_id: {const.CONF_DEVICE_CLASS: const.DEVICE_CLASS_BUTTON}}
        )

    state = State(entity_id, "click", {ATTR_DEVICE_CLASS: device_class})
    assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.VIBRATION)
    if supported:
        prop = get_exact_one_property(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)
    else:
        assert_no_properties(hass, entry_data, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)
        return

    assert not prop.retrievable
    assert prop.parameters == {
        "events": [{"value": "click"}, {"value": "double_click"}, {"value": "long_press"}],
        "instance": "button",
    }
    assert prop.get_value() == "click"

    prop.state = State(entity_id, "double")
    assert prop.get_value() == "double_click"

    prop.state = State(entity_id, "hold")
    assert prop.get_value() == "long_press"

    prop.state = State(entity_id, "invalid")
    assert prop.get_value() is None


@pytest.mark.parametrize(
    "domain,attribute,device_class,supported",
    [
        (binary_sensor.DOMAIN, "last_action", None, True),
        (sensor.DOMAIN, "action", None, True),
        (binary_sensor.DOMAIN, None, BinarySensorDeviceClass.VIBRATION, True),
        (binary_sensor.DOMAIN, "bar", None, False),
    ],
)
async def test_state_property_event_vibration_sensor(hass, domain, attribute, device_class, supported):
    attributes = {}
    if attribute:
        attributes[attribute] = "vibrate"
    if device_class:
        attributes[ATTR_DEVICE_CLASS] = device_class

    state = State(f"{domain}.test", STATE_ON, attributes)
    assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.BUTTON)

    if supported:
        prop = get_exact_one_property(
            hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.VIBRATION
        )
    else:
        assert_no_properties(hass, BASIC_ENTRY_DATA, state, PropertyType.EVENT, EventPropertyInstance.VIBRATION)
        return

    assert not prop.retrievable
    assert prop.parameters == {
        "events": [{"value": "tilt"}, {"value": "fall"}, {"value": "vibration"}],
        "instance": "vibration",
    }
    assert prop.get_value() == "vibration"

    if attribute:
        prop.state = State(f"{domain}.test", STATE_ON, {attribute: "flip90"})
        assert prop.get_value() == "tilt"

        prop.state = State(f"{domain}.test", STATE_ON, {attribute: "free_fall"})
        assert prop.get_value() == "fall"

        prop.state = State(f"{domain}.test", STATE_ON, {attribute: "invalid"})
        assert prop.get_value() is None

    if device_class:
        prop.state = State(f"{domain}.test", STATE_OFF, {ATTR_DEVICE_CLASS: device_class})
        assert prop.get_value() is None
