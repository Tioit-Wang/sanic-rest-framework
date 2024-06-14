"""
@Author:TioitWang
@E-mile:me@tioit.cc
@CreateTime:2022/6/6-12:30
@DependencyLibrary:[...]
@MainFunction:None
@FileDoc:
    exception_handlers is python file
@ChangeHistory:
    datetime action why
    2022/6/6-12:30 [Create] exception_handlers.py
"""
import logging

from rest_framework.response import JsonResponse
from rest_framework.status import ResponseCode

logger = logging.getLogger()


async def catch_api_exc(request, exception):
    return exception.response


async def catch_serializer_validation_exc(request, exception):
    return JsonResponse({
        'message': 'Request validation error',
        'code': ResponseCode.FAIL_CODE,
        'data': exception.error_detail
    })
