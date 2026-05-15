from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timesheet', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='role',
            field=models.CharField(
                choices=[('Dev', 'Dev'), ('QA', 'QA')],
                default='Dev',
                max_length=10,
            ),
        ),
    ]
