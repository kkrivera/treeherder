from mohawk import Sender
from rest_framework import status
from rest_framework.decorators import APIView
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from treeherder.webapp.api import permissions


class AuthenticatedView(APIView):
    permission_classes = (permissions.HasHawkPermissionsOrReadOnly,)

    def get(self, request, *args, **kwargs):
        return Response({'foo': 'bar'})

    def post(self, request, *args, **kwargs):
        return Response({'foo': 'bar'})

factory = APIRequestFactory()
url = 'http://testserver/'


def _get_hawk_response(client_id, secret, method='GET',
                       content='', content_type='application/json'):
    auth = {
        'id': client_id,
        'key': secret,
        'algorithm': 'sha256'
    }
    sender = Sender(auth, url, method,
                    content=content,
                    content_type=content_type)

    do_request = getattr(factory, method.lower())
    request = do_request(url,
                         data=content,
                         content_type=content_type,
                         # factory.get doesn't set the CONTENT_TYPE header from
                         # `content_type` so the header has to be set manually.
                         CONTENT_TYPE=content_type,
                         HTTP_AUTHORIZATION=sender.request_header)

    view = AuthenticatedView.as_view()
    return view(request)


def test_get_hawk_authorized(client_credentials):
    response = _get_hawk_response(client_credentials.client_id,
                                  str(client_credentials.secret))
    assert response.status_code == status.HTTP_200_OK
    assert response.data == {'foo': 'bar'}


def test_get_hawk_unauthorized(client_credentials):
    client_credentials.authorized = False
    client_credentials.save()
    response = _get_hawk_response(client_credentials.client_id,
                                  str(client_credentials.secret))
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {'detail': ('No authorised credentials '
                                        'found with id %s') % client_credentials.client_id}


def test_get_no_auth():
    request = factory.get(url)
    view = AuthenticatedView.as_view()
    response = view(request)
    assert response.status_code == status.HTTP_200_OK
    assert response.data == {'foo': 'bar'}


def test_post_hawk_authorized(client_credentials):
    response = _get_hawk_response(client_credentials.client_id,
                                  str(client_credentials.secret), method='POST',
                                  content="{'this': 'that'}")
    assert response.status_code == status.HTTP_200_OK
    assert response.data == {'foo': 'bar'}


def test_post_hawk_unauthorized(client_credentials):
    client_credentials.authorized = False
    client_credentials.save()
    response = _get_hawk_response(client_credentials.client_id,
                                  str(client_credentials.secret), method='POST',
                                  content="{'this': 'that'}")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {'detail': ('No authorised credentials '
                                        'found with id %s') % client_credentials.client_id}


def test_post_no_auth():
    request = factory.post(url)
    view = AuthenticatedView.as_view()
    response = view(request)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {'detail': 'Authentication credentials were not provided.'}
