import itertools
from typing import Any

from homeassistant.components import binary_sensor, sensor
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import State
import pytest

from custom_components.yandex_smart_home import const
from custom_components.yandex_smart_home.helpers import APIError, DictRegistry
from custom_components.yandex_smart_home.property_custom import (
    EVENT_PROPERTIES_REGISTRY,
    FLOAT_PROPERTIES_REGISTRY,
    get_custom_property,
)
from custom_components.yandex_smart_home.schema import (
    EventPropertyInstance,
    FloatPropertyInstance,
    PropertyType,
    ResponseCode,
)

from . import BASIC_ENTRY_DATA

ALL_INSTANCES = set(
    map(str, itertools.chain(*[v.__members__.values() for v in (EventPropertyInstance, FloatPropertyInstance)]))
)


@pytest.mark.parametrize(
    "registry,instance",
    ((FLOAT_PROPERTIES_REGISTRY, FloatPropertyInstance), (EVENT_PROPERTIES_REGISTRY, EventPropertyInstance)),
)
def test_property_custom_registry(registry: DictRegistry[Any], instance):
    assert set(instance.__members__.values()) == set(registry.keys())


@pytest.mark.parametrize("domain", [sensor.DOMAIN, binary_sensor.DOMAIN])
@pytest.mark.parametrize("instance", ALL_INSTANCES)
async def test_property_custom(hass, domain, instance):
    state = State(f"{domain}.test", "10")
    hass.states.async_set(state.entity_id, state.state)

    if domain == binary_sensor.DOMAIN and instance in [
        "humidity",
        "temperature",
        "pressure",
        "co2_level",
        "power",
        "voltage",
        "amperage",
        "illumination",
        "tvoc",
        "pm1_density",
        "pm2.5_density",
        "pm10_density",
    ]:
        with pytest.raises(APIError) as e:
            get_custom_property(hass, BASIC_ENTRY_DATA, {const.CONF_ENTITY_PROPERTY_TYPE: instance}, state.entity_id)

        assert e.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE
        assert e.value.message == f"Unsupported entity {domain}.test for {instance} instance of {state.entity_id}"
        return

    prop = get_custom_property(hass, BASIC_ENTRY_DATA, {const.CONF_ENTITY_PROPERTY_TYPE: instance}, state.entity_id)
    if instance in ["vibration", "open", "button", "motion", "smoke", "gas", "water_leak"]:
        assert prop.type == PropertyType.EVENT
    else:
        if domain == binary_sensor.DOMAIN and instance in ["water_level", "battery_level"]:
            assert prop.type == PropertyType.EVENT
        else:
            assert prop.type == PropertyType.FLOAT

    assert prop.parameters.dict()["instance"] == instance

    if prop.type == PropertyType.FLOAT:
        assert prop.parameters.dict()["unit"] is not None

    if prop.type == PropertyType.EVENT:
        assert len(prop.parameters.dict()["events"]) != 0

    if instance in ["button", "vibration"]:
        assert prop.retrievable is False
    else:
        assert prop.retrievable is True


async def test_property_custom_get_value_button_event(hass):
    state = State("sensor.button", "")
    hass.states.async_set(state.entity_id, state.state)

    prop = get_custom_property(
        hass,
        BASIC_ENTRY_DATA,
        {
            const.CONF_ENTITY_PROPERTY_TYPE: "button",
        },
        state.entity_id,
    )
    assert prop.get_value() is None

    hass.states.async_set(state.entity_id, "", {"action": "foo"})
    prop = get_custom_property(
        hass,
        BASIC_ENTRY_DATA,
        {const.CONF_ENTITY_PROPERTY_TYPE: "button", const.CONF_ENTITY_PROPERTY_ATTRIBUTE: "action"},
        state.entity_id,
    )
    assert prop.get_value() is None

    hass.states.async_set(state.entity_id, "", {"action": "long_click_press"})
    prop = get_custom_property(
        hass,
        BASIC_ENTRY_DATA,
        {const.CONF_ENTITY_PROPERTY_TYPE: "button", const.CONF_ENTITY_PROPERTY_ATTRIBUTE: "action"},
        state.entity_id,
    )
    assert prop.get_value() == "long_press"


async def test_property_custom_get_value_binary_event(hass):
    state = State("binary_sensor.test", STATE_UNAVAILABLE)
    hass.states.async_set(state.entity_id, state.state)

    prop = get_custom_property(
        hass,
        BASIC_ENTRY_DATA,
        {
            const.CONF_ENTITY_PROPERTY_TYPE: "gas",
        },
        state.entity_id,
    )
    assert prop.get_value() is None

    hass.states.async_set(state.entity_id, STATE_ON)
    prop = get_custom_property(
        hass,
        BASIC_ENTRY_DATA,
        {
            const.CONF_ENTITY_PROPERTY_TYPE: "gas",
        },
        state.entity_id,
    )
    assert prop.get_value() == "detected"


