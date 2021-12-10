import pytest

from node.blockchain.inner_models import NodeDeclarationSignedChangeRequestMessage, SignedChangeRequest
from node.core.utils.collections import deep_update


@pytest.mark.django_db
def test_node_declaration_signed_change_request_can_be_sent_via_api(api_client, regular_node, regular_node_key_pair):
    message = NodeDeclarationSignedChangeRequestMessage(
        node=regular_node,
        account_lock=regular_node.identifier,
    )

    signed_change_request = SignedChangeRequest.create_from_signed_change_request_message(
        message=message,
        signing_key=regular_node_key_pair.private,
    )
    assert signed_change_request.message
    assert signed_change_request.signer
    assert signed_change_request.signature

    payload = signed_change_request.dict()
    # TODO(dmu) CRITICAL: Expect `assert response.status_code == 204` instead once `perform_create()` is implemented
    #                     https://thenewboston.atlassian.net/browse/BC-167
    with pytest.raises(NotImplementedError, match=f'"signer":"{regular_node.identifier}"'):
        api_client.post('/api/signed-change-request/', payload)


@pytest.mark.skip('Not implemented yet')
def test_type_validation_for_node_declaration():
    # TODO(dmu) HIGH: Implement similar to `node.blockchain.tests.test_models.test_signed_change_request.
    #                 test_node_declaration.test_type_validation_for_node_declaration_message_on_parsing`
    #                 !!! Reuse the same input data
    #                 https://thenewboston.atlassian.net/browse/BC-170
    raise NotImplementedError


@pytest.mark.django_db
@pytest.mark.parametrize(
    'update_with', (
        (dict(signature='0' * 128)),
        (dict(signer='0' * 64)),
        (dict(message=dict(account_lock=('0' * 64)))),
    )
)
def test_signature_validation_for_node_declaration(update_with, api_client, regular_node, regular_node_key_pair):
    message = NodeDeclarationSignedChangeRequestMessage(
        node=regular_node,
        account_lock=regular_node.identifier,
    )
    signed_change_request = SignedChangeRequest.create_from_signed_change_request_message(
        message=message,
        signing_key=regular_node_key_pair.private,
    )
    payload = signed_change_request.dict()

    wrong_payload = deep_update(payload, update_with)

    response = api_client.post('/api/signed-change-request/', wrong_payload)
    assert response.status_code == 400
    assert response.json() == {'non_field_errors': ['Invalid signature']}
