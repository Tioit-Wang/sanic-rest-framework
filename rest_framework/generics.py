import logging
import traceback

from rest_framework import mixins
from rest_framework.exceptions import APIException
from rest_framework.filters import ORMAndFilter
from rest_framework.status import HttpStatus
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

__all__ = ('GenericAPIView', 'CreateAPIView', 'ListAPIView', 'RetrieveAPIView',
           'DestroyAPIView', 'UpdateAPIView', 'ListCreateAPIView', 'RetrieveUpdateAPIView',
           'RetrieveDestroyAPIView', 'RetrieveUpdateDestroyAPIView')


class GenericAPIView(APIView):
    """
    视图集视图，可以配合Mixin实现复杂的视图集，
    数据来源基于模型查询集,可以配合Route组件实现便捷的路由管理
    """
    # 数据来源
    queryset = None
    # 数据序列化器
    serializer_class = None
    # 主键
    lookup_field = 'pk'

    # 分页器
    pagination_class = None

    # 过滤器
    filter_class = ORMAndFilter
    search_fields = None

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)

    async def get_object(self):
        """
        返回视图显示的对象。
        如果您需要提供非标准的内容，则可能要覆盖此设置
        queryset查找。
        """
        queryset = await self.get_queryset()

        lookup_field = self.lookup_field

        assert lookup_field in self.kwargs, f'{lookup_field} 不存在于 {self.__class__.__name__} 的 Url配置中的关键词内 '

        filter_kwargs = {lookup_field: self.kwargs[lookup_field]}
        try:
            obj = await queryset.get_or_none(**filter_kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise APIException(f'{",".join(e.args)}.', status=HttpStatus.HTTP_502_BAD_GATEWAY)
        if obj is None:
            raise APIException(
                f'No data found with {lookup_field} -> {self.kwargs[lookup_field]}', status=HttpStatus.HTTP_200_OK)

        # May raise a permission denied
        await self.check_object_permissions(self.request, obj)

        return obj

    async def get_queryset(self):
        assert self.queryset is not None, (
            "'%s'应该包含一个'queryset'属性，"
            "或重写`get_queryset()`方法。"
            % self.__class__.__name__
        )
        queryset = self.queryset
        filter_orm = await self.filter_orm()
        queryset = queryset.filter(filter_orm)
        return queryset

    async def filter_orm(self):
        """得到ORM过滤参数"""
        return self.filter_class(self.request, self).orm_filter

    async def get_serializer(self, *args, **kwargs):
        """
        返回应该用于验证和验证的序列化程序实例
        对输入进行反序列化，并对输出进行序列化。
        """
        serializer_class = await self.get_serializer_class()
        kwargs.setdefault('context', await self.get_serializer_context())
        return serializer_class(*args, **kwargs)

    async def get_serializer_class(self):
        """
        返回用于序列化器的类。
        默认使用`self.serializer_class`。

        如果您需要提供其他信息，则可能要覆盖此设置
        序列化取决于传入的请求。

        （例如，管理员获得完整的序列化，其他获得基本的序列化）
        """
        assert self.serializer_class is not None, (
            "'%s' should either include a `serializer_class` attribute, "
            "or override the `get_serializer_class()` method."
            % self.__class__.__name__
        )
        return self.serializer_class

    async def get_serializer_context(self):
        """
        提供给序列化程序类的额外上下文。
        """
        return {
            'request': self.request,
            'view': self
        }

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        if not hasattr(self, '_paginator'):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    async def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        if self.paginator is None:
            return None
        return await self.paginator.paginate_queryset(queryset, self.request, view=self)

    async def get_paginated_response(self, data):
        assert self.paginator is not None
        return await self.paginator.get_paginated_response(data)


class CreateAPIView(mixins.CreateModelMixin,
                    GenericAPIView):
    """
    用于创建模型实例的具体视图。
    """

    async def post(self, request, *args, **kwargs):
        return await self.create(request, *args, **kwargs)


class ListAPIView(mixins.ListModelMixin,
                  GenericAPIView):
    """
    列出查询集的具体视图。
    """

    async def get(self, request, *args, **kwargs):
        return await self.list(request, *args, **kwargs)


class RetrieveAPIView(mixins.RetrieveModelMixin,
                      GenericAPIView):
    """
    用于检索模型实例的具体视图。
    """

    async def get(self, request, *args, **kwargs):
        return await self.retrieve(request, *args, **kwargs)


class DestroyAPIView(mixins.DestroyModelMixin,
                     GenericAPIView):
    """
    用于删除模型实例的具体视图。
    """

    async def delete(self, request, *args, **kwargs):
        return await self.destroy(request, *args, **kwargs)


class UpdateAPIView(mixins.UpdateModelMixin,
                    GenericAPIView):
    """
    用于更新模型实例的具体视图。
    """

    async def put(self, request, *args, **kwargs):
        return await self.update(request, *args, **kwargs)

    async def patch(self, request, *args, **kwargs):
        return await self.partial_update(request, *args, **kwargs)


class ListCreateAPIView(mixins.ListModelMixin,
                        mixins.CreateModelMixin,
                        GenericAPIView):
    """
    用于列出查询集或创建模型实例的具体视图。
    """

    async def get(self, request, *args, **kwargs):
        return await self.list(request, *args, **kwargs)

    async def post(self, request, *args, **kwargs):
        return await self.create(request, *args, **kwargs)


class RetrieveUpdateAPIView(mixins.RetrieveModelMixin,
                            mixins.UpdateModelMixin,
                            GenericAPIView):
    """
    用于检索、更新模型实例的具体视图。
    """

    async def get(self, request, *args, **kwargs):
        return await self.retrieve(request, *args, **kwargs)

    async def put(self, request, *args, **kwargs):
        return await self.update(request, *args, **kwargs)

    async def patch(self, request, *args, **kwargs):
        return await self.partial_update(request, *args, **kwargs)


class RetrieveDestroyAPIView(mixins.RetrieveModelMixin,
                             mixins.DestroyModelMixin,
                             GenericAPIView):
    """
    用于检索或删除模型实例的具体视图。
    """

    async def get(self, request, *args, **kwargs):
        return await self.retrieve(request, *args, **kwargs)

    async def delete(self, request, *args, **kwargs):
        return await self.destroy(request, *args, **kwargs)


class RetrieveUpdateDestroyAPIView(mixins.RetrieveModelMixin,
                                   mixins.UpdateModelMixin,
                                   mixins.DestroyModelMixin,
                                   GenericAPIView):
    """
    用于检索、更新或删除模型实例的具体视图。
    """

    async def get(self, request, *args, **kwargs):
        return await self.retrieve(request, *args, **kwargs)

    async def put(self, request, *args, **kwargs):
        return await self.update(request, *args, **kwargs)

    async def patch(self, request, *args, **kwargs):
        return await self.partial_update(request, *args, **kwargs)

    async def delete(self, request, *args, **kwargs):
        return await self.destroy(request, *args, **kwargs)


class TreeAPIView(mixins.TreeModelMixin,
                  GenericAPIView):
    """
    用于列出查询集或创建模型实例的具体视图。
    """

    async def get(self, request, *args, **kwargs):
        return await self.tree(request, *args, **kwargs)
