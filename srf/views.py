"""
@Author: WangYuXiang
@E-mile: Hill@3io.cc
@CreateTime: 2021/1/19 15:44
@DependencyLibrary:
@MainFunction：
@FileDoc:
    login.py
    基础视图文件
    BaseView    只实现路由分发的基础视图
    GeneralView 通用视图，可以基于其实现增删改查，提供权限套件
    ViewSetView 视图集视图，可以配合Mixin实现复杂的视图集，
                数据来源基于模型查询集,可以配合Route组件实现便捷的路由管理



"""
from datetime import datetime
from traceback import format_exc

from sanic.log import logger
from sanic.response import json, HTTPResponse
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction
from ujson import dumps

from srf.authentication import BaseAuthenticate
from srf.constant import ALL_METHOD
from srf.exceptions import APIException, ValidationException
from srf.permissions import BasePermission

__all__ = ('BaseView', 'APIView')

from srf.status import HttpStatus, RuleStatus

from srf.utils import run_awaitable


class BaseView:
    """只实现路由分发的基础视图
    在使用时应当开放全部路由 ALL_METHOD
    app.add_route('/test', BaseView.as_view(), 'test', ALL_METHOD)
    如需限制路由则在其他地方注明
    app.add_route('/test', BaseView.as_view(), 'test', ALL_METHOD)
    注意以上方法的报错是不可控的
    """

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def as_view(cls, *class_args, **class_kwargs):
        # 返回的响应方法闭包
        async def view(request, *args, **kwargs):
            self = view.base_class(*class_args, **class_kwargs)

            self.request = request
            self.args = args
            self.kwargs = kwargs
            self.app = request.app
            return await self.dispatch(request, *args, **kwargs)

        view.funcs = {i: getattr(cls, i) for i in cls._effective_method()}
        view.methods = cls._effective_method()
        view.base_class = cls
        view.view_obj = cls(*class_args, **class_kwargs)
        view.API_DOC_CONFIG = class_kwargs.get('API_DOC_CONFIG')  # 未来的API文档配置属性+
        view.__module__ = cls.__module__
        view.__name__ = cls.__name__
        return view

    @classmethod
    def _effective_method(cls):
        methods = []
        for method in ALL_METHOD:
            method = method.lower()
            if hasattr(cls, method):
                methods.append(method)
        return methods

    # def _get_doc(self):

    async def dispatch(self, request, *args, **kwargs):
        """分发路由"""
        request.user = None
        method = request.method.lower()

        if not hasattr(self, method):
            return HTTPResponse('405请求方法错误', status=405)
        handler = getattr(self, method, None)
        return await run_awaitable(handler, request, *args, **kwargs)


class APIView(BaseView):
    """通用视图，可以基于其实现增删改查，提供权限套件"""
    authentication_classes = ()
    permission_classes = ()
    is_transaction = True

    async def dispatch(self, request, *args, **kwargs):
        """分发路由"""
        request.user = None
        method = request.method.lower()

        if not hasattr(self, method):
            return self.json_response(msg=f'发生错误：未找到{method}方法', status=RuleStatus.STATUS_0_FAIL,
                                      http_status=HttpStatus.HTTP_405_METHOD_NOT_ALLOWED)

        handler = getattr(self, method, None)
        try:
            await self.initial(request, *args, **kwargs)
            if self.is_transaction:
                async with in_transaction():
                    response = await run_awaitable(handler, request=request, *args, **kwargs)
            else:
                response = await run_awaitable(handler, request=request, *args, **kwargs)
        except APIException as exc:
            response = self.handle_exception(exc)
        except ValidationException as exc:
            response = self.error_json_response(exc.error_detail, '数据验证失败')
        except AssertionError as exc:
            raise exc
        except IntegrityError as exc:
            response = self.error_json_response(msg=str(exc), status=RuleStatus.STATUS_0_FAIL)
        except Exception as exc:
            logger.error(f'{format_exc()}')

            msg = f"发生致命的未知错误，请在服务器查看时间为{datetime.now().strftime('%F %T')}的日志"
            response = self.json_response(msg=msg, status=RuleStatus.STATUS_0_FAIL,
                                          http_status=HttpStatus.HTTP_500_INTERNAL_SERVER_ERROR)
        return response

    def handle_exception(self, exc: APIException):
        return self.json_response(**exc.response_data())

    def json_response(self, data=None, msg="OK", status=RuleStatus.STATUS_1_SUCCESS,
                      http_status=HttpStatus.HTTP_200_OK):
        """
        Json 相应体
        :param data: 返回的数据主题
        :param msg: 前台提示字符串
        :param status: 前台约定状态，供前台判断是否成功
        :param http_status: Http响应数据
        :return:
        """
        if data is None:
            data = {}
        response_body = {
            'data': data,
            'message': msg,
            'status': status
        }
        return json(body=response_body, status=http_status, dumps=dumps)

    def success_json_response(self, data=None, msg="Success", **kwargs):
        """
        快捷的成功的json响应体
        :param data: 返回的数据主题
        :param msg: 前台提示字符串
        :return: json
        """
        status = kwargs.pop('status', RuleStatus.STATUS_1_SUCCESS)
        http_status = kwargs.pop('http_status', HttpStatus.HTTP_200_OK)
        return self.json_response(data=data, msg=msg, status=status, http_status=http_status)

    def error_json_response(self, data=None, msg="Fail", **kwargs):
        """
        快捷的失败的json响应体
        :param data: 返回的数据主题
        :param msg: 前台提示字符串
        :return: json
        """
        status = kwargs.pop('status', RuleStatus.STATUS_0_FAIL)
        http_status = kwargs.pop('http_status', HttpStatus.HTTP_400_BAD_REQUEST)
        return self.json_response(data=data, msg=msg, status=status, http_status=http_status)

    def get_authenticators(self):
        """
        实例化并返回此视图可以使用的身份验证器列表
        """
        authentications = []
        for auth in self.authentication_classes:
            if isinstance(auth, BaseAuthenticate):
                authentications.append(auth)
            else:
                authentications.append(auth())
        return authentications

    async def check_authentication(self, request):
        """
        检查权限 查看是否拥有权限，并在此处为Request.User 赋值
        :param request: 请求
        :return:
        """
        for authenticators in self.get_authenticators():
            await authenticators.authenticate(request, self)

    def get_permissions(self):
        """
        实例化并返回此视图所需的权限列表
        """
        permissions = []
        for permission in self.permission_classes:
            if isinstance(permission, BasePermission):
                permissions.append(permission)
            else:
                permissions.append(permissions())
        return permissions

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
        pass

    async def initial(self, request, *args, **kwargs):
        """
        在请求分发之前执行初始化操作，用于检查权限及检查基础内容
        """
        await self.check_authentication(request)
        await self.check_permissions(request)
        await self.check_throttles(request)
