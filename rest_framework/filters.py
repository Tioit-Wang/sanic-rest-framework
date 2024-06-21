"""
@Author: TioitWang
@Email: me@tioit.cc
@CreateTime: 2021/3/10 17:25
@DependencyLibrary: None
@MainFunction: None
@FileDoc:
    filters.py
    File description
@ChangeHistory:
    datetime action why
    example:
    2021/3/10 17:25 change 'Fix bug'
"""

from tortoise.models import Q
from rest_framework.constant import LOOKUP_SEP
from rest_framework.openapi3.definitions import Parameter


class ORMAndFilter:
    """
    Query using AND logic.
    This class directly provides ORM filters.
    """

    lookup_prefixes = {
        '^': 'istartswith',
        '$': 'iendswith',
        '>=': 'gte',
        '<=': 'lte',
        '>': 'gt',
        '<': 'lt',
        '=': 'contains',
        '@': 'icontains',
    }

    def __init__(self, request, view):
        self.view = view
        self.request = request

    def get_search_fields(self):
        """
        Search fields are obtained from the view, but the request
        is always passed to this method. Subclasses can override
        this method to dynamically change search fields based on the
        request content.
        """
        return getattr(self.view, 'search_fields', None)

    @property
    def orm_filter(self):
        """
        Filter the incoming queryset based on defined search fields.
        """
        orm_filters = []
        search_fields = self.get_search_fields()
        if not search_fields:
            return Q(*orm_filters)
        orm_filters.extend(Q(**self.construct_orm_filter(search_field)) for search_field in search_fields)
        return Q(*orm_filters)

    def dismantle_search_field(self, search_field):
        """
        Disassemble search fields with special characters.
        """
        for prefix, lookup in self.lookup_prefixes.items():
            if search_field.startswith(prefix):
                return search_field[len(prefix) :], lookup
        return search_field, None

    def construct_orm_filter(self, search_field):
        """
        Construct filter parameters suitable for ORM.
        """
        field_name, lookup_suffix = self.dismantle_search_field(search_field)
        query_name = field_name.split(':')[0] if ':' in field_name else field_name
        args = self.request.args

        if query_name not in args:
            return {}

        orm_lookup = LOOKUP_SEP.join([field_name, lookup_suffix]) if lookup_suffix else field_name
        return {orm_lookup: self.get_filter_value(query_name)}

    def get_filter_value(self, field_name):
        """
        Get value from request based on field name.
        """
        values = self.request.args.get(field_name, [])
        return ''.join(values)

    @staticmethod
    def to_openapi(view):
        parameters = []
        search_fields = getattr(view, 'search_fields', None)
        if search_fields is None:
            return parameters

        for search_field in search_fields:
            _, field_name = search_field.split(':')
            parameters.append(Parameter.make(field_name, str, 'query', required=False))
        return parameters


class ORMOrFilter(ORMAndFilter):
    """
    Query using OR logic.
    This class directly provides ORM filters.
    """

    @property
    def orm_filter(self):
        """
        Filter the incoming queryset based on defined search fields.
        """
        orm_filters = []
        search_fields = self.get_search_fields()
        if not search_fields:
            return Q(*orm_filters)
        orm_filters.extend(Q(**self.construct_orm_filter(search_field)) for search_field in search_fields)
        return Q(*orm_filters, join_type=Q.OR)
