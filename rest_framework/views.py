"""
@Author: TioitWang
@E-mile: me@tioit.cc
@CreateTime: 2021/1/19 15:44
@DependencyLibrary:
@MainFunction:
@FileDoc:
    login.py
    基础视图文件
    BaseView    只实现路由分发的基础视图
    GeneralView 通用视图，可以基于其实现增删改查，提供权限套件
    ViewSetView 视图集视图，可以配合Mixin实现复杂的视图集，
                数据来源基于模型查询集,可以配合Route组件实现便捷的路由管理



"""

from tortoise.transactions import in_transaction

from rest_framework.constant import DEFAULT_METHOD_MAP

__all__ = ('BaseView', 'APIView')

from rest_framework.exceptions import APIException
from rest_framework.response import JsonResponse
from rest_framework.settings import srf_settings
from rest_framework.status import HttpStatus, ResponseCode
from rest_framework.utils import run_awaitable


class BaseView:
    """只实现路由分发的基础视图
    在使用时应当开放全部路由 ALL_METHOD
    app.add_route('/test', BaseView.as_view(), 'test', ALL_METHOD)
    如需限制路由则在其他地方注明
    app.add_route('/test', BaseView.as_view(), 'test', ALL_METHOD)
    注意以上方法的报错是不可控的
    """

    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def as_view(cls, method_map=DEFAULT_METHOD_MAP, *class_args, **class_kwargs):
        async def view(request, *args, **kwargs):
            self = view.base_class(*class_args, **class_kwargs)
            # Methods the mapping
            view_method_map = {}
            for method, action in method_map.items():
                handler = getattr(self, action, None)
                if handler:
                    setattr(self, method, handler)
                    view_method_map[method] = action

            # Check the validity of the request method
            if request.method.lower() not in view_method_map:
                msg = f'Method `{request.method}` is not allowed.'
                raise APIException(msg, status=HttpStatus.HTTP_405_METHOD_NOT_ALLOWED)

            self.request = request
            self.args = args
            self.kwargs = kwargs
            self.app = request.app
            return await self.dispatch(request, *args, **kwargs)

        methods = [i.lower() for i in method_map.keys() if hasattr(cls, i.lower())]

        view.detail = class_kwargs.get('detail', None)
        view.methods = methods
        view.base_class = cls
        view.__module__ = cls.__module__
        view.__name__ = cls.__name__
        return view

    async def dispatch(self, request, *args, **kwargs):
        method = request.method.lower()
        handler = getattr(self, method, None)
        return await run_awaitable(handler, request, *args, **kwargs)


class APIView(BaseView):
    """通用视图，可以基于其实现增删改查，提供权限套件"""

    authentication_classes = (*srf_settings.DEFAULT_AUTHENTICATION_CLASSES,)
    permission_classes = (*srf_settings.DEFAULT_PERMISSION_CLASSES,)
    throttle_classes = (*srf_settings.DEFAULT_THROTTLE_CLASSES,)
    throttle_rates = (*srf_settings.DEFAULT_THROTTLE_RATES,)
    transaction = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _transaction(self):
        transaction = srf_settings.VIEW_TRANSACTION
        return transaction or bool(self.transaction)

    async def dispatch(self, request, *args, **kwargs):
        """分发路由"""
        method = request.method.lower()
        handler = getattr(self, method, None)
        try:
            await self.initial(request, *args, **kwargs)
            if self._transaction():
                async with in_transaction():
                    response = await handler(request=request, *args, **kwargs)
                    # response = await run_awaitable(handler, request=request, *args, **kwargs)
            else:
                response = await handler(request=request, *args, **kwargs)
                # response = await run_awaitable(handler, request=request, *args, **kwargs)
        except Exception as exc:
            return await self.handle_exception(exc)
        return response

    def json_response(self, data=None, msg="Request succeeded.", code=ResponseCode.SUCCESS_CODE, status=HttpStatus.HTTP_200_OK):
        """
        Json Response
        :param data: Response.Body.Data
        :param msg: messages
        :param code: custom code
        :param status: http status
        :return:
        """
        if data is None:
            data = {}
        return JsonResponse({'data': data, 'message': msg, 'code': code}, status=status)

    def success_json_response(self, data=None, msg="Request succeeded."):
        """
        快捷的成功的json响应体
        :param data: 返回的数据主题
        :param msg: 前台提示字符串
        :return: json
        """
        return self.json_response(data=data, msg=msg, code=ResponseCode.SUCCESS_CODE, status=HttpStatus.HTTP_200_OK)

    def error_json_response(self, data=None, msg="Request fail.", **kwargs):
        """
        快捷的失败的json响应体
        :param data: 返回的数据主题
        :param msg: 前台提示字符串
        :return: json
        """
        return self.json_response(data=data, msg=msg, code=ResponseCode.FAIL_CODE, status=HttpStatus.HTTP_200_OK)

    def get_authenticators(self):
        """
        实例化并返回此视图可以使用的身份验证器列表
        """

        return [auth() for auth in self.authentication_classes]

    def get_permissions(self):
        """
        实例化并返回此视图所需的权限列表
        """
        return [permission() for permission in self.permission_classes]

    def get_throttles(self):
        """
        实例化并返回此视图可以使用的身份验证器列表
        """
        throttles = []
        for throttle in self.throttle_classes:
            for rate in self.throttle_rates:
                throttles.append(throttle(rate))
        return throttles

    async def check_authentication(self, request):
        """
        检查权限 查看是否拥有权限，并在此处为Request.User 赋值
        :param request: 请求
        :return:
        """
        for authenticators in self.get_authenticators():
            await authenticators.authenticate(request, self)

    async def check_permissions(self, request):
        """
        检查是否应允许该请求，如果不允许该请求，
        则在 has_permission 中引发一个适当的异常。
        :param request: 当前请求
        :return:
        """
        for permission in self.get_permissions():
            await permission.has_permission(request, self)

    async def check_object_permissions(self, request, obj):
        """
        检查是否应允许给定对象的请求, 如果不允许该请求，
        则在 has_object_permission 中引发一个适当的异常。
            常用于 get_object() 方法
        :param request: 当前请求
        :param obj: 需要鉴权的模型对象
        :return:
        """
        for permission in self.get_permissions():
            await permission.has_object_permission(request, self, obj)

    async def check_throttles(self, request):
        """
        检查范围频率。
        则引发一个 APIException 异常。
        :param request:
        :return:
        """
        for throttle in self.get_throttles():
            await throttle.allow_request(request, self)

    async def initial(self, request, *args, **kwargs):
        """
        在请求分发之前执行初始化操作，用于检查权限及检查基础内容
        """
        await self.check_authentication(request)
        await self.check_permissions(request)
        await self.check_throttles(request)

    async def handle_exception(self, exception):
        if isinstance(exception, APIException):
            return exception.response
        raise exception
