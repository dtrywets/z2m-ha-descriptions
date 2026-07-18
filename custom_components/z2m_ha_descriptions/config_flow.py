"""Config flow for Z2M HA Descriptions."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BASE_TOPIC,
    CONF_SYNC_EMPTY,
    DEFAULT_BASE_TOPIC,
    DEFAULT_SYNC_EMPTY,
    DOMAIN,
)


class Z2mHaDescriptionsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Z2M HA Descriptions."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if "mqtt" not in self.hass.config.components:
            return self.async_abort(reason="mqtt_not_loaded")

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Z2M HA Descriptions",
                data={},
                options={
                    CONF_BASE_TOPIC: user_input[CONF_BASE_TOPIC],
                    CONF_SYNC_EMPTY: user_input[CONF_SYNC_EMPTY],
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BASE_TOPIC, default=DEFAULT_BASE_TOPIC
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                    vol.Optional(
                        CONF_SYNC_EMPTY, default=DEFAULT_SYNC_EMPTY
                    ): selector.BooleanSelector(),
                }
            ),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):  # noqa: ANN001
        """Return the options flow handler."""
        return Z2mHaDescriptionsOptionsFlow()


class Z2mHaDescriptionsOptionsFlow(OptionsFlow):
    """Handle options for Z2M HA Descriptions."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BASE_TOPIC,
                        default=options.get(CONF_BASE_TOPIC, DEFAULT_BASE_TOPIC),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                    vol.Optional(
                        CONF_SYNC_EMPTY,
                        default=options.get(CONF_SYNC_EMPTY, DEFAULT_SYNC_EMPTY),
                    ): selector.BooleanSelector(),
                }
            ),
        )
