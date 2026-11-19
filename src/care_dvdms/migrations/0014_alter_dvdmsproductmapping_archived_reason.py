from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('care_dvdms', '0013_remove_dvdmsrecordorder_uniq_order_active_record_order_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dvdmsproductmapping',
            name='archived_reason',
            field=models.CharField(blank=True, choices=[('PRODUCT_ARCHIVED', 'Product Archived'), ('DVDMS_CONFIG_CHANGED', 'Dvdms Config Changed')], max_length=50, null=True),
        ),
    ]