async def test_property_custom_get_value_float(hass):
    state = State("sensor.test", "3.36")
    hass.states.async_set(state.entity_id, state.state)

    prop = get_custom_property(
        hass,
        BASIC_ENTRY_DATA,
        {
            const.CONF_ENTITY_PROPERTY_TYPE: "temperature",
        },
        state.entity_id,
    )
    assert prop.get_value() == 3.36

    for s in ["", "-", "none", "unknown"]:
        hass.states.async_set(state.entity_id, s)
        assert prop.get_value() is None

    hass.states.async_set(state.entity_id, "not-a-number")
    with pytest.raises(APIError) as e:
        prop.get_value()
    assert e.value.code == ResponseCode.NOT_SUPPORTED_IN_CURRENT_MODE
    assert e.value.message == "Unsupported value 'not-a-number' for instance temperature of sensor.test"

    prop = get_custom_property(
        hass,
        BASIC_ENTRY_DATA,
        {
            const.CONF_ENTITY_PROPERTY_TYPE: "temperature",
            const.CONF_ENTITY_PROPERTY_ATTRIBUTE: "value",
        },
        state.entity_id,
    )
    prop.get_value()
    assert prop.get_value() is None
    hass.states.async_set(state.entity_id, "not-a-number", {"value": "55"})
    assert prop.get_value() == 55

    prop = get_custom_property(
        hass,
        BASIC_ENTRY_DATA,
        {
            const.CONF_ENTITY_PROPERTY_TYPE: "temperature",
            const.CONF_ENTITY_PROPERTY_ENTITY: "sensor.test_2",
        },
        state.entity_id,
    )
    assert prop.get_value() is None
    hass.states.async_set("sensor.test_2", "4.52")
    assert prop.get_value() == 4.52

    hass.states.async_set("sensor.test_2", "4.52", {"value": 9.99})
    prop = get_custom_property(
        hass,
        BASIC_ENTRY_DATA,
        {
            const.CONF_ENTITY_PROPERTY_TYPE: "temperature",
            const.CONF_ENTITY_PROPERTY_ENTITY: "sensor.test_2",
            const.CONF_ENTITY_PROPERTY_ATTRIBUTE: "value",
        },
        state.entity_id,
    )
    assert prop.get_value() == 9.99


async def test_property_custom_value_float_limit(hass):
    state = State("sensor.test", "-5")
    hass.states.async_set(state.entity_id, state.state)

    prop = get_custom_property(
        hass,
        BASIC_ENTRY_DATA,
        {
            const.CONF_ENTITY_PROPERTY_TYPE: "battery_level",
        },
        state.entity_id,
    )
    assert prop.get_value() == 0


@pytest.mark.parametrize(
    "instance,unit_of_measurement,unit,value",
    [
        ("pressure", "bar", "unit.pressure.mmhg", 75006.16),
        ("tvoc", "ppb", "unit.density.mcg_m3", 449.63),
        ("amperage", "mA", "unit.ampere", 0.1),
        ("voltage", "mV", "unit.volt", 0.1),
        ("temperature", "K", "unit.temperature.celsius", -173.15),
        ("humidity", "x", "unit.percent", 100),
    ],
)
async def test_property_custom_get_value_float_conversion(hass, instance, unit_of_measurement, unit, value):
    state = State("sensor.test", "100")
    hass.states.async_set(state.entity_id, state.state)
    hass.states.async_set("climate.test", STATE_ON, {ATTR_UNIT_OF_MEASUREMENT: unit_of_measurement, "t": 100})

    prop = get_custom_property(
        hass,
        BASIC_ENTRY_DATA,
        {
            const.CONF_ENTITY_PROPERTY_TYPE: instance,
            const.CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT: unit_of_measurement,
        },
        state.entity_id,
    )
    assert prop.parameters.dict()["unit"] == unit
    assert prop.get_value() == value

    hass.states.async_set(state.entity_id, STATE_UNAVAILABLE)
    assert prop.get_value() is None

    state = State("sensor.test_with_uom", "100", {ATTR_UNIT_OF_MEASUREMENT: unit_of_measurement})
    hass.states.async_set(state.entity_id, state.state, state.attributes)
    prop = get_custom_property(hass, BASIC_ENTRY_DATA, {const.CONF_ENTITY_PROPERTY_TYPE: instance}, state.entity_id)
    assert prop.parameters.dict()["unit"] == unit
    assert prop.get_value() == value

    # ignore unit_of_measurement when use attribute
    prop = get_custom_property(
        hass,
        BASIC_ENTRY_DATA,
        {
            const.CONF_ENTITY_PROPERTY_TYPE: instance,
            const.CONF_ENTITY_PROPERTY_ENTITY: "climate.test",
            const.CONF_ENTITY_PROPERTY_ATTRIBUTE: "t",
        },
        state.entity_id,
    )
    assert prop.parameters.dict()["unit"] == unit
    assert prop.get_value() == 100

    # override unit_of_measurement when use attribute
    prop = get_custom_property(
        hass,
        BASIC_ENTRY_DATA,
        {
            const.CONF_ENTITY_PROPERTY_TYPE: instance,
            const.CONF_ENTITY_PROPERTY_ENTITY: "climate.test",
            const.CONF_ENTITY_PROPERTY_ATTRIBUTE: "t",
            const.CONF_ENTITY_PROPERTY_UNIT_OF_MEASUREMENT: unit_of_measurement,
        },
        state.entity_id,
    )
    assert prop.parameters.dict()["unit"] == unit
    assert prop.get_value() == value
