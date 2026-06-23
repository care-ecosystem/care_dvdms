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
Search and replace `care_myplugin` → `care_yourplugin` across all files.

### 3. Register with CARE
Copy `plug_config_example.py` snippet into `care/plug_config.py`.

### 4. Run migrations
```bash
python manage.py makemigrations care_myplugin
python manage.py migrate
```

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

Once registered, your plugin's URLs are mounted at `/api/care_myplugin/`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/care_myplugin/notes/` | List notes (requires `facility_id`) |
| POST | `/api/care_myplugin/notes/` | Create a note |
| GET | `/api/care_myplugin/notes/{id}/` | Retrieve a note |
| PATCH | `/api/care_myplugin/notes/{id}/` | Update a note |

## GitHub Actions

`trigger-care-build.yml` dispatches a build event to the CARE backend repo on every push to `main`.
Set the `CARE_REPO_DISPATCH_TOKEN` secret in your repo settings.
