# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CustomContent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title_or_subject', models.CharField(help_text="In Screen Messages, this field is the title of it, in Email Messages, this field is the subject of Email you send, you can use the {platform_name} and {email} tags where you want show your platform name and user's email.", max_length=200, verbose_name='Title or subject')),
                ('body', models.TextField(help_text="This field is the body in all messages, you can use the {platform_name} and {email} tags where you want show your platform name and user's email.", verbose_name='Cuerpo')),
                ('language', models.CharField(default=b'en', help_text="You can use this field to indicate the language of message, the platform will use one language or another depending of the user's language preferences.", max_length=7, verbose_name='Language', choices=[(b'en', 'English'), (b'es', 'Spanish')])),
                ('type_message', models.CharField(default=b'Screen', help_text='In this case, you can choose between different types of messages:</br>- Screen: is the messages that the platform will show in screen for welcome messages.</br>- Activation Email: The platform will use this type for send to user wellcome email.</br>- Resend Email: These emails will send to user when the user login without activate her account.</br>', max_length=16, verbose_name='Type message', choices=[(b'Activation Email', 'Activation Email'), (b'Resend Email', 'Resend Email'), (b'Screen', 'Screen')])),
                ('enable', models.BooleanField(default=False, help_text='For different types of messages, you should enable only one for each type of message, if no enabled will show which is default on the platform, if you select enable attribute and others elements with equal languages and types was enabled, your element will be enabled and others elements will be disabled.', verbose_name='Enable')),
            ],
            options={
                'verbose_name': 'Custom Content',
            },
        ),
    ]
