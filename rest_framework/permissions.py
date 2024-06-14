"""
@Author:TioitWang
@E-mile:me@tioit.cc
@CreateTime:2021/4/25 16:51
@DependencyLibrary:无
@MainFunction:无
@FileDoc:
    permissions.py
    文件说明
@ChangeHistory:
    datetime action why
    example:
    2021/4/25 16:51 change 'Fix bug'
"""

from tortoise import fields

from rest_framework.constant import ALL_METHOD, BoolEnum
from rest_framework.exceptions import APIException, PermissionDenied


class BasePermission:
    async def has_permission(self, request, view):
        pass

    async def has_object_permission(self, request, view, obj):
        pass


class UserModelMixin:
    async def has_permissions(self, codes):
        raise NotImplementedError()

    is_superuser = fields.IntEnumField(
        BoolEnum, default=BoolEnum.FALSE, description="是否为超级用户"
    )


class CodePermission(BasePermission):
    async def has_permission(self, request, view):
        permission_code = getattr(view, "permission_code", None)
        if permission_code is None:
            return False

        if not await request.user.has_permissions([permission_code]):
            raise PermissionDenied()
        return True


class ViewMapPermission(BasePermission):
    """
    APIView permission_classes

    example
        class ViewName(APIView):
            permission_classes = (ViewMapPermission)
            permission_map = {
                'get':['can_view']
                'post':['can_create']
                ....
                'all':['need_perm']
            }

    Note, request.user must need `has_permissions(codes)` method
    """

    def get_permission_map(self, view):
        permission_map = self.permission_map
        if hasattr(view, "permission_map"):
            permission_map.update(view.permission_map)
        return permission_map

    async def has_permission(self, request, view):
        permission_map = self.get_permission_map(view)
        all_permissions = permission_map.get("all")
        method = request.method.lower()
        method_permission = permission_map.get(method)
        permissions = (*method_permission, *all_permissions)
        if not request.user.has_permissions(permissions):
            raise PermissionDenied()

    async def has_object_permission(self, request, view, obj):
        pass

    @property
    def permission_map(self):
        permission_map = {method.lower(): () for method in ALL_METHOD}
        permission_map["all"] = ()
        return permission_map


def verify_prem(permissions: list, exception: APIException = None):
    """
    verify user has permissions
    @param permissions: list
    @param exception:
    @return:
    """
    if exception is None:
        exception = PermissionDenied()

    def set_fun(func):
        async def call_fun(view, request, *args, **kwargs):
            if not await request.user.has_permissions(permissions):
                raise exception
            return await func(view, request, *args, **kwargs)

        return call_fun

    return set_fun
