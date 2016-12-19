# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bulk_email', '0005_emailallusers'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseemailtemplate',
            name='microsite_target',
            field=models.CharField(default=b'mooc', max_length=7, verbose_name=b'Microsite Target', choices=[(b'mooc', b'Mooc'), (b'nooc', b'Nooc')]),
        ),
        migrations.AddField(
            model_name='courseemailtemplate',
            name='type_of_email',
            field=models.CharField(default=b'course_email', max_length=20, verbose_name='Type of email', choices=[(b'course_email', 'Course Email'), (b'email_all_users', 'Email for all users')]),
        ),
    ]
