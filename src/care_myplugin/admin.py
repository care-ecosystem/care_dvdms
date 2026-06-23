from django.contrib import admin

from care_myplugin.models.note import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "facility", "created_by", "created_date")
    list_filter = ("facility",)
    search_fields = ("title", "content")
    readonly_fields = ("external_id", "created_date", "modified_date", "created_by", "updated_by")
