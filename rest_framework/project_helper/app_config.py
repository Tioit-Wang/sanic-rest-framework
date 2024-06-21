from importlib import import_module
from sanic.blueprints import Blueprint


class AppConfig:
    app_name = None
    base_url = None
    router_module = 'urls'
    model_module = 'models'

    def __init__(self, **kwargs):
        self.app_name = kwargs.get('app_name', self.app_name)
        if self.app_name is None:
            raise ValueError('app_name is required')

        self.base_url = kwargs.get('base_url', f'/{self.app_name}')
        self.router_module = kwargs.get('router_module', self.router_module)
        self.model_module = kwargs.get('model_module', self.model_module)

        self.bp = Blueprint(self.app_name, self.base_url)
        self.urls = getattr(import_module(f'{self.__module__}.{self.router_module}'), 'urls')
        self.models = f'{self.__module__}.{self.model_module}'
