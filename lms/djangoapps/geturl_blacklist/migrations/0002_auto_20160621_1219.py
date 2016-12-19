# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geturl_blacklist', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='geturlblacklist',
            name='url',
        ),
        migrations.AddField(
            model_name='geturlblacklist',
            name='black_url',
            field=models.CharField(default='', max_length=300, verbose_name='Black url'),
            preserve_default=False,
        ),
    ]
