"""
@Author: WangYuXiang
@E-mile: Hill@3io.cc
@CreateTime: 2021/1/20 20:03
@DependencyLibrary: 无
@MainFunction：无
@FileDoc:
    exceptions.py
    序列化器文件
"""

from srf.status import HttpStatus, RuleStatus


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
    def __init__(self, message, status=RuleStatus.STATUS_0_FAIL, http_status=HttpStatus.HTTP_500_INTERNAL_SERVER_ERROR,
                 *args, **kwargs):
        self.message = message
        self.status = status
        self.http_status = http_status

    def response_data(self):
        return {
            'msg': self.message,
            'status': self.status,
            'http_status': self.http_status
        }


class PermissionDenied(APIException):
    def __init__(self, message='没有操作权限，请完成对应授权', status=RuleStatus.STATUS_0_FAIL, http_status=HttpStatus.HTTP_403_FORBIDDEN,
                 *args, **kwargs):
        super().__init__(message, status, http_status, *args, **kwargs)


class AuthenticationDenied(APIException):
    def __init__(self, message='身份验证失败，请重新登录', status=RuleStatus.STATUS_0_FAIL, http_status=HttpStatus.HTTP_401_UNAUTHORIZED,
                 *args, **kwargs):
        super().__init__(message, status, http_status, *args, **kwargs)
