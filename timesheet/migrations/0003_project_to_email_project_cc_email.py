from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timesheet', '0002_location_employee_location_fk'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='cc_email',
            field=models.TextField(blank=True, help_text='Semicolon-separated CC email addresses'),
        ),
        migrations.AddField(
            model_name='project',
            name='to_email',
            field=models.TextField(blank=True, help_text='Semicolon-separated To email addresses'),
        ),
    ]
