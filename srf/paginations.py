"""
@Author：WangYuXiang
@E-mile：Hill@3io.cc
@CreateTime：2021/3/11 17:37
@DependencyLibrary：无
@MainFunction：无
@FileDoc： 
    paginations.py
    分页器
@ChangeHistory:
    datetime action why
    example:
    2021/3/11 17:37 change 'Fix bug'
        
"""

from srf.exceptions import APIException
from srf.openapi import Parameters, Parameter
from srf.status import HttpStatus
from srf.utils import replace_query_param


class ORMPagination:
    """通用分页器"""
    page_size = 60
    page_query_param = 'page'
    page_size_query_param = 'page_size'
    max_page_size = 10000

    def __init__(self, request, view):
        """
        :param request: 当前请求
        :param view: 当前视图
        """
        self.view = view
        self.request = request

    def set_count(self, count):
        """
        设置集合
        :param count:
        :return:
        """
        self.count = count

    @property
    def next_page(self):
        """得到下一页的页码，不存在则返回None"""
        assert hasattr(self, 'count'), '必须先执行 `.set_count()` 函数才能使用.next_page'
        if self.query_page * self.page_size + self.page_size >= self.count:
            return None
        return self.query_page + 1

    @property
    def next_link(self):
        """
        得到下一页的请求地址
        :return: None or String
        """
        page = self.next_page
        if not page:
            return None
        uri = self.request.server_path
        query_string = f'?{self.request.query_string}'
        query_string = replace_query_param(query_string, self.page_query_param, page)
        query_string = replace_query_param(query_string, self.page_size_query_param, self.page_size)
        return uri + query_string

    @property
    def previous_page(self):
        """得到上一页页码，不存在则返回None"""
        assert hasattr(self, 'count'), '必须先执行 `.set_count()` 函数才能使用.previous_page'
        if self.query_page * self.page_size <= 0:
            return None
        return self.query_page - 1

    @property
    def previous_link(self):
        """
        得到上一页的请求地址
        :return: None or String
        """
        if not self.previous_page:
            return None
        uri = self.request.server_path
        query_string = f'?{self.request.query_string}'
        query_string = replace_query_param(query_string, self.page_query_param, self.previous_page)
        query_string = replace_query_param(query_string, self.page_size_query_param, self.page_size)
        return uri + query_string

    @property
    def query_page(self):
        """得到页数"""
        try:
            page = int(self.request.args.get(self.page_query_param, 1))
        except ValueError as exc:
            raise APIException('发生错误的分页数据', http_status=HttpStatus.HTTP_400_BAD_REQUEST)
        page = max(page, 1)
        return page

    @property
    def query_page_size(self):
        """得到页记录数"""
        try:
            page = int(self.request.args.get(self.page_size_query_param, self.page_size))
            if page > self.max_page_size:
                raise APIException('分页内容大小超出最大限制', http_status=HttpStatus.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            raise APIException('发生错误的分页数据', http_status=HttpStatus.HTTP_400_BAD_REQUEST)
        return page

    @staticmethod
    def parameters() -> list:
        # sourcery skip: inline-immediately-returned-variable
        parameters = Parameters()
        parameters.add(Parameter('page', 'int'))
        parameters.add(Parameter('page_size', 'int'))

        return parameters.parameters
