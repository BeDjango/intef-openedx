# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('course_creators', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='coursecreator',
            name='note',
            field=models.CharField(help_text='Notas opcionales sobre este usuario (por ejemplo, por qu\xe9 se ha denegado el acceso a crear cursos). ', max_length=512, blank=True),
        ),
        migrations.AlterField(
            model_name='coursecreator',
            name='state',
            field=models.CharField(default=b'unrequested', help_text='Estado actual del creador del curso', max_length=24, choices=[(b'unrequested', 'no solicitado'), (b'pending', 'pendiente'), (b'granted', 'concedido'), (b'denied', 'denegado')]),
        ),
        migrations.AlterField(
            model_name='coursecreator',
            name='state_changed',
            field=models.DateTimeField(help_text='Fecha de la \xfaltima actualizaci\xf3n del estado', verbose_name=b'state last updated', auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='coursecreator',
            name='user',
            field=models.OneToOneField(to=settings.AUTH_USER_MODEL, help_text='usuario del Studio'),
        ),
    ]
