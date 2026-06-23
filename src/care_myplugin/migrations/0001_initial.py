import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("facility", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Note",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("external_id", models.UUIDField(db_index=True, default=uuid.uuid4, unique=True)),
                ("created_date", models.DateTimeField(auto_now_add=True, null=True)),
                ("modified_date", models.DateTimeField(auto_now=True, null=True)),
                ("deleted", models.BooleanField(default=False)),
                ("history", models.JSONField(default=dict)),
                ("meta", models.JSONField(default=dict)),
                ("title", models.CharField(max_length=255)),
                ("content", models.TextField(blank=True, default="")),
                (
                    "facility",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="myplugin_notes",
                        to="facility.facility",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="care_myplugin_note_created_by",
                        to="users.user",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="care_myplugin_note_updated_by",
                        to="users.user",
                    ),
                ),
            ],
            options={"abstract": False},
        ),
    ]
