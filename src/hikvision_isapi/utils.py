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

from . import const
from .isapi.client import ISAPIClient


def api_client_from_config(config: Dict) -> ISAPIClient:
    return ISAPIClient(config.get(const.CONF_BASE_URL),
                       username=config.get(const.CONF_USER),
                       password=config.get(const.CONF_PASSWORD),
                       ignore_ssl_errors=config.get(const.CONF_IGNORE_SSL_ERRORS)
                       )


def handle_hik_client_error(e: Exception, errors: Dict, logger: logging.Logger):
    # TODO: Implement proper handling, e.g. Unauthorized errors
    errors['base'] = 'unable_to_connect'
    logger.exception('Unable to connect to hikvision device')
