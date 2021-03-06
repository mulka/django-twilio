# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from django.conf import settings
from django.http import HttpResponse
from django.test import Client, TestCase
from django.test.utils import override_settings

from twilio.twiml.voice_response import VoiceResponse

from django_dynamic_fixture import G

from django_twilio2.models import Caller

from .views import (response_view, str_view, bytes_view, verb_view,
                    BytesView, StrView, VerbView, ResponseView)
from .utils import TwilioRequestFactory


class TwilioViewTestCase(TestCase):

    urls = 'test_project.test_app.urls'

    def setUp(self):

        self.regular_caller = G(Caller, phone_number='+12222222222', blacklisted=False)
        self.blocked_caller = G(Caller, phone_number='+13333333333', blacklisted=True)

        self.factory = TwilioRequestFactory(
            token=settings.TWILIO_AUTH_TOKEN,
            enforce_csrf_checks=True,
        )

        # Test URIs.
        self.uris = []
        self.str_uri = '/test_app/decorators/str_view/'
        self.uris.append(self.str_uri)
        self.str_class_uri = '/test_app/decorators/str_class_view/'
        self.uris.append(self.str_class_uri)
        self.bytes_uri = '/test_app/decorators/bytes_view/'
        self.uris.append(self.bytes_uri)
        self.bytes_class_uri = '/test_app/decorators/bytes_class_view/'
        self.uris.append(self.bytes_class_uri)
        self.verb_uri = '/test_app/decorators/verb_view/'
        self.uris.append(self.verb_uri)
        self.verb_class_uri = '/test_app/decorators/verb_class_view/'
        self.uris.append(self.verb_class_uri)
        self.response_uri = '/test_app/decorators/response_view/'
        self.uris.append(self.response_uri)
        self.response_class_uri = '/test_app/decorators/response_class_view/'
        self.uris.append(self.response_class_uri)

    def _assertStatusCode(self, actual_code, expected_code, uri):
            return self.assertEqual(
                actual_code, expected_code,
                '%s != %s. Bad uri is: %s' % (actual_code, expected_code, uri)
            )

    def test_requires_get_or_post(self):
        c = Client(enforce_csrf_checks=True)
        with override_settings(DEBUG=False):
            for uri in self.uris:
                self._assertStatusCode(c.get(uri).status_code, 403, uri)
                self._assertStatusCode(c.post(uri).status_code, 403, uri)
                self._assertStatusCode(c.head(uri).status_code, 405, uri)
                self._assertStatusCode(c.options(uri).status_code, 405, uri)
                self._assertStatusCode(c.put(uri).status_code, 405, uri)
                self._assertStatusCode(c.delete(uri).status_code, 405, uri)

    def test_all_return_statuses_when_debug_true(self):
        c = Client(enforce_csrf_checks=True)
        with override_settings(DEBUG=True):
            for uri in self.uris:
                self._assertStatusCode(c.get(uri).status_code, 200, uri)
                self._assertStatusCode(c.post(uri).status_code, 200, uri)
                self._assertStatusCode(c.head(uri).status_code, 200, uri)
                self._assertStatusCode(c.options(uri).status_code, 200, uri)
                if uri.endswith('class_view/'):
                    self._assertStatusCode(c.put(uri).status_code, 405, uri)
                    self._assertStatusCode(c.delete(uri).status_code, 405, uri)
                else:
                    self._assertStatusCode(c.put(uri).status_code, 200, uri)
                    self._assertStatusCode(c.delete(uri).status_code, 200, uri)

    def test_allows_post(self):
        request = self.factory.post(self.str_uri)
        self.assertEqual(str_view(request).status_code, 200)

    def test_class_view_allows_post(self):
        request = self.factory.post(self.str_class_uri)
        self.assertEqual(StrView.as_view()(request).status_code, 200)

    def test_decorator_preserves_metadata(self):
        self.assertEqual(str_view.__name__, 'str_view')

    def test_class_decorator_preserves_metadata(self):
        self.assertEqual(StrView.dispatch.__name__, 'dispatch')

    @override_settings(TWILIO_ACCOUNT_SID=None)
    @override_settings(TWILIO_AUTH_TOKEN=None)
    def test_missing_settings_return_forbidden(self):
        with override_settings(DEBUG=False):
            self.assertEqual(self.client.post(self.str_uri).status_code, 403)
            self.assertEqual(self.client.post(self.str_class_uri).status_code, 403)
        with override_settings(DEBUG=True):
            self.assertEqual(self.client.post(self.str_uri).status_code, 200)
            self.assertEqual(self.client.post(self.str_class_uri).status_code, 200)

    def test_missing_signature_returns_forbidden(self):
        with override_settings(DEBUG=False):
            self.assertEqual(self.client.post(self.str_uri).status_code, 403)
            self.assertEqual(self.client.post(self.str_class_uri).status_code, 403)
        with override_settings(DEBUG=True):
            self.assertEqual(self.client.post(self.str_uri).status_code, 200)
            self.assertEqual(self.client.post(self.str_class_uri).status_code, 200)

    def test_incorrect_signature_returns_forbidden(self):
        with override_settings(DEBUG=False):
            request = self.factory.post(
                self.str_uri,
                HTTP_X_TWILIO_SIGNATURE='fake_signature',
            )
            self.assertEqual(str_view(request).status_code, 403)
        with override_settings(DEBUG=True):
            self.assertEqual(str_view(request).status_code, 200)

    def test_incorrect_signature_returns_forbidden_class_view(self):
        with override_settings(DEBUG=False):
            request = self.factory.post(
                self.str_class_uri,
                HTTP_X_TWILIO_SIGNATURE='fake_signature',
            )
            self.assertEqual(StrView.as_view()(request).status_code, 403)
        with override_settings(DEBUG=True):
            self.assertEqual(StrView.as_view()(request).status_code, 200)

    def test_no_from_field(self):
        request = self.factory.post(self.str_uri)
        self.assertEqual(str_view(request).status_code, 200)

    def test_no_form_field_class_view(self):
        request = self.factory.post(self.str_class_uri)
        self.assertEqual(StrView.as_view()(request).status_code, 200)

    def test_from_field_no_caller(self):
        request = self.factory.post(self.str_uri, {'From': '+12222222222'})
        self.assertEqual(str_view(request).status_code, 200)

    def tst_form_field_no_caller_class_view(self):
        request = self.factory.post(self.str_class_uri, {'From': '+12222222222'})
        self.assertEqual(StrView.as_view()(request).status_code, 200)

    def test_blacklist_works(self):
        with override_settings(DEBUG=False):
            request = self.factory.post(self.str_uri, {'From': '+13333333333'})
            response = str_view(request)
            r = VoiceResponse()
            r.reject()
            self.assertEqual(
                response.content,
                str(r).encode('utf-8'),
            )
        with override_settings(DEBUG=True):
            request = self.factory.post(self.str_uri, {'From': '+13333333333'})
            response = str_view(request)
            r = VoiceResponse()
            r.reject()
            self.assertEqual(
                response.content,
                str(r).encode('utf-8'),
            )

    def test_black_list_works_class_view(self):
        with override_settings(DEBUG=False):
            request = self.factory.post(self.str_class_uri, {'From': '+13333333333'})
            response = StrView.as_view()(request)
            r = VoiceResponse()
            r.reject()
            self.assertEqual(
                response.content,
                str(r).encode('utf-8'),
            )
        with override_settings(DEBUG=True):
            request = self.factory.post(self.str_class_uri, {'From': '+13333333333'})
            response = StrView.as_view()(request)
            r = VoiceResponse()
            r.reject()
            self.assertEqual(
                response.content,
                str(r).encode('utf-8'),
            )

    def test_decorator_modifies_str(self):
        request = self.factory.post(self.str_uri)
        self.assertIsInstance(str_view(request), HttpResponse)

    def test_decorator_modifies_str_class_view(self):
        request = self.factory.post(self.str_class_uri)
        self.assertIsInstance(StrView.as_view()(request), HttpResponse)

    def test_decorator_modifies_bytes(self):
        request = self.factory.post(self.bytes_uri)
        self.assertIsInstance(bytes_view(request), HttpResponse)

    def test_decorator_modifies_bytes_class_view(self):
        request = self.factory.post(self.bytes_class_uri)
        self.assertIsInstance(BytesView.as_view()(request), HttpResponse)

    def test_decorator_modifies_verb(self):
        request = self.factory.post(self.verb_uri)
        self.assertIsInstance(verb_view(request), HttpResponse)

    def test_decorator_modifies_verb_class_view(self):
        request = self.factory.post(self.verb_class_uri)
        self.assertIsInstance(VerbView.as_view()(request), HttpResponse)

    def test_decorator_preserves_http_response(self):
        request = self.factory.post(self.response_uri)
        self.assertIsInstance(response_view(request), HttpResponse)

    def test_decorator_preserves_http_response_class_view(self):
        request = self.factory.post(self.response_class_uri)
        self.assertIsInstance(ResponseView.as_view()(request), HttpResponse)

    def test_override_forgery_protection_off_debug_off(self):
        with override_settings(DJANGO_TWILIO_FORGERY_PROTECTION=False, DEBUG=False):
            request = self.factory.post(
                self.str_uri,
                HTTP_X_TWILIO_SIGNATURE='fake_signature',
            )
            self.assertEqual(str_view(request).status_code, 200)

    def test_override_forgery_protection_off_debug_off_class_view(self):
        with override_settings(DJANGO_TWILIO_FORGERY_PROTECTION=False, DEBUG=False):
            request = self.factory.post(
                self.str_class_uri,
                HTTP_X_TWILIO_SIGNATURE='fake_signature',
            )
            self.assertEqual(StrView.as_view()(request).status_code, 200)

    def test_override_forgery_protection_off_debug_on(self):
        with override_settings(DJANGO_TWILIO_FORGERY_PROTECTION=False, DEBUG=True):
            request = self.factory.post(
                self.str_uri,
                HTTP_X_TWILIO_SIGNATURE='fake_signature',
            )
            self.assertEqual(str_view(request).status_code, 200)

    def test_override_forgery_protection_off_debug_on_class_view(self):
        with override_settings(DJANGO_TWILIO_FORGERY_PROTECTION=False, DEBUG=True):
            request = self.factory.post(
                self.str_class_uri,
                HTTP_X_TWILIO_SIGNATURE='fake_signature',
            )
            self.assertEqual(StrView.as_view()(request).status_code, 200)

    def test_override_forgery_protection_on_debug_off(self):
        with override_settings(DJANGO_TWILIO_FORGERY_PROTECTION=True, DEBUG=False):
            request = self.factory.post(
                self.str_uri,
                HTTP_X_TWILIO_SIGNATURE='fake_signature',
            )
            self.assertEqual(str_view(request).status_code, 403)

    def test_override_forgery_protection_on_debug_off_class_view(self):
        with override_settings(DJANGO_TWILIO_FORGERY_PROTECTION=True, DEBUG=False):
            request = self.factory.post(
                self.str_class_uri,
                HTTP_X_TWILIO_SIGNATURE='fake_signature',
            )
            self.assertEqual(StrView.as_view()(request).status_code, 403)

    def test_override_forgery_protection_on_debug_on(self):
        with override_settings(DJANGO_TWILIO_FORGERY_PROTECTION=True, DEBUG=True):
            request = self.factory.post(
                self.str_uri,
                HTTP_X_TWILIO_SIGNATURE='fake_signature',
            )
            self.assertEqual(str_view(request).status_code, 403)

    def test_override_forgery_protection_on_debug_on_class_view(self):
        with override_settings(DJANGO_TWILIO_FORGERY_PROTECTION=True, DEBUG=True):
            request = self.factory.post(
                self.str_class_uri,
                HTTP_X_TWILIO_SIGNATURE='fake_signature',
            )
            self.assertEqual(StrView.as_view()(request).status_code, 403)
