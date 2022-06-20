"""
@Author: WangYuXiang
@E-mile: Hill@3io.cc
@CreateTime: 2021/1/20 20:03
@DependencyLibrary: 无
@MainFunction:无
@FileDoc:
    exceptions.py
    序列化器文件
"""
from srf.response import JsonResponse
from srf.status import HttpStatus, ResponseCode


class CacheExpireEXC(Exception):
    def __init__(self, message="缓存超时", *args, **kwargs):
        self.message = message

    def __str__(self) -> str:
        return f'<CacheExpireEXC: {self.message}>'


class CacheNoFoundEXC(Exception):
    def __init__(self, message="找不到指定引擎", *args, **kwargs):
        self.message = message

    def __str__(self) -> str:
        return f'<CacheNoFoundEXC: {self.message}>'


class ValidatorAssertError(Exception):
    pass


class ValidationException(Exception):
    """验证错误类"""
    default_detail = '无效的输入'
    default_code = 'invalid'

    def __init__(self, error_detail=None, code=None):
        if error_detail is None:
            error_detail = self.default_detail
        if code is None:
            code = self.default_code

        if not isinstance(error_detail, dict) and not isinstance(error_detail, list):
            error_detail = [error_detail]

        self.code = code
        self.error_detail = error_detail


class APIException(Exception):
    def __init__(self, message, data=None, code=ResponseCode.FAIL_CODE, status=HttpStatus.HTTP_200_OK, **kwargs):
        self.message = message
        self.status = status
        self.code = code
        self.data = {} if data is None else data
        self.kwargs = kwargs

    @property
    def response(self):
        return JsonResponse({
            'code': self.code,
            'message': self.message,
            'data': self.data,
            **self.kwargs
        }, status=self.status)


class PermissionDenied(APIException):
    def __init__(self, message='No permission.'):
        super().__init__(message, status=HttpStatus.HTTP_403_FORBIDDEN)


class AuthenticationDenied(APIException):
    def __init__(self, message='Authentication failed. Please log in again.'):
        super().__init__(message, status=HttpStatus.HTTP_401_UNAUTHORIZED)


class Throttled(APIException):
    def __init__(self, message='Too many requests. Please try again later.'):
        super().__init__(message, status=HttpStatus.HTTP_429_TOO_MANY_REQUESTS)
