from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('care_dvdms', '0014_alter_dvdmsproductmapping_archived_reason'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='dvdmsdrug',
            options={'ordering': ['id'], 'verbose_name_plural': 'DVDMS Drugs'},
        ),
        migrations.AlterModelOptions(
            name='dvdmsinstitute',
            options={'ordering': ['-created_date', '-id'], 'verbose_name_plural': 'DVDMS Institutes'},
        ),
        migrations.AlterModelOptions(
            name='dvdmsinwarditemrecord',
            options={'ordering': ['id'], 'verbose_name_plural': 'DVDMS Inward Item Records'},
        ),
        migrations.AlterModelOptions(
            name='dvdmsinwardrecord',
            options={'ordering': ['-created_date', '-id'], 'verbose_name_plural': 'DVDMS Inward Records'},
        ),
        migrations.AlterModelOptions(
            name='dvdmsoutwardrecordorder',
            options={'ordering': ['-created_date', '-id'], 'verbose_name_plural': 'DVDMS Outward Record Orders'},
        ),
        migrations.AlterModelOptions(
            name='dvdmsproductmapping',
            options={'ordering': ['-created_date', '-id'], 'verbose_name_plural': 'DVDMS Product Mappings'},
        ),
        migrations.AlterModelOptions(
            name='dvdmsrecorddelivery',
            options={'ordering': ['-created_date', '-id'], 'verbose_name_plural': 'DVDMS Record Deliveries'},
        ),
        migrations.AlterModelOptions(
            name='dvdmsrecorditemdelivery',
            options={'ordering': ['id'], 'verbose_name_plural': 'DVDMS Record Item Deliveries'},
        ),
        migrations.AlterModelOptions(
            name='dvdmsrecorditemorder',
            options={'ordering': ['id'], 'verbose_name_plural': 'DVDMS Record Item Orders'},
        ),
        migrations.AlterModelOptions(
            name='dvdmsrecordorder',
            options={'ordering': ['-created_date', '-id'], 'verbose_name_plural': 'DVDMS Record Orders'},
        ),
        migrations.AlterModelOptions(
            name='dvdmsstore',
            options={'ordering': ['-created_date', '-id'], 'verbose_name_plural': 'DVDMS Stores'},
        ),
        migrations.AlterModelOptions(
            name='dvdmssupplier',
            options={'ordering': ['-created_date', '-id'], 'verbose_name_plural': 'DVDMS Suppliers'},
        ),
        migrations.AlterModelOptions(
            name='dvdmssynclog',
            options={'ordering': ['-created_date', '-id'], 'verbose_name_plural': 'DVDMS Sync Logs'},
        ),
        migrations.AddIndex(
            model_name='dvdmsdrug',
            index=models.Index(fields=['drug_id'], name='dvdms_drug_drug_id'),
        ),
        migrations.AddIndex(
            model_name='dvdmsinwardrecord',
            index=models.Index(fields=['institute', '-created_date', '-id'], name='dvdms_inward_inst_created'),
        ),
        migrations.AddIndex(
            model_name='dvdmsproductmapping',
            index=models.Index(fields=['institute', '-created_date', '-id'], name='dvdms_prodmap_inst_created'),
        ),
        migrations.AddIndex(
            model_name='dvdmsrecorddelivery',
            index=models.Index(fields=['record_order', '-created_date', '-id'], name='dvdms_recdeliv_order_created'),
        ),
        migrations.AddIndex(
            model_name='dvdmsrecordorder',
            index=models.Index(fields=['institute', '-created_date', '-id'], name='dvdms_recorder_inst_created'),
        ),
        migrations.AddIndex(
            model_name='dvdmsrecordorder',
            index=models.Index(fields=['institute', 'status'], name='dvdms_recorder_inst_status'),
        ),
        migrations.AddIndex(
            model_name='dvdmssynclog',
            index=models.Index(fields=['institute', '-created_date', '-id'], name='dvdms_synclog_inst_created'),
        ),
        migrations.AddIndex(
            model_name='dvdmssynclog',
            index=models.Index(fields=['institute', 'sync_type', 'request_status'], name='dvdms_synclog_inst_type_stat'),
        ),
    ]
