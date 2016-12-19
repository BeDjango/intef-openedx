# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bulk_email', '0004_auto_20160513_0406'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailAllUsers',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.CharField(max_length=128, db_index=True)),
                ('subject', models.CharField(max_length=128, blank=True)),
                ('html_message', models.TextField(null=True, blank=True)),
                ('text_message', models.TextField(null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('from_addr', models.CharField(max_length=255, null=True)),
                ('template_name', models.CharField(max_length=255, null=True)),
                ('sender', models.ForeignKey(default=1, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
        ),
    ]

