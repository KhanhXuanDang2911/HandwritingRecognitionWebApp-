# Generated by Django 5.2 on 2025-05-08 03:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0002_user_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('suspended', 'Suspended')], default='active', max_length=20),
        ),
    ]
