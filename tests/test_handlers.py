import json
from unittest.mock import Mock, patch

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import Context, State
from homeassistant.helpers.template import Template
from homeassistant.util.decorator import Registry

from custom_components.yandex_smart_home import YandexSmartHome, handlers
from custom_components.yandex_smart_home.capability_onoff import OnOffCapability
from custom_components.yandex_smart_home.capability_toggle import StateToggleCapability
from custom_components.yandex_smart_home.const import CONF_DEVICES_DISCOVERED, DOMAIN, EVENT_DEVICE_ACTION
from custom_components.yandex_smart_home.handlers import PING_REQUEST_USER_ID
from custom_components.yandex_smart_home.helpers import APIError, RequestData
from custom_components.yandex_smart_home.schema import (
    CapabilityType,
    GetStreamInstanceActionResultValue,
    OnOffCapabilityInstance,
    OnOffCapabilityInstanceActionState,
    ResponseCode,
    ToggleCapabilityInstance,
    ToggleCapabilityInstanceActionState,
)

from . import BASIC_REQUEST_DATA, REQ_ID, MockConfigEntryData, generate_entity_filter


async def test_handle_request(hass, caplog):
    r = Registry()

    @r.register("error")
    async def error(*_, **__):
        raise APIError(ResponseCode.INVALID_ACTION, "foo")

    @r.register("exception")
    async def exception(*_, **__):
        raise ValueError("boooo")

    @r.register("none")
    async def none(*_, **__):
        return None

    with patch("custom_components.yandex_smart_home.handlers.HANDLERS", r):
        assert (await handlers.async_handle_request(hass, BASIC_REQUEST_DATA, "missing", "")).as_dict() == {
            "request_id": REQ_ID,
            "payload": {"error_code": "INTERNAL_ERROR"},
        }
        assert caplog.messages == ["Unexpected action 'missing'"]
        caplog.clear()

        assert (await handlers.async_handle_request(hass, BASIC_REQUEST_DATA, "error", "")).as_dict() == {
            "request_id": REQ_ID,
            "payload": {"error_code": "INVALID_ACTION"},
        }
        assert caplog.messages == ["foo (INVALID_ACTION)"]
        caplog.clear()

        assert (await handlers.async_handle_request(hass, BASIC_REQUEST_DATA, "exception", "")).as_dict() == {
            "request_id": REQ_ID,
            "payload": {"error_code": "INTERNAL_ERROR"},
        }
        assert caplog.records[-1].message == "Unexpected exception"
        assert "boooo" in caplog.records[-1].exc_text
        caplog.clear()

        assert (await handlers.async_handle_request(hass, BASIC_REQUEST_DATA, "none", "")).as_dict() == {
            "request_id": REQ_ID,
        }


async def test_handler_devices_query(hass, caplog):
    switch_1 = State("switch.test_1", STATE_OFF)
    switch_not_expose = State("switch.not_expose", STATE_ON)
    sensor = State("sensor.test", "33")
    hass.states.async_set(switch_1.entity_id, switch_1.state, switch_1.attributes)
    hass.states.async_set(switch_not_expose.entity_id, switch_not_expose.state, switch_not_expose.attributes)
    hass.states.async_set(sensor.entity_id, sensor.state, sensor.attributes)

    entry_data = MockConfigEntryData(entity_filter=generate_entity_filter(exclude_entities=["switch.not_expose"]))
    data = RequestData(entry_data, Context(), PING_REQUEST_USER_ID, REQ_ID)
    payload = json.dumps(
        {"devices": [{"id": switch_1.entity_id}, {"id": switch_not_expose.entity_id}, {"id": "invalid.foo"}]}
    )

    assert (await handlers.async_devices_query(hass, data, payload)).as_dict() == {
        "devices": [
            {
                "id": "switch.test_1",
                "capabilities": [{"type": "devices.capabilities.on_off", "state": {"instance": "on", "value": False}}],
                "properties": [],
            },
            {
                "id": "switch.not_expose",
                "capabilities": [{"type": "devices.capabilities.on_off", "state": {"instance": "on", "value": True}}],
                "properties": [],
            },
            {"id": "invalid.foo", "error_code": "DEVICE_UNREACHABLE"},
        ]
    }
    assert (await handlers.async_device_list(hass, data, "")).as_dict() == {
        "user_id": "ping",
        "devices": [
            {
                "id": "switch.test_1",
                "name": "test 1",
                "type": "devices.types.switch",
                "capabilities": [{"type": "devices.capabilities.on_off", "retrievable": True, "reportable": True}],
                "device_info": {"model": "switch.test_1"},
            }
        ],
    }

    assert caplog.messages[-3:] == [
        "State requested for unexposed entity switch.not_expose. Please either expose the entity via filters in "
        "component configuration or delete the device from Yandex.",
        "State requested for unexposed entity invalid.foo. Please either expose the entity via filters in component "
        "configuration or delete the device from Yandex.",
        "Missing capabilities and properties for sensor.test",
    ]


