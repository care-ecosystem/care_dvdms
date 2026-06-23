from django.db import models

from care.emr.models.base import EMRBaseModel
from care.facility.models import Facility


class Note(EMRBaseModel):
    """
    Example facility-scoped model. Replace with your domain model.
    Inherits: external_id, meta, history, created_by, updated_by,
              created_date, modified_date, deleted (soft delete).
    """

    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name="myplugin_notes",  # TODO: rename related_name
    )
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Note"
        verbose_name_plural = "Notes"
        # TODO: add UniqueConstraints here if needed
        # constraints = [
        #     models.UniqueConstraint(fields=["facility", "title"], name="uniq_facility_note_title"),
        # ]

    def __str__(self):
        return f"{self.facility} - {self.title}"
