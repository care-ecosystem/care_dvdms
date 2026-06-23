# Celery tasks for background processing.
# This file is auto-imported in apps.py ready().

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


# TODO: add your Celery tasks here
# Example:
# @shared_task
# def process_note(note_id: int) -> None:
#     from care_myplugin.models.note import Note
#     try:
#         note = Note.objects.get(pk=note_id)
#         logger.info("Processing note: %s", note.title)
#     except Note.DoesNotExist:
#         logger.error("Note %d not found", note_id)
