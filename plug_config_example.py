# Copy this snippet into care's plug_config.py to register your plugin.
# TODO: Replace care_dvdms with your plugin name.

from plugs.plug import Plug

care_dvdms_plugin = Plug(
    name="care_dvdms",
    package_name="/app/care_dvdms",       # local dev path; use git+https://... in production
    version="",                               # keep empty for local dev; "@main" for production
    configs={
        "DVDMS_API_ENDPOINT": "https://api.example.com",
        "DVDMS_AUTH_TOKEN": "your-auth-token",
    },
)

# In plug_config.py, add to plugs list:
# plugs = [
#     care_dvdms_plugin,
# ]
