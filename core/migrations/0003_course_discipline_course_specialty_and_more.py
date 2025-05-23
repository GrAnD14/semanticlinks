# Generated by Django 5.2.1 on 2025-05-21 16:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_discipline_created_by_term_created_by_profile'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='discipline',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.discipline'),
        ),
        migrations.AddField(
            model_name='course',
            name='specialty',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.specialty'),
        ),
        migrations.AddField(
            model_name='discipline',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='specialty',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]
