"""Config flow for the Alert integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
import yaml

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import (
    CONF_ENTITY_ID,
    CONF_NAME,
    CONF_REPEAT,
    CONF_STATE,
    STATE_ON,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_ALERT_MESSAGE,
    CONF_CAN_ACK,
    CONF_DATA,
    CONF_DONE_MESSAGE,
    CONF_NOTIFIERS,
    CONF_SKIP_FIRST,
    CONF_TITLE,
    DEFAULT_CAN_ACK,
    DEFAULT_SKIP_FIRST,
    DOMAIN,
)

_MULTILINE = TextSelector(TextSelectorConfig(multiline=True))
_TEXT = TextSelector()
_BOOL = BooleanSelector()
_ENTITY = EntitySelector()
_REPEAT_NUMBER = NumberSelector(
    NumberSelectorConfig(min=0.016, step=1, mode=NumberSelectorMode.BOX)
)

_SUBENTRY_SCHEMA_BASE = {
    vol.Required(CONF_NAME): _TEXT,
    vol.Required(CONF_ENTITY_ID): _ENTITY,
    vol.Required(CONF_REPEAT): _REPEAT_NUMBER,
    vol.Optional(CONF_STATE, default=STATE_ON): _TEXT,
    vol.Optional(CONF_CAN_ACK, default=DEFAULT_CAN_ACK): _BOOL,
    vol.Optional(CONF_SKIP_FIRST, default=DEFAULT_SKIP_FIRST): _BOOL,
    vol.Optional(CONF_ALERT_MESSAGE, default=""): _MULTILINE,
    vol.Optional(CONF_DONE_MESSAGE, default=""): _MULTILINE,
    vol.Optional(CONF_TITLE, default=""): _TEXT,
    vol.Optional(CONF_NOTIFIERS, default=""): _MULTILINE,
    vol.Optional(CONF_DATA, default=""): _MULTILINE,
}


_SUBENTRY_SCHEMA = vol.Schema(_SUBENTRY_SCHEMA_BASE)


def _parse_subentry_user_input(
    user_input: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Parse and validate user input for a subentry.

    Returns (parsed_data, errors). On success errors is empty.
    """
    errors: dict[str, str] = {}

    # Parse repeat: NumberSelector returns a float; store as list[float] for AlertEntity
    repeat_val = user_input.get(CONF_REPEAT, 1)
    repeat = [float(repeat_val)]

    # Parse notifiers: split multiline text into a list, stripping blanks
    notifiers_raw: str = user_input.get(CONF_NOTIFIERS, "") or ""
    notifiers = [line.strip() for line in notifiers_raw.splitlines() if line.strip()]

    # Parse data: YAML mapping or empty
    data_raw: str = user_input.get(CONF_DATA, "") or ""
    data: dict[str, Any] | None = None
    if data_raw.strip():
        try:
            parsed = yaml.safe_load(data_raw)
        except yaml.YAMLError:
            errors[CONF_DATA] = "invalid_yaml"
            return {}, errors
        if not isinstance(parsed, dict):
            errors[CONF_DATA] = "invalid_data"
            return {}, errors
        data = parsed

    # Optional string fields — store None when empty
    message = user_input.get(CONF_ALERT_MESSAGE, "").strip() or None
    done_message = user_input.get(CONF_DONE_MESSAGE, "").strip() or None
    title = user_input.get(CONF_TITLE, "").strip() or None

    parsed_data: dict[str, Any] = {
        CONF_NAME: user_input[CONF_NAME],
        CONF_ENTITY_ID: user_input[CONF_ENTITY_ID],
        CONF_REPEAT: repeat,
        CONF_STATE: user_input.get(CONF_STATE, STATE_ON),
        CONF_CAN_ACK: user_input.get(CONF_CAN_ACK, DEFAULT_CAN_ACK),
        CONF_SKIP_FIRST: user_input.get(CONF_SKIP_FIRST, DEFAULT_SKIP_FIRST),
        CONF_ALERT_MESSAGE: message,
        CONF_DONE_MESSAGE: done_message,
        CONF_TITLE: title,
        CONF_NOTIFIERS: notifiers,
        CONF_DATA: data,
    }
    return parsed_data, errors


def _subentry_data_to_form_defaults(data: Mapping[str, Any]) -> dict[str, Any]:
    """Convert stored subentry data back to form display values."""
    notifiers: list[str] = data.get(CONF_NOTIFIERS) or []
    data_dict: dict[str, Any] | None = data.get(CONF_DATA)

    return {
        CONF_NAME: data.get(CONF_NAME, ""),
        CONF_ENTITY_ID: data.get(CONF_ENTITY_ID, ""),
        CONF_REPEAT: data.get(CONF_REPEAT, [1])[0],
        CONF_STATE: data.get(CONF_STATE, STATE_ON),
        CONF_CAN_ACK: data.get(CONF_CAN_ACK, DEFAULT_CAN_ACK),
        CONF_SKIP_FIRST: data.get(CONF_SKIP_FIRST, DEFAULT_SKIP_FIRST),
        CONF_ALERT_MESSAGE: data.get(CONF_ALERT_MESSAGE) or "",
        CONF_DONE_MESSAGE: data.get(CONF_DONE_MESSAGE) or "",
        CONF_TITLE: data.get(CONF_TITLE) or "",
        CONF_NOTIFIERS: "\n".join(notifiers),
        CONF_DATA: yaml.dump(data_dict, default_flow_style=False) if data_dict else "",
    }


class AlertConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Alert."""

    VERSION = 1

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentry types supported by this integration."""
        return {"alert": AlertSubentryFlowHandler}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial (parent entry) step."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Alert", data={})
        return self.async_show_form(step_id="user")


class AlertSubentryFlowHandler(ConfigSubentryFlow):
    """Handle an Alert subentry flow."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Handle adding a new alert subentry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            parsed, errors = _parse_subentry_user_input(user_input)
            if not errors:
                return self.async_create_entry(
                    title=parsed[CONF_NAME],
                    data=parsed,
                )
        return self.async_show_form(
            step_id="user",
            data_schema=_SUBENTRY_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Handle reconfiguring an existing alert subentry."""
        subentry = self._get_reconfigure_subentry()
        errors: dict[str, str] = {}
        if user_input is not None:
            parsed, errors = _parse_subentry_user_input(user_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    self._get_entry(),
                    subentry,
                    title=parsed[CONF_NAME],
                    data=parsed,
                )
        defaults = _subentry_data_to_form_defaults(subentry.data)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(_SUBENTRY_SCHEMA, defaults),
            errors=errors,
        )
