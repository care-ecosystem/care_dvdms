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

## Deliberate deviations
- (none recorded — note that the missing `Meta.ordering` and `Meta.indexes` on these models are
  known gaps, not decisions. Flagging them is correct.)
