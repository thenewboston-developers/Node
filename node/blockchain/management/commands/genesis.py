import json
from contextlib import closing
from urllib.parse import urlparse
from urllib.request import urlopen

from django.conf import settings
from django.core.management.base import BaseCommand

from node.blockchain.inner_models import (
    GenesisBlockMessage, GenesisSignedChangeRequestMessage, Node, SignedChangeRequest
)
from node.blockchain.models.block import Block
from node.core.utils.cryptography import derive_public_key
from node.core.utils.types import AccountLock


def is_valid_url(source):
    try:
        parsed = urlparse(source)
        return all((parsed.scheme, parsed.netloc, parsed.path))
    except Exception:
        return False


def read_source(source):
    if is_valid_url(source):
        fo = urlopen(source)
    else:
        fo = open(source)

    with closing(fo) as fo:
        return json.load(fo)


class Command(BaseCommand):
    help = 'Create genesis block'  # noqa: A003

    def add_arguments(self, parser):
        parser.add_argument('source', help='file paths or/and URLs to serialized blockchain state or URL')

    def handle(self, *args, **options):
        source = options['source']
        account_root_file = read_source(source)
        signing_key = settings.SIGNING_KEY
        account_number = derive_public_key(signing_key)

        request_message = GenesisSignedChangeRequestMessage.create_from_alpha_account_root_file(
            account_lock=AccountLock(account_number),
            account_root_file=account_root_file,
        )

        request = SignedChangeRequest.create_from_signed_change_request_message(
            message=request_message,
            signing_key=signing_key,
        )

        # TODO(dmu) CRITICAL: Autodetect node address
        #                     https://thenewboston.atlassian.net/browse/BC-150
        primary_validator_node = Node(
            identifier=account_number,
            addresses=['http://non-existing-address-4643256.com:8555/'],
            fee=4,
        )

        block_message = GenesisBlockMessage.create_from_signed_change_request(
            request=request,
            primary_validator_node=primary_validator_node,
        )

        Block.objects.create_from_block_message(
            message=block_message,
            signing_key=signing_key,
        )
