import logging
import os
import ssl
from typing import Union

import jwt
import requests

logger = logging.getLogger()


class OpenIDValidator:

    def __init__(self):
        self.verify_ssl = self._get_verify_ssl()
        self.ssl_context = self._get_ssl_context(self.verify_ssl)
        self.openid_conf = self._get_openid_conf(self.verify_ssl)

    @staticmethod
    def _get_verify_ssl() -> bool:
        return os.getenv('VERIFY_SSL', 'true').lower() != 'false'

    @staticmethod
    def _get_ssl_context(verify_ssl: bool) -> ssl.SSLContext:
        if verify_ssl:
            return ssl.SSLContext()
        else:
            return ssl.SSLContext(verify_mode=ssl.CERT_NONE)

    @staticmethod
    def _get_openid_conf(verify_ssl: bool) -> Union[dict, None]:
        url = os.environ['OIDC_CONFIGURATION_URL']
        r = requests.get(url, verify=verify_ssl)
        r.raise_for_status()
        return r.json()

    def validate(self, access_token):
        if os.getenv('DISABLE_AUTH', 'false').lower() == 'true':
            return self.validate_fake_token(access_token)
        url = self.openid_conf['jwks_uri']
        jwks_client = jwt.PyJWKClient(url, ssl_context=self.ssl_context)

        signing_key = jwks_client.get_signing_key_from_jwt(access_token)
        token_header = jwt.get_unverified_header(access_token)
        try:
            data = jwt.decode(
                access_token,
                signing_key.key,
                algorithms=[token_header['alg']],
                audience="account",
                options={"verify_exp": True},
            )
        except jwt.exceptions.InvalidTokenError as e:
            logger.debug(msg="Authentication failed", exc_info=e)
            raise
        return data

    def validate_fake_token(self, access_token):
        """ Validate fake token for testing purpose

        This expects a jwt token using the HMAC+SHA (HS) algorithm and the
        secret 'fake-secret'
        """
        token_header = jwt.get_unverified_header(access_token)
        try:
            data = jwt.decode(
                access_token,
                'fake-secret',
                algorithms=[token_header['alg']],
                audience="account",
                options={"verify_exp": True},
            )
        except jwt.exceptions.InvalidTokenError as e:
            logger.debug(msg="Authentication failed", exc_info=e)
            raise
        return data
