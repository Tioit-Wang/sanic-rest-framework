"""
@Author:TioitWang
@E-mile:me@tioit.cc
@CreateTime:2021/3/11 17:37
@DependencyLibrary:无
@MainFunction:无
@FileDoc:
    paginations.py
    分页器
@ChangeHistory:
    datetime action why
    example:
    2021/3/11 17:37 change 'Fix bug'
"""

from math import ceil

from rest_framework.exceptions import APIException

# from srf.openapi.openapi import Parameter, Parameters
from rest_framework.openapi3.definitions import Parameter
from rest_framework.response import JsonResponse
from rest_framework.status import HttpStatus, ResponseCode


class BasePagination:
    page_size = 20
    page_query_param = 'page'
    page_size_query_param = 'page_size'
    max_page_size = 10000

    @classmethod
    def to_openapi(cls) -> list:
        return [
            Parameter.make('page', int, 'query', required=False),
            Parameter.make('page_size', int, 'query', required=False),
        ]

    async def paginate_queryset(self, queryset, request, view=None):
        pass

    async def get_paginated_response(self, data):
        pass


class ORMPageNumberPagination(BasePagination):
    page_size = 20
    page_query_param = 'page'
    page_size_query_param = 'page_size'
    max_page_size = 2000

    def __init__(self):
        self.__page_size = self.page_size
        self.__page = 0
        self.__total_count = 0
        self.__total_pages = 0

    # @classmethod
    # def parameters(cls) -> list:
    #     parameters = Parameters()
    #     parameters.add(Parameter(cls.page_query_param, 'integer'))
    #     parameters.add(Parameter(cls.page_size_query_param, 'integer'))
    #     return parameters.parameters

    def get_query_page(self, request):
        """得到页数"""
        try:
            page = int(request.args.get(self.page_query_param, 1))
        except ValueError as exc:
            raise APIException(f'{self.page_query_param} must be integer.', status=HttpStatus.HTTP_400_BAD_REQUEST)
        page = max(page, 1)
        return page

    def get_query_page_size(self, request):
        """得到页记录数"""
        try:
            page = int(request.args.get(self.page_size_query_param, self.page_size))
        except ValueError as exc:
            raise APIException(f'{self.page_size_query_param} must be integer.', status=HttpStatus.HTTP_400_BAD_REQUEST)
        if page > self.max_page_size:
            raise APIException(f'{self.page_size_query_param} too big.', status=HttpStatus.HTTP_400_BAD_REQUEST)
        return page

    async def get_total_count(self, queryset):
        return await queryset.count()

    async def get_total_pages(self):
        return ceil(self.__total_count / self.__page_size)

    def get_next_page(self):
        if self.__page >= self.__total_pages:
            return None
        return self.__page + 1

    def get_prev_page(self):
        if self.__page <= 1:
            return None
        return self.__page - 1

    async def paginate_queryset(self, queryset, request, view=None):
        """Return queryset"""
        self.__total_count = await self.get_total_count(queryset)
        self.__page = self.get_query_page(request)
        self.__page_size = self.get_query_page_size(request)
        self.__total_pages = await self.get_total_pages()
        offset = (self.__page - 1) * self.__page_size
        return queryset.limit(self.__page_size).offset(offset)

    async def get_paginated_response(self, data):
        return JsonResponse(
            {
                'code': ResponseCode.SUCCESS_CODE,
                'message': 'Request succeeded.',
                'data': {
                    'page': self.__page,
                    'page_size': self.__page_size,
                    'total_count': self.__total_count,
                    'total_pages': self.__total_pages,
                    'next': self.get_next_page(),
                    'par': self.get_prev_page(),
                    'results': data,
                },
            }
        )
