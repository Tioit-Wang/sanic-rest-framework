import logging
from importlib import import_module
from typing import Dict, List, Optional

from sanic.log import logger

from .app_config import AppConfig
from rest_framework.settings import srf_settings

log = logging.getLogger(__name__)


ALL_METHOD = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}


def path(
    uri: str, handler, name: str, upgrade: bool = False, version: Optional[str] = None, version_prefix: Optional[str] = None
) -> dict:
    """
    Returns a dictionary representing a route path.

    Args:
        uri (str): The URI of the route.
        handler: The handler function for the route.
        name (str): The name of the route.
        upgrade (bool, optional): Whether to upgrade the route. Defaults to False.
        version (str, optional): The version of the route. Defaults to None.
        version_prefix (str, optional): The version prefix of the route. Defaults to None.

    Returns:
        dict: A dictionary containing the route information.
    """
    return {"handler": handler, "uri": uri, "name": name, "upgrade": upgrade, "version": version, "version_prefix": version_prefix}


class AppStructureError(Exception):
    """Exception raised for errors in the application structure."""

    pass


class ProjectStructureHelper:
    """
    An app loader, easy to load and manage apps.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._sanic_app = None
            self.modules = {}
            self.orm_models = {}
            self.routers = []
            self._initialized = True

    def to_models_config(self) -> dict:
        """
        Returns the models configuration for the ORM.

        Returns:
            dict: The models configuration.
        """
        return {
            "connections": {"default": srf_settings.DB_CONNECT_STR},
            "apps": {
                "models": {
                    "models": ["aerich.models", *[self.orm_models[key] for key in self.orm_models.keys()]],
                    "default_connection": "default",
                },
            },
            "timezone": srf_settings.TIME_ZONE,
        }

    def register(self, app) -> None:
        """
        Registers the app and loads its modules and routes.

        Args:
            app: The Sanic app instance.
        """
        self._sanic_app = app
        self.load_app_modules()
        self.load_middleware()

    def set_route(self, endpoint, route: Dict) -> None:
        """
        Provides default parameters for methods in URLs.

        Args:
            endpoint: The endpoint object (app instance or blueprint instance).
            route (Dict): The route configuration.
        """
        if 'methods' not in route:
            route['methods'] = ALL_METHOD
        endpoint.add_route(**route)

    def load_route(self, app, bp, routes: List[Dict]) -> None:
        """
        Adds routes to the specified endpoint in a loop.

        Args:
            app: The app instance.
            bp: The blueprint instance.
            routes (List[Dict]): The list of routes.
        """
        for route in routes:
            upgrade = route.pop('upgrade', False)
            self.set_route(app if upgrade else bp, route)

    def load_app_modules(self):
        logger.info("Start loading app.")
        for module_path in srf_settings.APP_MODULES:
            app_module = import_module(module_path)
            app_config_instance = None
            for name, app_config in app_module.__dict__.items():
                if '__' in name:
                    continue
                if isinstance(app_config, type) and issubclass(app_config, AppConfig) and app_config is not AppConfig:
                    app_config_instance = app_config()
                    break
            if app_config_instance is None:
                raise AppStructureError(f"{module_path} No App Config Found")

            self.orm_models[app_config_instance.app_name] = app_config_instance.models
            self.routers.extend(app_config_instance.urls)
            self.load_route(self._sanic_app, app_config_instance.bp, app_config_instance.urls)
            self._sanic_app.blueprint(app_config_instance.bp)
            logger.info(f"{app_config_instance.app_name} App Config Loaded √")

        logger.info(f"{len(srf_settings.APP_MODULES)} applications have been loaded")

    def load_middleware(self):
        for middleware in srf_settings.MIDDLEWARE:
            middleware(self._sanic_app)


project_helper = ProjectStructureHelper()
