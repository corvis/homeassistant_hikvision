#    hass-hikvision-connector
#    Copyright (C) 2020 Dmitry Berezovsky
#    The MIT License (MIT)
#    
#    Permission is hereby granted, free of charge, to any person obtaining
#    a copy of this software and associated documentation files
#    (the "Software"), to deal in the Software without restriction,
#    including without limitation the rights to use, copy, modify, merge,
#    publish, distribute, sublicense, and/or sell copies of the Software,
#    and to permit persons to whom the Software is furnished to do so,
#    subject to the following conditions:
#    
#    The above copyright notice and this permission notice shall be
#    included in all copies or substantial portions of the Software.
#    
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#    MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
#    CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
#    TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#    SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import logging
from typing import Dict

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from . import const, utils
from .isapi.client import ISAPIClient

_LOGGER = logging.getLogger(__name__)


class HikvisionFlowHandler(config_entries.ConfigFlow, domain=const.DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):

        errors = {}

        if user_input is not None:
            hik_client: ISAPIClient = None
            try:
                hik_client = utils.api_client_from_config(user_input)
                device_info = await hik_client.get_device_info()
                config = {const.CONF_DEVICE_TYPE: device_info.device_type}
                config.update(user_input)

            except Exception as e:
                utils.handle_hik_client_error(e, errors, _LOGGER)
            else:
                await self.async_set_unique_id(
                    device_info.serial_number, raise_on_progress=False
                )
                return self.async_create_entry(
                    title=device_info.device_name, data=config
                )
            finally:
                if hik_client is not None:
                    await hik_client.close()

        if user_input is None:
            user_input = {}
        return self.async_show_form(
            step_id='user',
            data_schema=vol.Schema({
                vol.Required(const.CONF_BASE_URL, default=user_input.get(const.CONF_BASE_URL)): str,
                vol.Optional(const.CONF_USER, default=user_input.get(const.CONF_USER)): str,
                vol.Optional(const.CONF_PASSWORD, default=user_input.get(const.CONF_PASSWORD)): str,
                vol.Optional(const.CONF_IGNORE_SSL_ERRORS,
                             default=user_input.get(const.CONF_IGNORE_SSL_ERRORS, False)): bool,
            }),
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HikvisionOptionsFlowHandler(config_entry)


class HikvisionOptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry
        self.current_options = config_entry.options or {
            const.OPT_ROOT_COMMON: {}
        }

    def preserve_options_section(self, section_name, value):
        result = dict(self.current_options)
        result.update({section_name: value})
        return self.async_create_entry(
            title="", data=result,
        )

    def is_nvr(self) -> bool:
        return self.config_entry.data.get(const.CONF_DEVICE_TYPE) == const.DEVICE_TYPE_NVR

    async def async_step_init(self, user_input=None):

        errors = {}

        if user_input is not None:
            if user_input[const.OPT_EDIT_KEY] == const.EDIT_COMMON_SETTINGS:
                return await self.async_step_common_settings()
            elif user_input[const.OPT_EDIT_KEY].startswith(const.EDIT_INPUT_PREFIX):
                return await self.async_step_alerts(
                    channel=user_input[const.OPT_EDIT_KEY].replace(const.EDIT_INPUT_PREFIX, '').strip())

        config_pages_dict = {const.EDIT_COMMON_SETTINGS: "Common Settings"}

        # For NVRs we have to render a page for each channel
        if self.is_nvr():
            try:
                async with utils.api_client_from_config(self.config_entry.data) as hik_client:
                    inputs = await hik_client.get_available_inputs()
                    config_pages_dict.update(
                        {const.EDIT_INPUT_PREFIX + x.input_id: 'Alerts: ' + x.input_name for x in inputs}
                    )
            except Exception as e:
                utils.handle_hik_client_error(e, errors, _LOGGER)
        else:
            config_pages_dict[const.EDIT_INPUT_PREFIX] = 'Alerts'

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(const.OPT_EDIT_KEY, default=const.EDIT_COMMON_SETTINGS): vol.In(config_pages_dict)
            }),
            errors=errors

        )

    async def async_step_common_settings(self, user_input: Dict = None):
        current = self.current_options.get(const.OPT_ROOT_COMMON)
        errors = {}

        if user_input is not None:
            # Validate input
            if not utils.parse_timedelta_or_default(user_input.get(const.OPT_COMMON_DEFAULT_RECOVERY_PERIOD), None):
                errors[const.OPT_COMMON_DEFAULT_RECOVERY_PERIOD] = 'invalid_period'
            if len(errors.keys()) == 0:
                return self.preserve_options_section(const.OPT_ROOT_COMMON, user_input)

        schema_dict = {
            vol.Optional(
                const.OPT_COMMON_DEFAULT_RECOVERY_PERIOD,
                description={"suggested_value": current.get(const.OPT_COMMON_DEFAULT_RECOVERY_PERIOD)},
                default=const.DEFAULTS_COMMON_DEFAULT_RECOVERY_PERIOD
            ): str,
        }

        # For NVRs we need channel selector
        # if self.is_nvr():
        #     try:
        #         async with utils.api_client_from_config(self.config_entry.data) as hik_client:
        #             inputs = await hik_client.get_available_inputs()
        #
        #             schema_dict.update({
        #                 vol.Optional(
        #                     const.OPT_COMMON_ALERT_INPUTS,
        #                     default=current.get(const.OPT_COMMON_ALERT_INPUTS),
        #                     description='alert_inputs_description'
        #                 ): cv.multi_select({x.input_id: x.input_name for x in inputs})
        #             })
        #     except Exception as e:
        #         utils.handle_hik_client_error(e, errors, _LOGGER)

        return self.async_show_form(
            step_id="common_settings",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={},
            errors=errors
        )

    async def async_step_alerts(self, user_input: Dict = None, channel: str = None):
        if user_input is None:
            options_key_name = const.OPT_ROOT_ALERTS + (channel or '')
            self.context[const.CONTEXT_ALERT_CONFIG_KEY] = options_key_name
        else:
            options_key_name = self.context[const.CONTEXT_ALERT_CONFIG_KEY]
        current = self.current_options.get(options_key_name, {})

        if user_input is not None:
            del self.context[const.CONTEXT_ALERT_CONFIG_KEY]
            return self.preserve_options_section(options_key_name, user_input)

        return self.async_show_form(
            step_id="alerts",
            data_schema=vol.Schema({
                vol.Optional(
                    const.OPT_ALERTS_ENABLE_TRACKING,
                    default=current.get(const.OPT_ALERTS_ENABLE_TRACKING)
                ): bool,
                vol.Optional(
                    const.OPT_ALERTS_ALERT_TYPES,
                    default=current.get(const.OPT_ALERTS_ALERT_TYPES)
                ): cv.multi_select({k.value: v for k, v in const.ALERT_TYPES_MAP.items()}),
            }),
            description_placeholders={}
        )
