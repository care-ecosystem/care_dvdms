# Care Plugin Template

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/care-ecosystem/care_plugin_template)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-4.2%2B-green.svg)](https://www.djangoproject.com/)
[![eGov Foundation](https://img.shields.io/badge/eGov-Foundation-orange.svg)](https://egov.org.in)

A starter template for building CARE backend plugins following the `EMRBaseViewSet` + `EMRResource` pattern.

**Developed by**: [eGov Foundation](https://egov.org.in)

## Quick Links

- 🖥️ **Frontend Template**: [care_fe_plugin_template](https://github.com/care-ecosystem/care_fe_plugin_template)
- 📖 **CARE Platform**: [ohcnetwork/care](https://github.com/ohcnetwork/care)
- 🐛 **Report Issues**: [GitHub Issues](https://github.com/care-ecosystem/care_plugin_template/issues)
- 🏢 **eGov Foundation**: [egov.org.in](https://egov.org.in)
- 📧 **Contact**: [jagan.kumar@egovernments.org](mailto:jagan.kumar@egovernments.org)

## Getting Started

### 1. Use this template
Click **Use this template** on GitHub to create your repo.

### 2. Rename the plugin
Search and replace `care_dvdms` → `care_yourplugin` across all files.

### 3. Register with CARE
Copy `plug_config_example.py` snippet into `care/plug_config.py`.

### 4. Run migrations
```bash
python manage.py makemigrations care_dvdms
python manage.py migrate
```

## Configuration Variables

Set via `PLUGIN_CONFIGS["care_dvdms"]` in CARE settings (see `plug_config_example.py`), or as environment variables.

### Mandatory

| Variable | Type | Description |
|----------|------|-------------|
| `DVDMS_API_ENDPOINT` | string | Base URL of the DVDMS / e-Aushadhi API |
| `DVDMS_AUTH_TOKEN` | string | Token used in the `Authorization` header |

### Optional

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DVDMS_AUTH_TOKEN_TYPE` | string | `Basic` | Auth scheme prefix for the `Authorization` header |
| `DVDMS_API_CONNECT_TIMEOUT` | int | `10` | Connection timeout (seconds) for DVDMS API calls |
| `DVDMS_API_READ_TIMEOUT` | int | `30` | Read timeout (seconds) for DVDMS API calls |
| `DVDMS_API_RETRY_COUNT` | int | `3` | Max retries for DVDMS sync tasks |
| `DVDMS_LOOKUP_CACHE_TTL` | int | `86400` | Cache TTL (seconds) for master-data lookups |
| `DVDMS_LOOKUP_FILTER_BY_HOSPITAL_CODE` | bool | `True` | Filter lookup master data by hospital code |
| `DVDMS_LOOKUP_FILTER_BY_SEAT_ID` | bool | `True` | Filter lookup master data by seat ID |

### GitHub Actions Secrets

| Variable | Required | Description |
|----------|----------|-------------|
| `CARE_REPO_DISPATCH_TOKEN` | Yes | Token used to dispatch a build event to the CARE backend repo |

## Architecture

This template demonstrates the full plugin pattern:

| Layer | Class | File |
|-------|-------|------|
| Model | `EMRBaseModel` | `models/note.py` |
| Read Spec | `EMRResource` | `api/specs/note.py` |
| Create Spec | `EMRResource` | `api/specs/note.py` |
| Update Spec | `EMRResource` | `api/specs/note.py` |
| ViewSet | `EMRBaseViewSet` + mixins | `api/viewsets/note.py` |
| Permissions | `PermissionController` | `security/permissions.py` |
| Authorization | `AuthorizationHandler` | `security/access.py` |

## API Endpoints

Once registered, your plugin's URLs are mounted at `/api/care_dvdms/`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/care_dvdms/notes/` | List notes (requires `facility_id`) |
| POST | `/api/care_dvdms/notes/` | Create a note |
| GET | `/api/care_dvdms/notes/{id}/` | Retrieve a note |
| PATCH | `/api/care_dvdms/notes/{id}/` | Update a note |

## GitHub Actions

`trigger-care-build.yml` dispatches a build event to the CARE backend repo on every push to `main`.
Set the `CARE_REPO_DISPATCH_TOKEN` secret in your repo settings.
