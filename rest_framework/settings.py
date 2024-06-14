"""
@Author: TioitWang
@E-mile: me@tioit.cc
@CreateTime: 2022/7/4 16:58
@DependencyLibrary: [...]
@MainFunction: None
@FileDoc:
    settings is python file
@ChangeHistory:
    datetime action why
    2022/7/4 16:58 [Create] settings.py
"""
import importlib

from sanic import Sanic

from rest_framework.utils import ObjectDict


def update_dict(target, change):
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


# 从模块中导入一个对象
def import_string(dotted_path):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.
    """
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % dotted_path) from err

    module = importlib.import_module(module_path)
    try:
        return getattr(module, class_name)
    except AttributeError as err:
        raise ImportError('Module "%s" does not define a "%s" attribute/class' % (module_path, class_name)) from err


def perform_import(val, setting_name):
    """
    If the given setting is a string import notation,
    then perform the necessary import or imports.
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
    """
    try:
        return import_string(val)
    except ImportError as e:
        msg = "Could not import '%s' for API setting '%s'. %s: %s." % (val, setting_name, e.__class__.__name__, e)
        raise ImportError(msg)


DEFAULT_SETTINGS = {
    'SANIC_NAME': 'SRF',
    'DEFAULT_AUTHENTICATION_CLASSES': (),
    'DEFAULT_PERMISSION_CLASSES': (),
    'VIEW_TRANSACTION': False,
    'OPENAPI_CONFIG': {
        'title': 'SRF REST framework',
        'servers': [],
        'openapi_json_url': '/openapi.json',
        'openapi_ui_url': '/openapi',
    },

    # 请严格按照以下顺序进行配置
    'THROTTLE_DB_CONFIG': {
        'redis_db': {},
    },
    'DEFAULT_THROTTLE_CLASSES': (),
    'DEFAULT_THROTTLE_RATES': ('15/min', '100/hour'),
}

IMPORT_STRINGS = (
    'DEFAULT_AUTHENTICATION_CLASSES',
    'DEFAULT_PERMISSION_CLASSES',
    'DEFAULT_THROTTLE_CLASSES',
)


# 在此 init settings 之前，引入View模型会导致循环引用，后续需要解决此问题
class Settings:
    def __init__(self, defaults=None, import_strings=None):
        self.defaults = defaults or {}
        self.import_strings = import_strings or ()
        self.user_settings = {}

    def init(self, app: Sanic):
        self.user_settings = app.config.get('SRF_CONFIGS', {})

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError("Invalid API setting: '%s'" % attr)

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
