import importlib

from sanic import Sanic
from rest_framework.utils import ObjectDict


def update_dict(target, change):
    """
    Recursively updates a nested dictionary with changes from another dictionary.

    Args:
        target (dict): The original dictionary to be updated.
        change (dict): The dictionary containing changes to be applied.

    Returns:
        ObjectDict: A new dictionary with updates applied.
    """
    ret_data = ObjectDict({})
    for key, val in target.items():
        if key in change:
            if isinstance(val, dict):
                ret_data[key] = update_dict(val, change.get(key, {}))
            else:
                ret_data[key] = change[key]
        else:
            ret_data[key] = val
    return ret_data


def import_string(dotted_path):
    """
    Import a module using a dotted path and return the attribute/class designated
    by the last name in the path.

    Args:
        dotted_path (str): The dotted module path.

    Raises:
        ImportError: If the import fails or the attribute/class is not found.

    Returns:
        Any: The imported attribute/class.
    """
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
    except ValueError as err:
        raise ImportError(f"{dotted_path} doesn't look like a module path") from err

    module = importlib.import_module(module_path)
    try:
        return getattr(module, class_name)
    except AttributeError as err:
        raise ImportError(f'Module "{module_path}" does not define a "{class_name}" attribute/class') from err


def perform_import(val, setting_name):
    """
    Perform import for a given setting if it is a string import notation.

    Args:
        val (Any): The value to import.
        setting_name (str): The name of the setting.

    Returns:
        Any: The imported value or the original value if no import is needed.
    """
    if val is None:
        return None
    elif isinstance(val, str):
        return import_from_string(val, setting_name)
    elif isinstance(val, (list, tuple)):
        return [import_from_string(item, setting_name) for item in val]
    return val


def import_from_string(val, setting_name):
    """
    Attempt to import a class from a string representation.

    Args:
        val (str): The string representation of the class.
        setting_name (str): The name of the setting.

    Raises:
        ImportError: If the import fails.

    Returns:
        Any: The imported class.
    """
    try:
        return import_string(val)
    except ImportError as e:
        msg = f"Could not import '{val}' for API setting '{setting_name}'. {e.__class__.__name__}: {e}."
        raise ImportError(msg)


DEFAULT_SETTINGS = {
    'NAME': 'SRF',
    'VERSION': "1.0.0",
    "OPENAPI_TITLE": "SRF API",
    "OPENAPI_DESCRIPTION": "SRF API",
    "OPENAPI_TERMS_OF_SERVICE": None,
    "OPENAPI_CONTACT_NAME": None,
    "OPENAPI_CONTACT_EMAIL": None,
    "OPENAPI_CONTACT_URL": None,
    "OPENAPI_LICENSE_NAME": None,
    "OPENAPI_LICENSE_URL": None,
    "OPENAPI_SERVERS": [],
    'DEFAULT_AUTHENTICATION_CLASSES': (),
    'DEFAULT_PERMISSION_CLASSES': (),
    'VIEW_TRANSACTION': False,
    'APP_MODULES': [],
    'MIDDLEWARE': [],
    'DB_CONNECT_STR': '',
    'TIME_ZONE': "Asia/Shanghai",
    # cache
    "CACHES": {"default": {"BACKEND": 'rest_framework.cache.backends.locmem.LocMemCache', "OPTIONS": {"MAX_ENTRIES": 10000}}},
    "THROTTLE_CACHES_ENGINE_NAME": "default",  # 缓存
    'DEFAULT_THROTTLE_CLASSES': (),
    'DEFAULT_THROTTLE_RATES': ('15/min', '100/hour'),
}

IMPORT_STRINGS = ['DEFAULT_AUTHENTICATION_CLASSES', 'DEFAULT_PERMISSION_CLASSES', 'DEFAULT_THROTTLE_CLASSES', 'MIDDLEWARE']


class Settings:
    """
    Manages the API settings, allowing for default settings and user overrides.
    """

    def __init__(self, defaults=None, import_strings=None):
        self.defaults = defaults or {}
        self.import_strings = import_strings or []
        self.user_settings = {}

    def init(self, app: Sanic):
        """
        Initialize the settings with user-defined settings from the Sanic app configuration.

        Args:
            app (Sanic): The Sanic application instance.
        """
        self.user_settings = app.config.get('REST_FRAMEWORK_CONFIG', {})

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError(f"Invalid API setting: '{attr}'")

        try:
            # Check if present in user settings
            val = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            val = self.defaults[attr]

        # Coerce import strings into classes
        if attr in self.import_strings:
            val = perform_import(val, attr)

        # Cache the result
        setattr(self, attr, val)
        return val


srf_settings = Settings(DEFAULT_SETTINGS, IMPORT_STRINGS)
