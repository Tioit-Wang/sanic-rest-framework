"""
@Author:TioitWang
@E-mile:me@tioit.cc
@CreateTime:2021/3/31 16:21
@DependencyLibrary:无
@MainFunction:无
@FileDoc:
    authentication.py
    文件说明
@ChangeHistory:
    datetime action why
    example:
    2021/3/31 16:21 change 'Fix bug'
"""

import jwt
from jwt.exceptions import DecodeError, ExpiredSignatureError

from settings import TOKEN_KEY
from rest_framework.exceptions import AuthenticationDenied
from rest_framework.openapi3.definitions import SecurityScheme
from rest_framework.request import SRFRequest


class BaseAuthenticate:
    token_key = None

    @classmethod
    def to_openapi(cls):
        """Returns an OpenAPI specification for the security scheme"""
        pass

    def authenticate(self, request: SRFRequest, view, **kwargs):
        """Validates the authentication and returns a User object"""
        pass


class BaseTokenAuthenticate(BaseAuthenticate):
    """Base authentication class using JWT tokens"""

    token_key = TOKEN_KEY

    @classmethod
    def to_openapi(cls):
        """Returns an OpenAPI specification for the security scheme"""
        return SecurityScheme(type="apiKey", name=cls.token_key, location="header", description="Token")

    async def authenticate(self, request: SRFRequest, view, **kwargs):
        """Authentication logic"""
        token = request.headers.get(self.token_key)
        if not token:
            raise AuthenticationDenied('Token is required')
        if 'Bearer' in token and len(token) > 7:
            _, token = token.split()
        if not token:
            raise AuthenticationDenied(f'`{self.token_key}` must exist in the request header.')

        token_secret = request.app.config.TOKEN_SECRET
        try:
            token_info = self.decode_token(token, token_secret)
        except ExpiredSignatureError:
            raise AuthenticationDenied('Login timeout.')
        except DecodeError:
            raise AuthenticationDenied('Invalid Token.')

        await self._authenticate(request, view, token_info, **kwargs)

    async def _authenticate(self, request: SRFRequest, view, token_info: dict, **kwargs):
        """Core authentication logic"""
        pass

    def decode_token(self, token: str, token_secret: str):
        """
        Decodes the JWT token

        Args:
            token (str): The JWT token
            token_secret (str): The secret key to decode the token

        Returns:
            dict: The decoded token information
        """
        return jwt.decode(token, token_secret, algorithms=['HS256'])
