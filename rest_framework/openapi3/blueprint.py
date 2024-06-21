# -*- coding: utf-8 -*-
# @Date : Fri May 31 2024
# @Author : v_wyxgwang
# @File : blueprint.py.py
# @Software: VSCode
import inspect
import re
import socket
from datetime import datetime
from os.path import abspath, dirname, realpath

from sanic.blueprints import Blueprint
from sanic.log import logger
from sanic.response import json, redirect

from rest_framework.openapi3.definitions import Response
from rest_framework.settings import srf_settings

# from ..utils import get_all_routes, get_blueprinted_routes
from . import operations, specification

DEFAULT_SWAGGER_UI_CONFIG = {
    "apisSorter": "alpha",
    "operationsSorter": "alpha",
}


def set_operation_default_tags(app):
    for blueprint in app.blueprints.values():
        if not hasattr(blueprint, "routes"):
            continue
        for route in blueprint.routes:
            if hasattr(route.handler, "base_class"):
                handler = route.handler
                base_class = handler.base_class
                base_class_name = base_class.__name__
                for method in handler.methods:
                    operation_id = f'{base_class.__module__}.{base_class_name}.{method}'
                    operation = operations[operation_id]
                    if not operation.tags:
                        operation.tag(blueprint.name)
            else:
                # TODO: add function view support
                pass


def build_classview_specification(url_tuple, route):
    uri = route.uri
    handler = route.handler
    base_class = handler.base_class
    for method in handler.methods:
        # 自动生成文档
        _handler = getattr(base_class, method)
        operation = operations[_handler]
        if operation._exclude:
            continue

        docstring = inspect.getdoc(_handler)
        if docstring:
            operation.autodoc(docstring)

        # URL 参数
        for parameter in route.params.values():
            uri = re.sub(
                "<" + parameter.name + ".*?>",
                "{" + parameter.name + "}",
                uri,
            )
            if any((param.fields["name"] == parameter.name for param in operation.parameters)):
                continue
            maps = {
                'int': int,
                'float': float,
                'str': str,
                'strorempty': str,
                'alpha': str,
                'slug': str,
                'path': str,
                'ymd': datetime,
                'uuid': str,
                'regex': str,
            }
            operation.parameter(parameter.name, maps.get(parameter.label, str), "path", default=None)

        # 如果没有发现默认的Response就默认加入 200的成功响应与错误响应
        if not operation.responses:
            success_response = {"application/json": {"code": 1, "msg": "success", "data": {}}}
            error_response = {"application/json": {"code": 0, "msg": "error", "data": {}}}
            # 自动生成200成功响应
            operation.responses["200"] = Response.make(success_response, description="Success")
            # 自动生成默认的错误响应
            operation.responses["default"] = Response.make(error_response, description="Error")

        if not operation.security:
            if base_class.authentication_classes:
                for auth_class in base_class.authentication_classes:
                    operation.security.append(auth_class.to_openapi())

        specification.operation(uri, method, operation)


def build_methodview_specification(url_tuple, route):
    pass


def blueprint_factory():
    oas3_blueprint = Blueprint("openapi", url_prefix="/swagger")

    dir_path = dirname(realpath(__file__))
    dir_path = abspath(dir_path + "/ui")

    oas3_blueprint.static("", dir_path)

    # Redirect "/swagger" to "/swagger/"
    @oas3_blueprint.route("", strict_slashes=True)
    def index(request):
        return redirect("{}/".format(oas3_blueprint.url_prefix))

    @oas3_blueprint.route("/swagger.json")
    def spec(request):
        return json(specification.build().serialize())

    @oas3_blueprint.route("/swagger-config")
    def config(request):
        return json(
            getattr(
                request.app.config,
                "SWAGGER_UI_CONFIGURATION",
                DEFAULT_SWAGGER_UI_CONFIG,
            )
        )

    @oas3_blueprint.listener("before_server_start")
    def build_spec(app, loop):
        set_operation_default_tags(app)
        for url_tuple, route in app.router.routes_all.items():
            if route.name and "static" in route.name:
                continue
            if hasattr(route.handler, 'base_class'):
                build_classview_specification(url_tuple, route)
            else:
                build_methodview_specification(url_tuple, route)
        add_static_info_to_spec_from_config(specification)

        host = socket.gethostbyname(socket.gethostname())
        logger.info("Swagger UI: http://%s:%s%s/index.html", host, app.config.PORT, oas3_blueprint.url_prefix)
        logger.info("Swagger UI: http://%s:%s%s/index.html", app.config.HOST, app.config.PORT, oas3_blueprint.url_prefix)
        logger.info("OpenAPI 3.0.0 specification built successfully.")

    return oas3_blueprint


def add_static_info_to_spec_from_config(specification):
    """
    Reads app.config and sets attributes to specification according to the
    desired values.

    Modifies specification in-place and returns None
    """
    specification._do_describe(
        srf_settings.OPENAPI_TITLE,
        srf_settings.VERSION,
        srf_settings.OPENAPI_DESCRIPTION,
        srf_settings.OPENAPI_TERMS_OF_SERVICE,
    )

    specification._do_license(
        # getattr(app.config, "API_LICENSE_NAME", None),
        # getattr(app.config, "API_LICENSE_URL", None),
        srf_settings.OPENAPI_LICENSE_NAME,
        srf_settings.OPENAPI_LICENSE_URL,
    )

    specification._do_contact(
        srf_settings.OPENAPI_CONTACT_NAME,
        srf_settings.OPENAPI_CONTACT_URL,
        srf_settings.OPENAPI_CONTACT_EMAIL,
    )

    for server in srf_settings.OPENAPI_SERVERS:
        specification.url(server)
