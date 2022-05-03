from srf import mixins
from srf.constant import DEFAULT_METHOD_MAP
from srf.generics import GenericAPIView
from srf.views import APIView

__all__ = ('ViewSetMixin', 'ViewSet', 'GenericViewSet', 'ModelViewSet')


class ViewSetMixin:

    @classmethod
    def as_view(cls, method_map=DEFAULT_METHOD_MAP, *class_args, **class_kwargs):

        # 返回的响应方法闭包
        def view(request, *args, **kwargs):
            # sourcery skip: use-named-expression
            self = view.base_class(*class_args, **class_kwargs)
            view_method_map = {}
            for method, action in method_map.items():
                handler = getattr(self, action, None)
                if handler:
                    setattr(self, method, handler)
                    view_method_map[method] = action

            self.method_map = view_method_map
            self.methods = list(view_method_map.keys())
            self.request = request
            self.args = args
            self.kwargs = kwargs
            self.app = request.app
            return self.dispatch(request, *args, **kwargs)

        view.funcs = cls._effective_funcs(method_map)
        view.methods = cls._effective_method(method_map)
        view.base_class = cls
        view.view_obj = cls(*class_args, **class_kwargs)
        view.methods = list(method_map.keys())
        view.API_DOC_CONFIG = class_kwargs.get('API_DOC_CONFIG')  # 未来的API文档配置属性+
        view.__doc__ = cls.__doc__
        view.__module__ = cls.__module__
        view.__name__ = cls.__name__
        return view

    @classmethod
    def _effective_funcs(cls, method_map):
        # sourcery skip: use-named-expression
        funcs = {}
        for method, action in method_map.items():
            handler = getattr(cls, action, None)
            if handler:
                funcs[method] = handler
        return funcs

    @classmethod
    def _effective_method(cls, method_map):
        # sourcery skip: use-named-expression
        methods = []
        for method, action in method_map.items():
            handler = getattr(cls, action, None)
            if handler:
                methods.append(method)
        return methods


class ViewSet(ViewSetMixin, APIView):
    """
    By default, the basic ViewSet class does not provide any operations.
    """
    pass


class GenericViewSet(ViewSetMixin, GenericAPIView):
    """
    The GenericViewSet class does not provide any actions by default,
    but does contain a basic set of generic view behaviors,
    Examples are the 'get_object()' and 'get_queryset()' methods.
    """
    pass


class ModelViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin,
                   mixins.ListModelMixin,
                   GenericViewSet):
    """
    `create()`, `retrieve()`, `update()`, `partial_update()`, `destroy()`, `list()` actions.
    """
    pass
