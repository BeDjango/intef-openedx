# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bulk_email', '0003_courseemailtemplate_default_selected'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseemail',
            name='custom_to_addr',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='courseemail',
            name='to_option',
            field=models.CharField(default=b'myself', max_length=64, choices=[(b'myself', b'Myself'), (b'staff', b'Staff and instructors'), (b'all', b'All'), (b'custom', b'Custom')]),
        ),
    ]
