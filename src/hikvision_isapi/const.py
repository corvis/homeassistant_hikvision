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

DOMAIN = 'hikvision_isapi'
DATA_API_CLIENT = 'api_client'
DATA_EVENT_STREAM = 'event_stream'
DATA_HAS_SUBSCRIBERS = 'has_subscribers'
DATA_ALERT_CONFIGS = 'alert_configs'
DATA_BG_TASKS = 'bg_tasks'


DISCOVERY_DEVICE_NAME = 'device_name'
DISCOVERY_SENSOR_ID = 'sensor_id'
DISCOVERY_SENSOR_NAME = 'sensor_name'
DISCOVERY_CHANNEL_CFG = 'channel_cfg'
DISCOVERY_ALERT_CFG_ID = 'alert_cfg_id'
DISCOVERY_EVENT_STREAM = 'queue'

CONF_BASE_URL = 'base_url'
CONF_USER = 'username'
CONF_PASSWORD = 'password'
CONF_ALERTS = 'alerts'
CONF_CHANNELS = 'channels'
CONF_DEFAULT_RECOVERY_PERIOD = 'default_recovery_period'

CONF_ALERT_TYPE = 'type'
CONF_ALERT_CHANNEL = 'channel'
CONF_ALERT_NAME = 'name'
CONF_ALERT_RECOVERY_PERIOD = 'recovery_period'

CONF_CHANNEL_ID = 'id'
CONF_CHANNEL_ENTITY_ID = 'entity_id'
CONF_CHANNEL_NAME = 'name'

EVENT_ALERT_NAME = DOMAIN + '_alert'
EVENT_ALERT_DATA_CHANNEL = 'channel'
EVENT_ALERT_DATA_TYPE = 'alert_type'
EVENT_ALERT_DATA_DEVICE = 'device'
EVENT_ALERT_DATA_TIMESTAMP = 'timestamp'

ATTR_LAST_TRIGGERED_TIME = 'last_triggered'
