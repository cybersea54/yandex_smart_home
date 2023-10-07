"""Implement the Yandex Smart Home base device property."""
from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from .helpers import ListRegistry
from .schema import (
    PropertyDescription,
    PropertyInstance,
    PropertyInstanceState,
    PropertyInstanceStateValue,
    PropertyParameters,
    PropertyType,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, State

    from .entry_data import ConfigEntryData


@runtime_checkable
class Property(Protocol):
    """Base class for a device property."""

    device_id: str
    type: PropertyType
    instance: PropertyInstance

    _hass: HomeAssistant
    _entry_data: ConfigEntryData

    @property
    @abstractmethod
    def supported(self) -> bool:
        """Test if the property is supported."""
        ...

    @property
    def retrievable(self) -> bool:
        """Test if the property can return the current value."""
        return True

    @property
    def reportable(self) -> bool:
        """Test if the capability can report changes."""
        return self._entry_data.is_reporting_states

    @property
    def report_immediately(self) -> bool:
        """Test if property changes should be reported without debounce."""
        return False

    @property
    def report_on_startup(self) -> bool:
        """Test if property value should be reported on startup."""
        return True

    @property
    @abstractmethod
    def parameters(self) -> PropertyParameters:
        """Return parameters for a devices list request."""
        ...

    @abstractmethod
    def get_description(self) -> PropertyDescription:
        """Return a description for a device list request."""
        ...

    @abstractmethod
    def get_value(self) -> Any:
        """Return the current property value."""
        ...

    def get_instance_state(self) -> PropertyInstanceState | None:
        """Return a state for a state query request."""
        if (value := self.get_value()) is not None:
            return PropertyInstanceState(
                type=self.type, state=PropertyInstanceStateValue(instance=self.instance, value=value)
            )

        return None

    @property
    @abstractmethod
    def value_entity_id(self) -> str:
        """Return id of entity the current value is based on."""
        ...

    def __eq__(self, other: Any) -> bool:
        """Compare properties."""
        return bool(isinstance(other, self.__class__) and self.type == other.type and self.instance == other.instance)


class StateProperty(Property, Protocol):
    """Base class for a device property based on the state."""

    state: State

    def __init__(self, hass: HomeAssistant, entry_data: ConfigEntryData, state: State):
        """Initialize a property for the state."""
        self._hass = hass
        self._entry_data = entry_data

        self.state = state
        self.device_id = state.entity_id

    @property
    def value_entity_id(self) -> str:
        """Return id of entity the current value is based on."""
        return self.state.entity_id


STATE_PROPERTIES_REGISTRY = ListRegistry[type[StateProperty]]()
