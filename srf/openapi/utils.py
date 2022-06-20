"""
@Author:WangYuXiang
@E-mile:Hill@3io.cc
@CreateTime:2022/6/3-10:58
@DependencyLibrary:[...]
@MainFunction:None
@FileDoc:
    utils is python file
@ChangeHistory:
    datetime action why
    2022/6/3-10:58 [Create] utils.py
"""
import copy
import re

from srf.status import HttpStatus

default_responses = {
    HttpStatus.HTTP_200_OK: {
        "description": "Successful Response",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "title": "message",
                            "type": "string"
                        },
                        "code": {
                            "title": "message",
                            "type": "integer"
                        },
                        "data": {
                            "title": "data",
                            "type": "object"
                        },
                    }
                }
            }
        }
    }
}


def parsing_url(uri_tuple):
    parameters = []
    uri = ''
    for i in uri_tuple:
        if '<' in i:
            key_field = re.search('<(.*):', i).groups()[0]
            field_type = re.search(':(.*)>', i).groups()[0]
            uri += '/{' + key_field + '}'
            parameters.append({
                "required": True,
                "schema": {
                    "title": key_field,
                    "type": 'string',
                },
                "name": key_field,
                "in": "path"
            })
        else:
            uri += '/' + i
    return uri, parameters


def get_request_body(serializer_obj, method):
    request_body = {'content': {}}
    if method in ['post', 'put', 'patch']:
        schema = {
            'schema': serializer_obj._doc_request_schema()
        }
        request_body = {
            'content': {
                'application/x-www-form-urlencoded': schema,
                'application/json': schema,
            }
        }
    return request_body


def gen_response(code: int, description: str, data: dict):
    response = {
        code: {
            "description": description,
            "content": {
                "application/json": {
                    "schema":
                        {
                            "type": "object",
                            "properties": {
                                'message': {
                                    "title": '提示',
                                    "type": 'string'
                                },
                                'code': {
                                    "title": '状态码',
                                    "type": 'integer'
                                },
                                **data
                            }
                        }
                }
            }
        }
    }
    return response


def get_responses(serializer_obj, method, detail):
    if method == 'get' and detail:
        data = {'data': {
            "title": '状态码',
            "type": 'array',
            "items": serializer_obj._doc_response_schema()
        }}
    else:
        data = {'data': serializer_obj._doc_response_schema()}

    return gen_response(HttpStatus.HTTP_200_OK, "Successful Response", data)


def get_security_by_view(obj, security_schemes: dict):
    security = []
    for i in obj.authentication_classes:
        authentication_name = i.__name__
        security_item = i.get_security()
        if authentication_name not in security_schemes:
            security_schemes[authentication_name] = security_item
        security.append({authentication_name: []})
    return security


def get_parameters(view_class, detail, method):
    parameter_list = []

    if hasattr(view_class, 'filter_class') and not detail and method == 'get':
        parameter_list.extend(view_class.filter_class.parameters(view_class))

    if hasattr(view_class, 'pagination_class') and view_class.pagination_class and not detail and method == 'get':
        parameter_list.extend(view_class.pagination_class.parameters())

    return parameter_list


def comm_handler_request_body(base_class, config, method):
    request_serializer_class = config.get('request_serializer_class')
    if not request_serializer_class:
        if hasattr(base_class, 'serializer_class'):
            request_serializer_class = base_class.serializer_class
    if request_serializer_class:
        partial = False
        if method == 'patch':
            partial = True
        serializer_obj = request_serializer_class(partial=partial)
    else:
        return {'content': {}}
    schema = {
        'schema': serializer_obj._doc_request_schema()
    }
    request_body = {
        'content': {
            'application/json': schema,
            'application/x-www-form-urlencoded': schema,
        }
    }
    return request_body


def comm_handler_response(base_class, config, method, detail):
    responses = copy.deepcopy(default_responses)
    response_serializer_class = config.get('response_serializer_class')
    if not response_serializer_class:
        if hasattr(base_class, 'serializer_class'):
            response_serializer_class = base_class.serializer_class
    if response_serializer_class:
        serializer_obj = response_serializer_class()
        responses = get_responses(serializer_obj, method, detail)
    return responses


def comm_handler_summary(handler):
    if hasattr(handler, 'summary'):
        return handler.summary
    return handler.__qualname__


def comm_handler_description(handler):
    description = 'Use `@openapi.description("add your description")` add your description'
    if hasattr(handler, 'description'):
        description = handler.description
    return description


def comm_handler_tags(view_openapi_config, method_openapi_config, uri_tuple):
    if 'tags' in view_openapi_config:
        tags = view_openapi_config['tags']
    elif 'tags' in method_openapi_config:
        tags = method_openapi_config['tags']
    else:
        tags = uri_tuple[:1]
    return tags
