"""
@Author:TioitWang
@E-mile:me@tioit.cc
@CreateTime:2021/3/26 14:43
@DependencyLibrary:无
@MainFunction:无
@FileDoc:
    mixins.py
    文件说明
@ChangeHistory:
    datetime action why
    example:
    2021/3/26 14:43 change 'Fix bug'
"""

from typing import List
from rest_framework.exceptions import APIException
from rest_framework.paginations import ORMPageNumberPagination

__all__ = ("ListModelMixin", "CreateModelMixin", "RetrieveModelMixin", "UpdateModelMixin", "DestroyModelMixin")


class TreeModelMixin:
    parent_field = "parent_id"
    children_field = "children"
    lookup_field = "id"
    order_field = "order"
    order_reverse = False

    async def get(self, request, *args, **kwargs):
        return await self.tree(request, *args, **kwargs)

    async def tree(self, request, *args, **kwargs):
        queryset = await self.get_queryset()
        serializer = await self.get_serializer(queryset, many=True)
        data_list = await serializer.data
        return self.success_json_response(data=await self.build_tree_structure(data_list))

    async def build_tree_structure(self, data_list: List[dict]):
        # Create a dictionary to store references with id as key and item as value
        item_dict = {item[self.lookup_field]: item for item in data_list}
        for item in item_dict.values():
            item[self.children_field] = []  # Initialize child node list

        # Initialize root node list
        tree_root = []

        for item in data_list:
            parent_id = item.get(self.parent_field)
            # If there is a valid parent node, add the current item to the parent's children
            if parent_id and parent_id in item_dict:
                parent_item = item_dict[parent_id]
                parent_item[self.children_field].append(item)
            else:
                tree_root.append(item)

        if self.order_field:
            # If an order field is specified, sort the children of each node
            for item in item_dict.values():
                item[self.children_field] = sorted(
                    item[self.children_field], key=lambda x: x[self.order_field], reverse=self.order_reverse
                )

        return tree_root


class ListModelMixin:
    """
    List a queryset.
    """
    pagination_class = ORMPageNumberPagination
    detail = False

    async def get(self, request, *args, **kwargs):
        return await self.list(request, *args, **kwargs)

    async def list(self, request, *args, **kwargs):
        queryset = await self.get_queryset()

        page = await self.paginate_queryset(queryset)
        if page is not None:
            serializer = await self.get_serializer(page, many=True)
            return await self.get_paginated_response(await serializer.data)

        serializer = await self.get_serializer(queryset, many=True)
        return self.success_json_response(data=await serializer.data)


class CreateModelMixin:
    """
    Create a model instance.
    """
    unique_field = ()
    unique_error_msg = "The value {rt_msg} already exists."

    async def post(self, request, *args, **kwargs):
        return await self.create(request, *args, **kwargs)

    async def create(self, request, *args, **kwargs):
        serializer = await self.get_serializer(data=request.data)
        await serializer.is_valid(raise_exception=True)
        await self.is_unique(serializer.validated_data)
        await self.perform_create(serializer)
        return self.success_json_response(data=await serializer.data)

    async def is_unique(self, data, update_obj=None):
        if not isinstance(self.unique_field, (list, tuple)) or not self.unique_field:
            return None

        kws = {}
        rt_msg = ""
        for field in self.unique_field:
            if isinstance(field, (list, tuple)):
                for i in field:
                    kws[i] = data[i]
                    rt_msg += f" {i}:{data[i]} "
            else:
                kws[field] = data[field]
                rt_msg += f" {field}:{data[field]}"

        checked = False
        if update_obj:
            for key, value in kws.items():
                if value != getattr(update_obj, key):
                    checked = True

        if checked or update_obj is None:
            condition = await self.queryset.filter(**kws).exists()
            if condition:
                raise APIException(self.unique_error_msg.format(rt_msg=rt_msg))
        return None

    async def perform_create(self, serializer):
        return await serializer.save()


class RetrieveModelMixin:
    detail = True

    async def get(self, request, *args, **kwargs):
        return await self.retrieve(request, *args, **kwargs)

    async def retrieve(self, request, *args, **kwargs):
        instance = await self.get_object()
        serializer = await self.get_serializer(instance)
        return self.success_json_response(data=await serializer.data)


class UpdateModelMixin:
    async def put(self, request, *args, **kwargs):
        return await self.update(request, *args, **kwargs)

    async def patch(self, request, *args, **kwargs):
        return await self.partial_update(request, *args, **kwargs)

    async def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = await self.get_object()
        serializer = await self.get_serializer(instance, data=request.data, partial=partial)
        await serializer.is_valid(raise_exception=True)
        if hasattr(self, "unique_field") and hasattr(self, "is_unique"):
            await self.is_unique(serializer.validated_data, instance)
        await self.perform_update(serializer)
        return self.success_json_response(data=await serializer.data)

    async def perform_update(self, serializer):
        return await serializer.save()

    async def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return await self.update(request, *args, **kwargs)


class DestroyModelMixin:
    async def delete(self, request, *args, **kwargs):
        return await self.destroy(request, *args, **kwargs)

    async def destroy(self, request, *args, **kwargs):
        instance = await self.get_object()
        serializer = await self.get_serializer(instance)
        data = await serializer.data
        await self.perform_destroy(instance)
        return self.success_json_response(data=data)

    async def perform_destroy(self, instance):
        await instance.delete()