async def test_handler_devices_discovery(hass_platform_direct):
    hass = hass_platform_direct
    component: YandexSmartHome = hass.data[DOMAIN]
    entry_data = component.get_direct_connection_entry_data()
    assert entry_data.entry.data.get(CONF_DEVICES_DISCOVERED) is None

    with patch("homeassistant.config_entries.ConfigEntries.async_update_entry") as mock_update_entry:
        await handlers.async_device_list(hass, RequestData(entry_data, Context(), PING_REQUEST_USER_ID, REQ_ID), "")
        mock_update_entry.assert_not_called()

        await handlers.async_device_list(hass, RequestData(entry_data, Context(), "foo", REQ_ID), "")
        mock_update_entry.assert_called_once()

    await handlers.async_device_list(hass, RequestData(entry_data, Context(), "foo", REQ_ID), "")
    assert entry_data.entry.data.get(CONF_DEVICES_DISCOVERED) is True

    with patch("homeassistant.config_entries.ConfigEntries.async_update_entry") as mock_update_entry:
        await handlers.async_device_list(hass, RequestData(entry_data, Context(), "foo", REQ_ID), "")
        mock_update_entry.assert_not_called()


async def test_handler_devices_action(hass, caplog):
    class MockCapability(StateToggleCapability):
        @property
        def supported(self) -> bool:
            return True

        def get_value(self) -> bool | None:
            return None

        async def set_instance_state(self, context: Context, state: ToggleCapabilityInstanceActionState) -> None:
            pass

    class MockCapabilityA(MockCapability):
        instance = ToggleCapabilityInstance.PAUSE

    class MockCapabilityReturnState(MockCapability):
        instance = ToggleCapabilityInstance.BACKLIGHT

        async def set_instance_state(self, *_, **__):
            return GetStreamInstanceActionResultValue(stream_url="foo", protocol="hls")

    class MockCapabilityFail(MockCapability):
        instance = ToggleCapabilityInstance.IONIZATION

        async def set_instance_state(self, *_, **__):
            raise Exception("fail set_state")

    class MockCapabilityUnsupported(MockCapability):
        instance = ToggleCapabilityInstance.KEEP_WARM

        @property
        def supported(self) -> bool:
            return False

    switch_1 = State("switch.test_1", STATE_OFF)
    switch_2 = State("switch.test_2", STATE_OFF)
    switch_3 = State("switch.test_3", STATE_UNAVAILABLE)
    hass.states.async_set(switch_1.entity_id, switch_1.state, switch_1.attributes)
    hass.states.async_set(switch_2.entity_id, switch_2.state, switch_2.attributes)
    hass.states.async_set(switch_3.entity_id, switch_3.state, switch_3.attributes)
    device_action_event = Mock()
    hass.bus.async_listen(EVENT_DEVICE_ACTION, device_action_event)

    with patch(
        "custom_components.yandex_smart_home.device.STATE_CAPABILITIES_REGISTRY",
        [MockCapabilityA, MockCapabilityReturnState, MockCapabilityFail],
    ):
        payload = json.dumps(
            {
                "payload": {
                    "devices": [
                        {
                            "id": switch_1.entity_id,
                            "capabilities": [
                                {
                                    "type": MockCapabilityA.type,
                                    "state": {"instance": MockCapabilityA.instance, "value": True},
                                },
                                {
                                    "type": MockCapabilityReturnState.type,
                                    "state": {"instance": MockCapabilityReturnState.instance, "value": True},
                                },
                                {
                                    "type": MockCapabilityFail.type,
                                    "state": {"instance": MockCapabilityFail.instance, "value": True},
                                },
                            ],
                        },
                        {
                            "id": switch_2.entity_id,
                            "capabilities": [
                                {
                                    "type": MockCapabilityUnsupported.type,
                                    "state": {"instance": MockCapabilityUnsupported.instance, "value": True},
                                },
                                {
                                    "type": MockCapabilityA.type,
                                    "state": {"instance": ToggleCapabilityInstance.CONTROLS_LOCKED, "value": True},
                                },
                            ],
                        },
                        {
                            "id": switch_3.entity_id,
                            "capabilities": [
                                {
                                    "type": MockCapabilityA.type,
                                    "state": {"instance": MockCapabilityA.instance, "value": True},
                                }
                            ],
                        },
                        {
                            "id": "foo.not_exist",
                            "capabilities": [
                                {
                                    "type": MockCapabilityA.type,
                                    "state": {"instance": MockCapabilityA.instance, "value": True},
                                }
                            ],
                        },
                    ]
                }
            }
        )
        assert (await handlers.async_devices_action(hass, BASIC_REQUEST_DATA, payload)).as_dict() == {
            "devices": [
                {
                    "id": "switch.test_1",
                    "capabilities": [
                        {
                            "type": "devices.capabilities.toggle",
                            "state": {"instance": "pause", "action_result": {"status": "DONE"}},
                        },
                        {
                            "type": "devices.capabilities.toggle",
                            "state": {
                                "instance": "backlight",
                                "action_result": {
                                    "status": "DONE",
                                },
                                "value": {"protocol": "hls", "stream_url": "foo"},
                            },
                        },
                        {
                            "type": "devices.capabilities.toggle",
                            "state": {
                                "instance": "ionization",
                                "action_result": {"status": "ERROR", "error_code": "INTERNAL_ERROR"},
                            },
                        },
                    ],
                },
                {
                    "id": "switch.test_2",
                    "capabilities": [
                        {
                            "type": "devices.capabilities.toggle",
                            "state": {
                                "instance": "keep_warm",
                                "action_result": {"status": "ERROR", "error_code": "NOT_SUPPORTED_IN_CURRENT_MODE"},
                            },
                        },
                        {
                            "type": "devices.capabilities.toggle",
                            "state": {
                                "instance": "controls_locked",
                                "action_result": {"status": "ERROR", "error_code": "NOT_SUPPORTED_IN_CURRENT_MODE"},
                            },
                        },
                    ],
                },
                {"id": "switch.test_3", "action_result": {"status": "ERROR", "error_code": "DEVICE_UNREACHABLE"}},
                {"id": "foo.not_exist", "action_result": {"status": "ERROR", "error_code": "DEVICE_UNREACHABLE"}},
            ]
        }

        await hass.async_block_till_done()

        assert device_action_event.call_count == 7
        args, _ = device_action_event.call_args_list[0]
        assert args[0].as_dict()["data"] == {
            "entity_id": "switch.test_1",
            "capability": {"state": {"instance": "pause", "value": True}, "type": "devices.capabilities.toggle"},
        }

        args, _ = device_action_event.call_args_list[1]
        assert args[0].as_dict()["data"] == {
            "entity_id": "switch.test_1",
            "capability": {"state": {"instance": "backlight", "value": True}, "type": "devices.capabilities.toggle"},
        }

        args, _ = device_action_event.call_args_list[2]
        assert args[0].as_dict()["data"] == {
            "entity_id": "switch.test_1",
            "capability": {"state": {"instance": "ionization", "value": True}, "type": "devices.capabilities.toggle"},
            "error_code": "INTERNAL_ERROR",
        }

        args, _ = device_action_event.call_args_list[6]
        assert args[0].as_dict()["data"] == {
            "entity_id": "foo.not_exist",
            "error_code": "DEVICE_UNREACHABLE",
        }

        filtered_messages = [m for m in caplog.messages if "Bus:Handling" not in m]
        assert filtered_messages == [
            "Failed to execute action for instance ionization (devices.capabilities.toggle) of switch.test_1: "
            "Exception('fail set_state') (INTERNAL_ERROR)",
            "Capability not found for instance keep_warm (devices.capabilities.toggle) of switch.test_2 "
            "(NOT_SUPPORTED_IN_CURRENT_MODE)",
            "Capability not found for instance controls_locked (devices.capabilities.toggle) of switch.test_2 "
            "(NOT_SUPPORTED_IN_CURRENT_MODE)",
        ]


