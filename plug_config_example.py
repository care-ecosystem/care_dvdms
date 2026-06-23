# Copy this snippet into care's plug_config.py to register your plugin.
# TODO: Replace care_myplugin with your plugin name.

from plugs.plug import Plug

care_myplugin_plugin = Plug(
    name="care_myplugin",                    # TODO: rename
    package_name="/app/care_myplugin",       # local dev path; use git+https://... in production
    version="",                               # keep empty for local dev; "@main" for production
    configs={
        # TODO: add your plugin settings here
        # "MYPLUGIN_API_KEY": "your-api-key",
        # "MYPLUGIN_API_ENDPOINT": "https://api.example.com",
    },
)

# In plug_config.py, add to plugs list:
# plugs = [
#     care_myplugin_plugin,
# ]
