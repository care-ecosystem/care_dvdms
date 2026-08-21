from django.db import migrations

SEQUENCE_NAME = "care_dvdms_dvdmsrecordorder_care_indent_no_seq"


class Migration(migrations.Migration):

    dependencies = [
        ('care_dvdms', '0002_dvdmsrecordorder_care_indent_no'),
    ]

    operations = [
        migrations.RunSQL(
            sql=f"CREATE SEQUENCE IF NOT EXISTS {SEQUENCE_NAME};",
            reverse_sql=f"DROP SEQUENCE IF EXISTS {SEQUENCE_NAME};",
        ),
    ]