async def test_handler_devices_action_error_template(hass, caplog):
    class MockCapabilityA(OnOffCapability):
        @property
        def supported(self) -> bool:
            return True

        def get_value(self) -> bool | None:
            return None

        async def set_instance_state(self, context: Context, state: OnOffCapabilityInstanceActionState) -> None:
            pass

        async def _set_instance_state(self, context: Context, state: OnOffCapabilityInstanceActionState) -> None:
            pass

    class MockCapabilityB(StateToggleCapability):
        instance = ToggleCapabilityInstance.PAUSE

        @property
        def supported(self) -> bool:
            return True

        def get_value(self) -> bool | None:
            return None

        async def set_instance_state(self, context: Context, state: ToggleCapabilityInstanceActionState) -> None:
            pass

    class MockCapabilityC(StateToggleCapability):
        instance = ToggleCapabilityInstance.BACKLIGHT

        @property
        def supported(self) -> bool:
            return True

        def get_value(self) -> bool | None:
            return None

        async def set_instance_state(self, context: Context, state: ToggleCapabilityInstanceActionState) -> None:
            pass

    entry_data = MockConfigEntryData(
        entity_config={
            "switch.test": {
                "error_code_template": Template(
                    """
                    {% if capability.type == "devices.capabilities.on_off" and capability.state.instance == "on" and
                          capability.state.value %}
                        NOT_ENOUGH_WATER
                    {% elif capability.state.instance == 'pause' %}
                        {% if is_state('sensor.foo', 'bar') %}
                            CONTAINER_FULL
                        {% endif %}
                    {% elif capability.state.instance == 'backlight' and capability.state.value %}
                        WAT?
                    {% endif %}
                """
                )
            }
        }
    )
    data = RequestData(entry_data, Context(), "test", REQ_ID)

    switch = State("switch.test", STATE_OFF)
    hass.states.async_set(switch.entity_id, switch.state, switch.attributes)

    with patch(
        "custom_components.yandex_smart_home.device.STATE_CAPABILITIES_REGISTRY",
        [MockCapabilityA, MockCapabilityB, MockCapabilityC],
    ):
        payload = json.dumps(
            {
                "payload": {
                    "devices": [
                        {
                            "id": switch.entity_id,
                            "capabilities": [
                                {
                                    "type": MockCapabilityA.type,
                                    "state": {"instance": MockCapabilityA.instance, "value": True},
                                },
                                {
                                    "type": MockCapabilityB.type,
                                    "state": {"instance": MockCapabilityB.instance, "value": True},
                                },
                                {
                                    "type": MockCapabilityC.type,
                                    "state": {"instance": MockCapabilityC.instance, "value": True},
                                },
                            ],
                        }
                    ]
                }
            }
        )

        assert (await handlers.async_devices_action(hass, data, payload)).as_dict() == {
            "devices": [
                {
                    "id": "switch.test",
                    "capabilities": [
                        {
                            "type": MockCapabilityA.type,
                            "state": {
                                "instance": MockCapabilityA.instance,
                                "action_result": {"status": "ERROR", "error_code": "NOT_ENOUGH_WATER"},
                            },
                        },
                        {
                            "type": MockCapabilityB.type,
                            "state": {"instance": MockCapabilityB.instance, "action_result": {"status": "DONE"}},
                        },
                        {
                            "type": MockCapabilityC.type,
                            "state": {
                                "instance": MockCapabilityC.instance,
                                "action_result": {"status": "ERROR", "error_code": "INTERNAL_ERROR"},
                            },
                        },
                    ],
                }
            ]
        }

        assert caplog.records[-2].message == "Invalid error code for switch.test: 'WAT?' (INTERNAL_ERROR)"

        hass.states.async_set("sensor.foo", "bar")
        payload = json.dumps(
            {
                "payload": {
                    "devices": [
                        {
                            "id": switch.entity_id,
                            "capabilities": [
                                {
                                    "type": MockCapabilityB.type,
                                    "state": {"instance": MockCapabilityB.instance, "value": True},
                                }
                            ],
                        }
                    ]
                }
            }
        )

        assert (await handlers.async_devices_action(hass, data, payload)).as_dict() == {
            "devices": [
                {
                    "id": "switch.test",
                    "capabilities": [
                        {
                            "type": MockCapabilityB.type,
                            "state": {
                                "instance": MockCapabilityB.instance,
                                "action_result": {"status": "ERROR", "error_code": "CONTAINER_FULL"},
                            },
                        }
                    ],
                }
            ]
        }


async def test_handler_devices_action_not_allowed(hass, caplog):
    entry_data = MockConfigEntryData(entity_config={"switch.test": {"turn_on": False}})
    data = RequestData(entry_data, Context(), "test", REQ_ID)

    switch = State("switch.test", STATE_OFF)
    hass.states.async_set(switch.entity_id, switch.state, switch.attributes)

    payload = json.dumps(
        {
            "payload": {
                "devices": [
                    {
                        "id": switch.entity_id,
                        "capabilities": [
                            {
                                "type": CapabilityType.ON_OFF,
                                "state": {"instance": OnOffCapabilityInstance.ON, "value": True},
                            },
                        ],
                    }
                ]
            }
        }
    )

    assert (await handlers.async_devices_action(hass, data, payload)).as_dict() == {
        "devices": [
            {
                "id": "switch.test",
                "capabilities": [
                    {
                        "type": "devices.capabilities.on_off",
                        "state": {
                            "instance": "on",
                            "action_result": {"error_code": "REMOTE_CONTROL_DISABLED", "status": "ERROR"},
                        },
                    }
                ],
            }
        ]
    }

    assert len([m for m in caplog.messages if "Bus:Handling" not in m]) == 0
