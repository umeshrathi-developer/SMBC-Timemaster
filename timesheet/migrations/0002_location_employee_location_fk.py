from django.db import migrations, models
import django.db.models.deletion


DEFAULT_LOCATIONS = ['Pune', 'Chennai', 'Indore']


def migrate_employee_locations(apps, schema_editor):
    Location = apps.get_model('timesheet', 'Location')
    Employee = apps.get_model('timesheet', 'Employee')

    for location_name in DEFAULT_LOCATIONS:
        Location.objects.get_or_create(name=location_name)

    existing_locations = (
        Employee.objects.exclude(location__isnull=True)
        .exclude(location='')
        .values_list('location', flat=True)
        .distinct()
    )
    for location_name in existing_locations:
        Location.objects.get_or_create(name=str(location_name).strip())

    for employee in Employee.objects.all():
        location_name = str(employee.location or '').strip()
        if not location_name:
            continue
        location = Location.objects.filter(name__iexact=location_name).first()
        if location:
            employee.location_ref_id = location.id
            employee.save(update_fields=['location_ref'])


class Migration(migrations.Migration):

    dependencies = [
        ('timesheet', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Location',
                'verbose_name_plural': 'Locations',
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='location',
            index=models.Index(fields=['name'], name='timesheet_l_name_b53e0a_idx'),
        ),
        migrations.AddField(
            model_name='employee',
            name='location_ref',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='timesheet.location'),
        ),
        migrations.RunPython(migrate_employee_locations, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='employee',
            name='location',
        ),
        migrations.RenameField(
            model_name='employee',
            old_name='location_ref',
            new_name='location',
        ),
    ]
