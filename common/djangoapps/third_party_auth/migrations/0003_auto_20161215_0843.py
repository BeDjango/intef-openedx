# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('third_party_auth', '0002_auto_20161213_1028'),
    ]

    operations = [
        migrations.AlterField(
            model_name='oauth2providerconfig',
            name='backend_name',
            field=models.CharField(help_text=b'Which python-social-auth OAuth2 provider backend to use. The list of backend choices is determined by the THIRD_PARTY_AUTH_BACKENDS setting.', max_length=50, db_index=True),
        ),
        migrations.AlterField(
            model_name='samlproviderconfig',
            name='backend_name',
            field=models.CharField(default=b'tpa-saml', help_text=b"Which python-social-auth provider backend to use. 'tpa-saml' is the standard edX SAML backend.", max_length=50),
        ),
    ]
