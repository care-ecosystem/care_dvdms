import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("care_dvdms", "0007_dvdmsprescriptionsequence"),
        ("emr", "0080_alter_activitydefinition_category_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dvdmsrecorditemdelivery",
            name="supply_delivery",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="dvdms_record_item_delivery",
                to="emr.supplydelivery",
            ),
        ),
    ]
