from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timesheet', '0002_employee_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='holiday',
            name='holiday_type',
            field=models.CharField(
                choices=[
                    ('PUBLIC_HOLIDAY', 'Public Holiday'),
                    ('WEEKEND', 'Weekend'),
                    ('US_HOLIDAY', 'US Holiday'),
                    ('SPECIAL_HOLIDAY', 'Special Holiday'),
                ],
                max_length=50,
            ),
        ),
    ]
