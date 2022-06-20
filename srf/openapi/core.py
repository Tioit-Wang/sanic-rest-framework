"""
@Author:WangYuXiang
@E-mile:Hill@3io.cc
@CreateTime:2022/6/3-10:58
@DependencyLibrary:[...]
@MainFunction:None
@FileDoc: 
    core is python file
@ChangeHistory:
    datetime action why
    2022/6/3-10:58 [Create] core.py
"""
import logging
import os
from functools import partial, wraps
from inspect import isfunction
from os.path import dirname, abspath, realpath

from sanic import Sanic
from sanic.response import file_stream, html
from sanic_plugin_toolkit import SanicPlugin

from srf.openapi.builders import OpenAPIStore
from srf.openapi.utils import parsing_url, get_parameters, comm_handler_response, \
    comm_handler_request_body, comm_handler_tags
from srf.views import BaseView


def openapi_json_view(request):
    return file_stream(os.path.join(request.app.config.get('PROJECT_PATH'), 'openapi.json'))


def openapi_ui_view(request, ui):
    dir_path = dirname(realpath(__file__))
    if ui == 'redoc':
        html_path = abspath(dir_path + "/templates/redoc.html")
    else:
        html_path = abspath(dir_path + "/templates/swagger.html")

    with open(html_path, "r") as f:
        page = f.read()
    return html(page.replace('{URL}', request.app.config.get('OPENAPI_JSON_URL_PREFIX', '/openapi.json')))
    # return html("""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Swagger UI</title><link
    # rel="stylesheet"type="text/css"href="./openapi_static/swagger-ui.css"/>
    # <style>html{box-sizing:border-box;overflow:-moz-scrollbars-vertical;overflow-y:scroll}
    # *,*:before,*:after{box-sizing:inherit}body{margin:0;background:#fafafa}</style></head>
    # <body><div id="swagger-ui"></div><script src="./openapi_static/swagger-ui-bundle.js"charset="UTF-8">
    # </script><script src="./openapi_static/swagger-ui-standalone-preset.js"charset="UTF-8"></script>
    # <script>window.onload=function(){window.ui=SwaggerUIBundle({url:".{URL}",dom_id:'#swagger-ui',
    # deepLinking:true,presets:[SwaggerUIBundle.presets.apis,],plugins:[SwaggerUIBundle.plugins.DownloadUrl],})};
    # </script></body></html>""".replace('{URL}', request.app.config.get('OPENAPI_JSON_URL_PREFIX', '/openapi.json')))


