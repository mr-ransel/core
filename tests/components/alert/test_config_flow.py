"""Tests for the Alert config flow."""

from __future__ import annotations

from typing import Any

import pytest

from homeassistant import config_entries
from homeassistant.components.alert.const import (
    CONF_ALERT_MESSAGE,
    CONF_CAN_ACK,
    CONF_DATA,
    CONF_DONE_MESSAGE,
    CONF_NOTIFIERS,
    CONF_SKIP_FIRST,
    CONF_TITLE,
    DOMAIN,
)
from homeassistant.const import (
    CONF_ENTITY_ID,
    CONF_NAME,
    CONF_REPEAT,
    CONF_STATE,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry

WATCH_ENTITY = "binary_sensor.door"

REQUIRED_SUBENTRY_INPUT: dict[str, Any] = {
    CONF_NAME: "My Alert",
    CONF_ENTITY_ID: WATCH_ENTITY,
    CONF_REPEAT: 5,
    CONF_STATE: STATE_ON,
    CONF_CAN_ACK: True,
    CONF_SKIP_FIRST: False,
    CONF_ALERT_MESSAGE: "",
    CONF_DONE_MESSAGE: "",
    CONF_TITLE: "",
    CONF_NOTIFIERS: "",
    CONF_DATA: "",
}

ALL_FIELDS_INPUT: dict[str, Any] = {
    CONF_NAME: "Full Alert",
    CONF_ENTITY_ID: WATCH_ENTITY,
    CONF_REPEAT: 10,
    CONF_STATE: "problem",
    CONF_CAN_ACK: False,
    CONF_SKIP_FIRST: True,
    CONF_ALERT_MESSAGE: "Alert fired!",
    CONF_DONE_MESSAGE: "Alert cleared.",
    CONF_TITLE: "My Notification",
    CONF_NOTIFIERS: "notify.mobile_app_phone\nnotify.persistent_notification",
    CONF_DATA: "sound: default\ncritical: true",
}


async def _setup_parent_entry(hass: HomeAssistant) -> config_entries.ConfigEntry:
    """Create and load a parent Alert config entry."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    await async_setup_component(hass, DOMAIN, {})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


# ---------------------------------------------------------------------------
# Parent entry flow
# ---------------------------------------------------------------------------


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    """Test that the user flow creates a parent config entry."""
    await async_setup_component(hass, DOMAIN, {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Alert"
    assert result["data"] == {}


async def test_second_entry_aborted(hass: HomeAssistant) -> None:
    """Test that creating a second parent entry is aborted."""
    await async_setup_component(hass, DOMAIN, {})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    await hass.config_entries.flow.async_configure(result["flow_id"], user_input={})
    await hass.async_block_till_done()

    # Second attempt
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# ---------------------------------------------------------------------------
# Subentry: no subentries
# ---------------------------------------------------------------------------


async def test_entry_no_subentries_no_entities(hass: HomeAssistant) -> None:
    """Config entry with no subentries sets up without errors and creates no entities."""
    entry = await _setup_parent_entry(hass)
    assert entry.state is config_entries.ConfigEntryState.LOADED
    # No alert entities should be in the state machine from this entry
    alert_states = hass.states.async_entity_ids(DOMAIN)
    assert not alert_states


# ---------------------------------------------------------------------------
# Subentry: add with required fields only
# ---------------------------------------------------------------------------


async def test_subentry_required_fields(hass: HomeAssistant) -> None:
    """Adding a subentry with only required fields creates the expected entity."""
    entry = await _setup_parent_entry(hass)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "alert"),
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], user_input=REQUIRED_SUBENTRY_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    await hass.async_block_till_done()

    subentry_id = list(entry.subentries)[0]
    subentry = entry.subentries[subentry_id]
    assert subentry.title == "My Alert"
    assert subentry.data[CONF_NAME] == "My Alert"
    assert subentry.data[CONF_ENTITY_ID] == WATCH_ENTITY
    assert subentry.data[CONF_REPEAT] == [5.0]
    assert subentry.data[CONF_NOTIFIERS] == []
    assert subentry.data[CONF_DATA] is None


# ---------------------------------------------------------------------------
# Subentry: add with all fields
# ---------------------------------------------------------------------------


async def test_subentry_all_fields(hass: HomeAssistant) -> None:
    """Adding a subentry with all fields creates entity with correct attributes."""
    entry = await _setup_parent_entry(hass)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "alert"),
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], user_input=ALL_FIELDS_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    await hass.async_block_till_done()

    subentry_id = list(entry.subentries)[0]
    subentry = entry.subentries[subentry_id]
    assert subentry.title == "Full Alert"
    assert subentry.data[CONF_REPEAT] == [10.0]
    assert subentry.data[CONF_STATE] == "problem"
    assert subentry.data[CONF_CAN_ACK] is False
    assert subentry.data[CONF_SKIP_FIRST] is True
    assert subentry.data[CONF_ALERT_MESSAGE] == "Alert fired!"
    assert subentry.data[CONF_DONE_MESSAGE] == "Alert cleared."
    assert subentry.data[CONF_TITLE] == "My Notification"
    assert subentry.data[CONF_NOTIFIERS] == [
        "notify.mobile_app_phone",
        "notify.persistent_notification",
    ]
    assert subentry.data[CONF_DATA] == {"sound": "default", "critical": True}


# ---------------------------------------------------------------------------
# Subentry: invalid YAML in data field
# ---------------------------------------------------------------------------


async def test_subentry_invalid_yaml_data(hass: HomeAssistant) -> None:
    """Submitting invalid YAML in the data field returns an error."""
    entry = await _setup_parent_entry(hass)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "alert"),
        context={"source": config_entries.SOURCE_USER},
    )
    bad_input = {**REQUIRED_SUBENTRY_INPUT, CONF_DATA: ": invalid: yaml: [[["}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], user_input=bad_input
    )
    assert result["type"] is FlowResultType.FORM
    assert CONF_DATA in result["errors"]
    assert result["errors"][CONF_DATA] == "invalid_yaml"


# ---------------------------------------------------------------------------
# Subentry: YAML data field parses to non-mapping
# ---------------------------------------------------------------------------


async def test_subentry_data_not_mapping(hass: HomeAssistant) -> None:
    """YAML data field that parses to a non-mapping returns an error."""
    entry = await _setup_parent_entry(hass)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "alert"),
        context={"source": config_entries.SOURCE_USER},
    )
    bad_input = {**REQUIRED_SUBENTRY_INPUT, CONF_DATA: "just a string"}
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], user_input=bad_input
    )
    assert result["type"] is FlowResultType.FORM
    assert CONF_DATA in result["errors"]
    assert result["errors"][CONF_DATA] == "invalid_data"


# ---------------------------------------------------------------------------
# Subentry: reconfigure
# ---------------------------------------------------------------------------


async def test_subentry_reconfigure(hass: HomeAssistant) -> None:
    """Reconfiguring an existing subentry updates the stored data."""
    subentry_id = "test_subentry_id"
    original_data: dict[str, Any] = {
        CONF_NAME: "Original Alert",
        CONF_ENTITY_ID: WATCH_ENTITY,
        CONF_REPEAT: [5.0],
        CONF_STATE: STATE_ON,
        CONF_CAN_ACK: True,
        CONF_SKIP_FIRST: False,
        CONF_ALERT_MESSAGE: None,
        CONF_DONE_MESSAGE: None,
        CONF_TITLE: None,
        CONF_NOTIFIERS: [],
        CONF_DATA: None,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        subentries_data=[
            config_entries.ConfigSubentryData(
                data=original_data,
                subentry_id=subentry_id,
                subentry_type="alert",
                title="Original Alert",
                unique_id=None,
            )
        ],
    )
    entry.add_to_hass(hass)
    await async_setup_component(hass, DOMAIN, {})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await entry.start_subentry_reconfigure_flow(hass, subentry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    updated_input = {
        CONF_NAME: "Renamed Alert",
        CONF_ENTITY_ID: WATCH_ENTITY,
        CONF_REPEAT: 15,
        CONF_STATE: STATE_ON,
        CONF_CAN_ACK: True,
        CONF_SKIP_FIRST: True,
        CONF_ALERT_MESSAGE: "",
        CONF_DONE_MESSAGE: "",
        CONF_TITLE: "",
        CONF_NOTIFIERS: "notify.test",
        CONF_DATA: "",
    }
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], user_input=updated_input
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    updated_subentry = entry.subentries[subentry_id]
    assert updated_subentry.title == "Renamed Alert"
    assert updated_subentry.data[CONF_NAME] == "Renamed Alert"
    assert updated_subentry.data[CONF_REPEAT] == [15.0]
    assert updated_subentry.data[CONF_SKIP_FIRST] is True
    assert updated_subentry.data[CONF_NOTIFIERS] == ["notify.test"]


# ---------------------------------------------------------------------------
# Coexistence: YAML and UI alerts
# ---------------------------------------------------------------------------


async def test_yaml_and_subentry_coexist(hass: HomeAssistant) -> None:
    """YAML-configured and subentry-configured alerts coexist."""
    yaml_config = {
        DOMAIN: {
            "yaml_alert": {
                CONF_NAME: "YAML Alert",
                CONF_ENTITY_ID: WATCH_ENTITY,
                CONF_REPEAT: [1],
                CONF_STATE: STATE_ON,
                CONF_CAN_ACK: True,
                CONF_SKIP_FIRST: False,
                CONF_NOTIFIERS: [],
            }
        }
    }
    assert await async_setup_component(hass, DOMAIN, yaml_config)
    await hass.async_block_till_done()

    # YAML alert should exist
    assert hass.states.get(f"{DOMAIN}.yaml_alert") is not None

    # Now set up a config entry with one subentry
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        subentries_data=[
            config_entries.ConfigSubentryData(
                data={
                    CONF_NAME: "UI Alert",
                    CONF_ENTITY_ID: WATCH_ENTITY,
                    CONF_REPEAT: [2.0],
                    CONF_STATE: STATE_ON,
                    CONF_CAN_ACK: True,
                    CONF_SKIP_FIRST: False,
                    CONF_ALERT_MESSAGE: None,
                    CONF_DONE_MESSAGE: None,
                    CONF_TITLE: None,
                    CONF_NOTIFIERS: [],
                    CONF_DATA: None,
                },
                subentry_id="ui_subentry",
                subentry_type="alert",
                title="UI Alert",
                unique_id=None,
            )
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Both alerts should be present
    assert hass.states.get(f"{DOMAIN}.yaml_alert") is not None
    all_alert_entity_ids = hass.states.async_entity_ids(DOMAIN)
    assert len(all_alert_entity_ids) >= 2


# ---------------------------------------------------------------------------
# Notifiers: multiline input parsed to list
# ---------------------------------------------------------------------------


async def test_notifiers_multiline_parsed(hass: HomeAssistant) -> None:
    """Notifier multiline input is correctly parsed and stored as a list."""
    entry = await _setup_parent_entry(hass)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "alert"),
        context={"source": config_entries.SOURCE_USER},
    )
    notifier_input = {
        **REQUIRED_SUBENTRY_INPUT,
        CONF_NOTIFIERS: "notify.service_a\n  notify.service_b  \nnotify.service_c\n",
    }
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], user_input=notifier_input
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    subentry_id = list(entry.subentries)[0]
    notifiers = entry.subentries[subentry_id].data[CONF_NOTIFIERS]
    assert notifiers == ["notify.service_a", "notify.service_b", "notify.service_c"]
