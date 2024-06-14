# -*- coding: utf-8 -*-
# @Date : Fri May 31 2024
# @Author : v_wyxgwang
# @File : blueprint.py.py
# @Software: VSCode
import inspect
import re
from datetime import datetime
from os.path import abspath, dirname, realpath

from sanic.blueprints import Blueprint
from sanic.response import json, redirect

from rest_framework.openapi3.definitions import Response

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
        print("Building OpenAPI 3.0.0 specification...")
        set_operation_default_tags(app)
        for url_tuple, route in app.router.routes_all.items():
            if route.name and "static" in route.name:
                continue
            if hasattr(route.handler, 'base_class'):
                build_classview_specification(url_tuple, route)
            else:
                build_methodview_specification(url_tuple, route)
        add_static_info_to_spec_from_config(app, specification)

    #     # --------------------------------------------------------------- #
    #     # Blueprint Tags
    #     # --------------------------------------------------------------- #

    #     for blueprint_name, handler in get_blueprinted_routes(app):
    #         operation = operations[handler]
    #         if not operation.tags:
    #             operation.tag(blueprint_name)

    #     # --------------------------------------------------------------- #
    #     # Operations
    #     # --------------------------------------------------------------- #
    #     for (
    #         uri,
    #         route_name,
    #         route_parameters,
    #         method_handlers,
    #     ) in get_all_routes(app, oas3_blueprint.url_prefix):

    #         # --------------------------------------------------------------- #
    #         # Methods
    #         # --------------------------------------------------------------- #

    #         uri = uri if uri == "/" else uri.rstrip("/")

    #         for method, _handler in method_handlers:

    #             if method == "OPTIONS":
    #                 continue

    #             if hasattr(_handler, "view_class"):
    #                 _handler = getattr(_handler.view_class, method.lower())
    #             operation = operations[_handler]

    #             if operation._exclude:
    #                 continue

    #             docstring = inspect.getdoc(_handler)

    #             if docstring:
    #                 operation.autodoc(docstring)

    #             # operation ID must be unique, and it isnt currently used for
    #             # anything in UI, so dont add something meaningless
    #             # if not hasattr(operation, "operationId"):
    #             #     operation.operationId = "%s_%s" % (
    #             #       method.lower(), route.name
    #             #     )

    #             for _parameter in route_parameters:
    #                 if any((param.fields["name"] == _parameter.name for param in operation.parameters)):
    #                     continue

    #                 operation.parameter(_parameter.name, _parameter.cast, "path")

    #             specification.operation(uri, method, operation)

    #     add_static_info_to_spec_from_config(app, specification)

    return oas3_blueprint


def add_static_info_to_spec_from_config(app, specification):
    """
    Reads app.config and sets attributes to specification according to the
    desired values.

    Modifies specification in-place and returns None
    """
    specification._do_describe(
        getattr(app.config, "API_TITLE", "API"),
        getattr(app.config, "API_VERSION", "1.0.0"),
        getattr(app.config, "API_DESCRIPTION", None),
        getattr(app.config, "API_TERMS_OF_SERVICE", None),
    )

    specification._do_license(
        getattr(app.config, "API_LICENSE_NAME", None),
        getattr(app.config, "API_LICENSE_URL", None),
    )

    specification._do_contact(
        getattr(app.config, "API_CONTACT_NAME", None),
        getattr(app.config, "API_CONTACT_URL", None),
        getattr(app.config, "API_CONTACT_EMAIL", None),
    )

    for scheme in getattr(app.config, "API_SCHEMES", ["http"]):
        host = getattr(app.config, "API_HOST", None)
        basePath = getattr(app.config, "API_BASEPATH", "")
        if host is None or basePath is None:
            continue

        specification.url(f"{scheme}://{host}/{basePath}")
