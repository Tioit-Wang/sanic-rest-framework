from rest_framework import mixins
from rest_framework.generics import GenericAPIView

__all__ = ('GenericViewSet', 'ModelViewSet')


class GenericViewSet(GenericAPIView):
    """
    The GenericViewSet class does not provide any actions by default,
    but does contain a basic set of generic view behaviors,
    Examples are the 'get_object()' and 'get_queryset()' methods.
    """


class ModelViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin,
                   mixins.ListModelMixin,
                   GenericViewSet):
    """
    `create()`, `retrieve()`, `update()`, `partial_update()`, `destroy()`, `list()` actions.
    """
    hidden_actions = []
    # hidden_actions = ['create', 'list', 'retrieve', 'patch', 'delete', 'put']
    pass
