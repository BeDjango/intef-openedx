# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bulk_email', '0006_auto_20161214_1046'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseemailtemplate',
            name='microsite_target',
            field=models.CharField(default=b'mooc', max_length=7, verbose_name=b'Microsite Target', choices=[(b'mooc', b'Mooc'), (b'nooc', b'Nooc'), (b'spooc', b'Spooc')]),
        ),
    ]
