"""
@Author：WangYuXiang
@E-mile：Hill@3io.cc
@CreateTime：2021/3/10 17:25
@DependencyLibrary：无
@MainFunction：无
@FileDoc： 
    filters.py
    文件说明
@ChangeHistory:
    datetime action why
    example:
    2021/3/10 17:25 change 'Fix bug'
        
"""
from tortoise.models import Q

from srf.constant import LOOKUP_SEP

__all__ = ('ORMAndFilter', 'ORMOrFilter')

from srf.openapi import Parameters, Parameter


class ORMAndFilter:
    """以And进行查询
        该类将直接得到 ORM_Filter
    """
    lookup_prefixes = {
        '^': 'istartswith',
        '$': 'iendswith',
        '>': 'gt',
        '<': 'lt',
        '>=': 'gte',
        '<=': 'lte',
        '=': 'contains',
        '@': 'icontains'
    }

    def __init__(self, request, view):
        """
        :param request: 当前请求
        :param view: 当前视图
        """
        self.view = view
        self.request = request

    def get_search_fields(self):
        """
        搜索字段是从视图获取的，但请求始终是
        传递给此方法。子类可以重写此方法以
        根据请求内容动态更改搜索字段。
        """
        return getattr(self.view, 'search_fields', None)

    @property
    def orm_filter(self):
        """
        根据定义的搜索字段过滤传入的queryset
        :return: Q object
        """
        orm_filters = []
        search_fields = self.get_search_fields()
        if not search_fields:
            return Q(*orm_filters)
        orm_filters.extend(Q(**self.construct_orm_filter(search_field)) for search_field in search_fields)

        return Q(*orm_filters)

    def dismantle_search_field(self, search_field):
        """
        拆解带有特殊字符的搜索字段
        :param search_field: 搜索字段
        :return: (field_name, lookup_suffix)
        """
        lookup_suffix_keys = list(self.lookup_prefixes.keys())
        lookup_suffix = None
        field_name = search_field
        for lookup_suffix_key in lookup_suffix_keys:
            if lookup_suffix_key in search_field:
                lookup_suffix = self.lookup_prefixes[lookup_suffix_key]
                field_name = search_field[len(lookup_suffix_key):]
                return field_name, lookup_suffix
        return field_name, lookup_suffix

    def construct_orm_filter(self, search_field):
        """
        构造适用于orm的过滤参数
        :param search_field: 搜索字段
        :return:
        """
        field_name, lookup_suffix = self.dismantle_search_field(search_field)
        args = self.request.args

        if field_name not in args:
            return {}
        if lookup_suffix:
            orm_lookup = LOOKUP_SEP.join([field_name, lookup_suffix])
        else:
            orm_lookup = field_name
        return {orm_lookup: self.get_filter_value(field_name)}

    def get_filter_value(self, field_name):
        """
        根据字段名从请求中得到值
        :param field_name: 字段名
        :return:
        """
        values = self.request.args.get(field_name)
        return ''.join(values)

    @staticmethod
    def parameters(view) -> list:
        parameters = Parameters()

        search_fields = getattr(view, 'search_fields', None)
        ret = []
        if search_fields is None:
            return ret
        for search_field in search_fields:
            lookup_suffix_keys = list(ORMAndFilter.lookup_prefixes.keys())
            field_name = search_field
            for lookup_suffix_key in lookup_suffix_keys:
                if lookup_suffix_key in search_field:
                    field_name = search_field[len(lookup_suffix_key):]
            parameters.add(Parameter(field_name, 'string'))

        return parameters.parameters


class ORMOrFilter(ORMAndFilter):
    """以And进行查询
        该类将直接得到 ORM_Filter
    """

    @property
    def orm_filter(self):
        """
        根据定义的搜索字段过滤传入的queryset
        :return:  Q object
        """
        orm_filters = []
        search_fields = self.get_search_fields()
        if not search_fields:
            return orm_filters
        orm_filters.extend(Q(**self.construct_orm_filter(search_field)) for search_field in search_fields)

        return Q(*orm_filters, join_type=Q.OR)
