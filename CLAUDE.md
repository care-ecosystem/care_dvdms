# care_dvdms

CARE backend plugin. PRs are reviewed by care_ci; the rules live in
`care-ecosystem/care_reviewer`. Keep this file under 60 lines — it is read on every review run.

## Identity
- `Plug(name=...)`: `care_dvdms` — also the API mount, `/api/care_dvdms/`
- Django app label (`PLUGIN_NAME`) is the same: `care_dvdms`
- Package layout: `src/care_dvdms/`

## Entry points
- `apps.py` `ready()` registers: `care_dvdms.signals`; `care_dvdms.tasks`;
  `CareDVDMSPermissions` via `PermissionController.register_permission_handler`; and
  `care_dvdms.security.access`. It then calls `plugin_settings.validate()`, skipped for
  `BUILD_TIME_COMMANDS`.
- `urls.py` exports `urlpatterns` as an explicit list, not a bare router — a new viewset must be
  added there by hand or it mounts nothing.
- Celery task functions in `tasks.py`: `save_indent_task`, `prefill_inward_record_task`,
  `save_acknowledgement_task` — all three cross into DVDMS.
- `signals.py` receives core `MedicationRequestPrescription`, `ProductKnowledge` and `RequestOrder`
  saves; those handlers run inside core's transaction, so no HTTP call belongs in them.

## Integrates with
- Core models extended via the `extensions` JSONField: none.
- **External system: DVDMS**, the state drug and vaccine distribution system. Orders,
  inward/outward records and deliveries written here cross a system boundary.

  This is the highest-risk area in the repo and the source of its known defect class: an order
  created in CARE and then abandoned when DVDMS rejects it is an orphan with no recovery path.
  Review every write path for: all prerequisites validated *before* the first write, the whole
  operation inside `transaction.atomic()`, an idempotency key on anything crossing into DVDMS,
  and complete consumption of paginated DVDMS responses rather than page one only.
- Frontend counterpart: `care_dvdms_fe`.

## Invariants — breaking one is a regression, not a style note
- **DVDMS rejects with HTTP 200** and a non-success body, so success is never `raise_for_status()`
  or a status code alone. Calls go through `api/services/dvdms_client.py`, never bare `requests`.
- **Response shape is pinned**: fields the code reads are `Used[...]` in `dvdms_response_schemas.py`
  and a change there blocks the call. Reading a new DVDMS field means declaring it there too.
- **Failures go through `utils/sync_errors.py`** (`record_sync_failure` + `store_record_error`),
  which write `response_payload` and the record's `meta.error`. Hand-rolled failure branches once
  lost DVDMS's own answer on all 17 recorded failures.
- **`autoretry_for` is only `ConnectTimeout`/`ReadTimeout`**, deliberately — widening it to
  `RequestException` retries a *rejected* payload and duplicates indents in DVDMS.
- **Institute config is locked, not just read**: writes using it call `lock_institute()` inside
  `transaction.atomic()`, and a `DVDMS_CONFIG_FIELDS` change mid-request is a 409, not a retry.
- **Inward item identity is the lot** — `(inward_record, drug_id, brand_id, batch, manufacturer)`.
  `(inward_record, record_order_item)` silently overwrote one issued lot with another; an ambiguous
  match must raise its named error, never merge.
- **Numbering comes from the sequence tables** (`DVDMSCareIndentSequence`,
  `DVDMSPrescriptionSequence`) via `ON CONFLICT ... DO UPDATE`, keyed by institute/facility and
  financial year. `max() + 1` or a Python-side counter collides under concurrency.

## Deliberate deviations and known gaps
- Deviations: none recorded. Everything below is a gap, not a decision — flagging it is correct.
- No tests anywhere in the repo, and no CI lint or test gate.
- `pyproject.toml` declares only `django`, `celery`, `djangorestframework`, all unbounded, while the
  code imports `requests`, `django-environ`, `pydantic`, `django-filter`, `drf-spectacular`; four
  template `TODO` markers remain.
- No model defines `Meta.ordering` or `Meta.indexes`.
