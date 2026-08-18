from care_dvdms.models.dvdms_sync_log import (
    DVDMSSyncLog,
    DVDMSSyncRequestStatus,
    DVDMSSyncTriggeredBy,
    DVDMSSyncType,
)


def track_indent(institute, outward_record, user):
    """
    Fetch the latest indent/issue status from DVDMS for an outward record.

    ponytail: DVDMS TRACK_INDENT endpoint contract (path/payload) isn't finalized
    yet. Wire the real dvdms_client call here once available; for now this only
    records the sync attempt so the outward/sync_log plumbing is in place.
    """
    sync_log = DVDMSSyncLog.objects.create(
        institute=institute,
        triggered_by=DVDMSSyncTriggeredBy.user,
        sync_type=DVDMSSyncType.track_indent,
        request_status=DVDMSSyncRequestStatus.pending,
        request_payload={"eaushadhi_indent_no": outward_record.eaushadhi_indent_no},
        created_by=user,
        updated_by=user,
    )

    outward_record.sync_log = sync_log
    outward_record.updated_by = user
    outward_record.save()

    return outward_record