class SRFOpenAPIHelper(SanicPlugin):
    """
    一个app应用加载器
    可以方便快捷的加载和管理apps程序

    :param SanicPlugin: sanic插件管理框架
    """

    def __init__(self):
        self.scheme = {
            "openapi": "3.0.0",
            "info": {},
            "servers": [],
            'paths': {},
            'components': {
                "securitySchemes": {}
            },
        }
        super(SRFOpenAPIHelper, self).__init__()

    # noinspection PyTypedDict
    def _set_scheme_info(self, title: str):
        self.scheme['info'] = {
            "title": title,
            "version": "1"
        }

    def _set_scheme_servers(self, config: dict):
        for server in config.get('OPENAPI_SERVERS', []):
            if 'url' in server:
                self.scheme['servers'].append({
                    "url": server['url'],
                    "description": server.get('description', f"{server['url']} server"),
                })

    def _comm_handler_security(self, config, base_class):
        security = []
        authentication_classes = config.get('authentication_classes', [])
        if hasattr(base_class, 'authentication_classes'):
            authentication_classes.extend(base_class.authentication_classes)
        for authentication_class in authentication_classes:
            authentication_name = authentication_class.__name__
            security_item = authentication_class.get_security()
            if authentication_name not in self.scheme['components']['securitySchemes']:
                self.scheme['components']['securitySchemes'][authentication_name] = security_item
            security.append({authentication_name: []})
        return security

    def _comm_handler_openapi_hidden(self, handler):
        return hasattr(handler, 'hidden') and not handler.hidden

    def _set_paths(self, routes):
        path = {}
        store = OpenAPIStore()
        for uri_tuple, route in routes.items():
            view_handler = route.handler
            if hasattr(view_handler, 'base_class'):
                # handlers = view_handler.handlers
                base_class = view_handler.base_class
                if self._comm_handler_openapi_hidden(base_class):
                    continue

                for method in view_handler.methods:
                    if self._comm_handler_openapi_hidden(base_class):
                        continue
                    detail = getattr(view_handler, 'detail', None)
                    class_module_path = f'{base_class.__module__}.{base_class.__name__}'
                    method_module_path = f'{base_class.__module__}.{base_class.__name__}.{method}'

                    operation_id = f'operationId.{base_class.__name__}.{method}.{detail}'
                    view_openapi_config = store.get(class_module_path, {})
                    method_openapi_config = store.get(method_module_path, {})

                    tags = comm_handler_tags(view_openapi_config, method_openapi_config, uri_tuple)
                    uri, url_parameters = parsing_url(uri_tuple)
                    parameters = get_parameters(base_class, detail, method)
                    parameters.extend(url_parameters)
                    security = self._comm_handler_security(method_openapi_config, base_class)

                    if uri not in path:
                        path[uri] = {}
                    description = 'Use `@openapi.description("add your description")` add your description'
                    path[uri][method] = {
                        'summary': method_openapi_config.get('summary', f'{base_class.__name__}.{method}'),
                        'description': method_openapi_config.get('description', description),
                        'tags': tags,
                        'operationId': operation_id,
                        'parameters': parameters,
                        'security': security,
                        'responses': comm_handler_response(base_class, method_openapi_config, method, detail)
                    }
                    if method in ['post', 'put', 'patch']:
                        path[uri][method]['requestBody'] = comm_handler_request_body(base_class, method_openapi_config,
                                                                                     method)
            else:

                pass
                # Function View
        self.scheme['paths'] = path

    def on_registered(self, context, reg, *args, **kwargs):
        """
        插件注册时调用的事件

        :param context: 插件上下文，可以用来存储内容
        :param reg: 已注册的内容
        :raises AppStructureError: APP结构错误异常
        """
        info = partial(context.log, logging.INFO)
        warn = partial(context.log, logging.WARN)
        info('SRF-OPENAPI plug-in has been loaded, '
             'All apis using CBV view will automatically generate SwaggerUI that complies with OpenAPI 3.0 rules')
        sanic_app: Sanic = context.app
        config = sanic_app.config
        self._set_scheme_info(sanic_app.name)
        self._set_scheme_servers(config)
        self._set_paths(sanic_app.router.routes_all)

        openapi_json_url_prefix = config.get('OPENAPI_JSON_URL_PREFIX', '/openapi.json')
        swagger_ui_url_prefix = f"/{config.get('SWAGGER_UI_URL_PREFIX', 'openapi')}/<ui:string>"

        sanic_app.add_route(openapi_json_view, openapi_json_url_prefix)
        sanic_app.add_route(openapi_ui_view, swagger_ui_url_prefix)

    @staticmethod
    def set(serializer_class, to='all'):
        def decorator_func(func):
            @wraps(func)
            def wrapper():
                key = f'{func.__module__}.{func.__qualname__}'
                if to == 'request' or to == 'all':
                    OpenAPIStore().add(key, 'request_serializer_class', serializer_class)
                if to == 'response' or to == 'all':
                    OpenAPIStore().add(key, 'response_serializer_class', serializer_class)
                return func

            return wrapper()

        return decorator_func

    @staticmethod
    def summary(summary: str):
        def decorator_func(func):
            @wraps(func)
            def wrapper():
                key = f'{func.__module__}.{func.__qualname__}'
                OpenAPIStore().add(key, 'summary', summary)
                return func

            return wrapper()

        return decorator_func

    @staticmethod
    def description(description: str):
        def decorator_func(func):
            @wraps(func)
            def wrapper():
                key = f'{func.__module__}.{func.__qualname__}'
                OpenAPIStore().add(key, 'description', description)
                return func

            return wrapper()

        return decorator_func

    @staticmethod
    def tags(*tags: str):
        def decorator_func(func):
            @wraps(func)
            def wrapper():
                if not isfunction(func) and issubclass(func, (BaseView,)):
                    OpenAPIStore().add(f'{func.__module__}.{func.__qualname__}', 'tags', [*tags])
                else:
                    key = f'{func.__module__}.{func.__qualname__}'
                    OpenAPIStore().add(key, 'tags', [*tags])
                return func

            return wrapper()

        return decorator_func

    @staticmethod
    def hidden(func):
        @wraps(func)
        def wrapper():
            key = f'{func.__module__}.{func.__qualname__}'
            OpenAPIStore().add(key, 'hidden', True)
            return func

        return wrapper()


openapi = SRFOpenAPIHelper()
__all__ = ['openapi', 'SRFOpenAPIHelper']
