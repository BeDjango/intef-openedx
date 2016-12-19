# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0002_auto_20151208_1034'),
    ]

    operations = [
        migrations.CreateModel(
            name='LocalizadorDeUsuario',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('student.courseenrollment',),
        ),
        migrations.AddField(
            model_name='courseenrollment',
            name='last_access',
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='historicalcourseenrollment',
            name='last_access',
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='camp1',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='camp2',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='camp3',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='camp4',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='camp5',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='comuni',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='esdoce',
            field=models.TextField(null=True, blank=True),
        ),
    ]
