# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bulk_email', '0002_data__load_course_email_template'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseemailtemplate',
            name='default_selected',
            field=models.BooleanField(default=False),
        ),
    ]
