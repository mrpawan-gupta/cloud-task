"""
Settings for cloud task are all namespace in the CLOUD_TASK setting.
For example your project's `settings.py` file might look like this:

CLOUD_TASK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.TemplateHTMLRenderer',
    ],
}

This module provides the `task_setting` object, that is used to access
CLOUD_TASK settings, checking for user settings first, then falling
back to the defaults.
"""
from django.conf import settings
from django.core.signals import setting_changed
from django.utils.module_loading import import_string

DEFAULTS = {
    'DEFAULT_CLIENT_CLASS': 'cloudtask.client.BaseTaskClient',
    'DEFAULT_AUTHENTICATION_CLASS ': 'cloudtask.client.BaseAuthenticationClass',

    'DEFAULT_QUOTE_ID': None,
    'DEFAULT_QUOTE_LOCATION': None,

    'DEFAULT_TASK_HANDLER_ROOT_URL': '',
    'DEFAULT_TASK_RATE_LIMIT':  10,
    'DEFAULT_TASK_RATE_INTERVAL':  1,

    'DEFAULT_TASK_EXECUTE_LOCALLY': False
}


# List of settings that may be in string import notation.
IMPORT_STRINGS = [
    'DEFAULT_RENDERER_CLASSES',
    'DEFAULT_PARSER_CLASSES',
]


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
        msg = "Could not import '%s' for Task setting '%s'. %s: %s." % (val, setting_name, e.__class__.__name__, e)
        raise ImportError(msg)


class TaskSettings:
    """
    A settings object that allows cloud task settings to be accessed as
    properties. For example:

        from cloudtask.settings import task_settings
        print(task_settings.DEFAULT_RENDERER_CLASSES)

    Any setting with string import paths will be automatically resolved
    and return the class, rather than the string literal.

    Note:
    This is an internal class that is only compatible with settings namespace
    under the Cloud task name. It is not intended to be used by 3rd-party
    apps, and test helpers like `override_settings` may not work as expected.
    """
    def __init__(self, defaults=None, import_strings=None):
        self._user_settings = {}
        self.defaults = defaults or DEFAULTS
        self.import_strings = import_strings or IMPORT_STRINGS
        self._cached_attrs = set()

    @property
    def user_settings(self):
        if not hasattr(self, '_user_settings'):
            self._user_settings = getattr(settings, 'REST_FRAMEWORK', {})
        return self._user_settings

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
        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    def reload(self):
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        if hasattr(self, '_user_settings'):
            delattr(self, '_user_settings')


task_settings = TaskSettings(defaults=DEFAULTS, import_strings=IMPORT_STRINGS)


def reload_task_settings(*args, **kwargs):
    setting = kwargs['setting']
    if setting == 'CLOUD_TASK':
        task_settings.reload()


setting_changed.connect(reload_task_settings)
