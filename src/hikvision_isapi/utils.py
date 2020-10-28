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
