"""
@Author:WangYuXiang
@E-mile:Hill@3io.cc
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

from srf.response import JsonResponse
from srf.status import ResponseCode

logger = logging.getLogger()


async def catch_api_exc(request, exception):
    return exception.response


async def catch_serializer_validation_exc(request, exception):
    return JsonResponse({
        'message': 'Request validation error',
        'code': ResponseCode.FAIL_CODE,
        'data': exception.error_detail
    })
