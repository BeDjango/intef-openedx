#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django import forms
from custom_content.models import *


class ValidationTagsForm(forms.ModelForm):

    class Meta(object):
        model = CustomContent
        fields = ('title_or_subject', 'body', 'language', 'type_message', 'enable')

    def clean(self):
        title = self.cleaned_data.get('title_or_subject')
        body = self.cleaned_data.get('body')

        if '{platform_name}' and '{email}' not in title or '{platform_name}' and '{email}' not in body:
            raise forms.ValidationError("Son necesarios los tags {platform_name} y {email} en el título o asunto del mensaje y en el cuerpo de este")

        for index, value in enumerate(title):
            if value == '{':
                if title[index:index + 15] != '{platform_name}' and title[index:index + 7] != '{email}':
                    raise forms.ValidationError("Alguno de los tags utilizados en el campo title no es correcto, solo se permiten: {platform_name} y {email}")

        for index, value in enumerate(body):
            if value == '{':
                if body[index:index + 15] != '{platform_name}' and body[index:index + 7] != '{email}':
                    raise forms.ValidationError("Alguno de los tags utilizados en el campo body no es correcto, solo se permiten: {platform_name} y {email}")

        return self.cleaned_data
