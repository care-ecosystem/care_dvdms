from typing import Any

import environ
from django.conf import settings
from django.core.signals import setting_changed
from django.dispatch import receiver
from rest_framework.settings import perform_import

from care_dvdms.apps import PLUGIN_NAME

env = environ.Env()


class PluginSettings:
    """
    Access plugin settings as properties. Reads from PLUGIN_CONFIGS[plugin_name]
    in Django settings, then falls back to environment variables, then defaults.

    Usage:
        from care_dvdms.settings import plugin_settings
        api_key = plugin_settings.CARE_DVDMS_API_KEY
    """

    def __init__(
        self,
        plugin_name: str = None,
        defaults: dict | None = None,
        import_strings: set | None = None,
        required_settings: set | None = None,
    ) -> None:
        if not plugin_name:
            raise ValueError("Plugin name must be provided")
        self.plugin_name = plugin_name
        self.defaults = defaults or {}
        self.import_strings = import_strings or set()
        self.required_settings = required_settings or set()
        self._cached_attrs = set()
        self.validate()

    def __getattr__(self, attr) -> Any:
        if attr not in self.defaults:
            raise AttributeError("Invalid setting: '%s'" % attr)

        val = self.defaults[attr]
        try:
            val = self.user_settings[attr]
        except KeyError:
            try:
                val = env(attr, cast=type(val))
            except environ.ImproperlyConfigured:
                pass

        if attr in self.import_strings:
            val = perform_import(val, attr)

        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    @property
    def user_settings(self) -> dict:
        if not hasattr(self, "_user_settings"):
            self._user_settings = getattr(settings, "PLUGIN_CONFIGS", {}).get(
                self.plugin_name, {}
            )
        return self._user_settings

    def validate(self) -> None:
        for setting in self.required_settings:
            if not getattr(self, setting, None):
                raise ValueError(f"Required plugin setting '{setting}' is missing or empty.")

    def reload(self) -> None:
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        if hasattr(self, "_user_settings"):
            delattr(self, "_user_settings")


@receiver(setting_changed)
def _reload_plugin_settings(*, setting, **kwargs):
    if setting == "PLUGIN_CONFIGS":
        plugin_settings.reload()


REQUIRED_SETTINGS: set[str] = {
    "DVDMS_API_ENDPOINT",
    "DVDMS_AUTH_TOKEN",
}

DEFAULTS: dict[str, Any] = {
    "DVDMS_API_ENDPOINT": "",
    "DVDMS_AUTH_TOKEN": "",
    "DVDMS_AUTH_TOKEN_TYPE": "Basic",
    "DVDMS_API_CONNECT_TIMEOUT": 10,
    "DVDMS_API_READ_TIMEOUT": 30,
    "DVDMS_LOOKUP_CACHE_TTL": 86400,
    "DVDMS_API_RETRY_COUNT": 3,
}

plugin_settings = PluginSettings(
    plugin_name=PLUGIN_NAME,
    defaults=DEFAULTS,
    required_settings=REQUIRED_SETTINGS,
)
