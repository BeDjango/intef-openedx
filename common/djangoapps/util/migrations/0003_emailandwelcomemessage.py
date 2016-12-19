# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('util', '0002_data__default_rate_limit_config'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailAndWelcomeMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=200)),
                ('body', models.TextField()),
                ('language', models.CharField(default=b'English', max_length=7, choices=[(b'English', b'English'), (b'Spanish', b'Spanish')])),
                ('type_message', models.CharField(default=b'Email', max_length=6, choices=[(b'Email', b'Email'), (b'Screen', b'Screen')])),
            ],
        ),
    ]

