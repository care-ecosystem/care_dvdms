import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('care_dvdms', '0006_remove_dvdmsinwarditemrecord_uniq_inward_record_item_and_more'),
        ('facility', '0485_rename_patientmobileotp_mobileotp'),
    ]

    operations = [
        migrations.CreateModel(
            name='DVDMSPrescriptionSequence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.PositiveSmallIntegerField()),
                ('last_value', models.PositiveIntegerField(default=0)),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dvdms_prescription_sequences', to='facility.facility')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('facility', 'year'), name='uniq_dvdms_prescription_facility_year')],
            },
        ),
    ]
