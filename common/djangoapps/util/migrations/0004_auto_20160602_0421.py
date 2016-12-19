# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('util', '0003_emailandwelcomemessage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailandwelcomemessage',
            name='type_message',
            field=models.CharField(default=b'Email', max_length=7, choices=[(b'Email', b'Email'), (b'Screen', b'Screen'), (b'Disable', b'Disable')]),
        ),
    ]

