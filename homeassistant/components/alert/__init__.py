"""Support for repeating alerts when conditions are met.

DEVELOPMENT OF THE ALERT INTEGRATION IS FROZEN.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ENTITY_ID,
    CONF_NAME,
    CONF_REPEAT,
    CONF_STATE,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.template import Template
from homeassistant.helpers.typing import ConfigType

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
    LOGGER,
)
from .entity import AlertEntity

ALERT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Optional(CONF_STATE, default=STATE_ON): cv.string,
        vol.Required(CONF_REPEAT): vol.All(
            cv.ensure_list,
            [vol.Coerce(float)],
            # Minimum delay is 1 second = 0.016 minutes
            [vol.Range(min=0.016)],
        ),
        vol.Optional(CONF_CAN_ACK, default=DEFAULT_CAN_ACK): cv.boolean,
        vol.Optional(CONF_SKIP_FIRST, default=DEFAULT_SKIP_FIRST): cv.boolean,
        vol.Optional(CONF_ALERT_MESSAGE): cv.template,
        vol.Optional(CONF_DONE_MESSAGE): cv.template,
        vol.Optional(CONF_TITLE): cv.template,
        vol.Optional(CONF_DATA): dict,
        vol.Optional(CONF_NOTIFIERS, default=list): vol.All(
            cv.ensure_list, [cv.string]
        ),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: cv.schema_with_slug_keys(ALERT_SCHEMA)}, extra=vol.ALLOW_EXTRA
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Alert component.

    DEVELOPMENT OF THE ALERT INTEGRATION IS FROZEN.
    """
    component = EntityComponent[AlertEntity](LOGGER, DOMAIN, hass)
    hass.data[DOMAIN] = component

    component.async_register_entity_service(SERVICE_TURN_OFF, None, "async_turn_off")
    component.async_register_entity_service(SERVICE_TURN_ON, None, "async_turn_on")
    component.async_register_entity_service(SERVICE_TOGGLE, None, "async_toggle")

    entities: list[AlertEntity] = []

    for object_id, cfg in config.get(DOMAIN, {}).items():
        if not cfg:
            cfg = {}

        name = cfg[CONF_NAME]
        watched_entity_id = cfg[CONF_ENTITY_ID]
        alert_state = cfg[CONF_STATE]
        repeat = cfg[CONF_REPEAT]
        skip_first = cfg[CONF_SKIP_FIRST]
        message_template = cfg.get(CONF_ALERT_MESSAGE)
        done_message_template = cfg.get(CONF_DONE_MESSAGE)
        notifiers = cfg[CONF_NOTIFIERS]
        can_ack = cfg[CONF_CAN_ACK]
        title_template = cfg.get(CONF_TITLE)
        data = cfg.get(CONF_DATA)

        entities.append(
            AlertEntity(
                hass,
                object_id,
                name,
                watched_entity_id,
                alert_state,
                repeat,
                skip_first,
                message_template,
                done_message_template,
                notifiers,
                can_ack,
                title_template,
                data,
            )
        )

    if entities:
        await component.async_add_entities(entities)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Alert from a config entry."""
    component: EntityComponent[AlertEntity] = hass.data[DOMAIN]

    entities: list[AlertEntity] = []
    for subentry in entry.subentries.values():
        if subentry.subentry_type != "alert":
            continue
        data: dict[str, Any] = dict(subentry.data)

        entity = AlertEntity(
            hass=hass,
            entity_id=None,
            name=data[CONF_NAME],
            watched_entity_id=data[CONF_ENTITY_ID],
            state=data.get(CONF_STATE, STATE_ON),
            repeat=data[CONF_REPEAT],
            skip_first=data.get(CONF_SKIP_FIRST, DEFAULT_SKIP_FIRST),
            message_template=(
                Template(data[CONF_ALERT_MESSAGE], hass)
                if data.get(CONF_ALERT_MESSAGE)
                else None
            ),
            done_message_template=(
                Template(data[CONF_DONE_MESSAGE], hass)
                if data.get(CONF_DONE_MESSAGE)
                else None
            ),
            notifiers=data.get(CONF_NOTIFIERS, []),
            can_ack=data.get(CONF_CAN_ACK, DEFAULT_CAN_ACK),
            title_template=(
                Template(data[CONF_TITLE], hass) if data.get(CONF_TITLE) else None
            ),
            data=data.get(CONF_DATA) or {},
        )
        entity._attr_unique_id = subentry.subentry_id
        entities.append(entity)

    await component.async_add_entities(entities)
    entry.runtime_data = entities
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Alert config entry."""
    for entity in entry.runtime_data:
        await entity.async_remove()
    return True
