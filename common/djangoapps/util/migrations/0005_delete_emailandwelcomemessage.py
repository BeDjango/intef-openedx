# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('util', '0004_auto_20160602_0421'),
    ]

    operations = [
        migrations.DeleteModel(
            name='EmailAndWelcomeMessage',
        ),
    ]

