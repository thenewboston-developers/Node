import logging
from typing import Type, TypeVar
from urllib.parse import urljoin

import requests

from node.blockchain.inner_models import Node, SignedChangeRequest

logger = logging.getLogger(__name__)

T = TypeVar('T', bound='NodeClient')

DEFAULT_TIMEOUT = 2


class NodeClient:
    _instance = None

    @classmethod
    def get_instance(cls: Type[T]) -> T:
        instance = cls._instance
        if not instance:
            instance = cls()
            cls.set_instance_cache(instance)

        return instance

    @classmethod
    def set_instance_cache(cls: Type[T], instance: T):
        cls._instance = instance

    @classmethod
    def clear_instance_cache(cls):
        cls._instance = None

    @staticmethod
    def requests_post(url, *args, **kwargs):  # We need this method for mocking in unittests
        return requests.post(url, *args, **kwargs)

    def http_post(self, network_address, resource, json_data=None, data=None, *, should_raise=True):
        url = urljoin(network_address, f'/api/{resource}/')

        try:
            response = self.requests_post(
                url, json=json_data, data=data, headers={'Content-Type': 'application/json'}, timeout=DEFAULT_TIMEOUT
            )
        except Exception:
            logger.warning('Could not POST %s, data: %s', url, data if json_data is None else json_data, exc_info=True)
            if should_raise:
                raise

            return None

        if should_raise:
            response.raise_for_status()
        else:
            status_code = response.status_code
            if status_code >= 400:
                logger.warning(
                    'Could not POST %s: HTTP%s: %s, data: %s', url, status_code, response.text,
                    data if json_data is None else json_data
                )

        return response

    def send_scr_to_address(self, address: str, signed_change_request: SignedChangeRequest):
        logger.debug('Sending %s to %s', signed_change_request, address)
        # TODO(dmu) LOW: Consider using `json=signed_change_request.dict()`, but this requires serialization
        #                enums to basic types in dict while still having enums in model instance representation
        return self.http_post(address, 'signed-change-requests', data=signed_change_request.json())

    def send_scr_to_node(self, node: Node, signed_change_request: SignedChangeRequest):
        for address in node.addresses:
            try:
                return self.send_scr_to_address(address, signed_change_request)
            except requests.RequestException:
                logger.warning('Error sending %s to %s at %s', signed_change_request, node, address)
        else:
            raise ConnectionError(f'Could not send signed change request to {node}')