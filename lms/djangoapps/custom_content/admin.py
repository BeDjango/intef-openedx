"""
Admin site bindings for custom_content
"""

from django.contrib import admin

from custom_content.models import CustomContent
from custom_content.forms import ValidationTagsForm


class CustomContentAdmin(admin.ModelAdmin):
    list_display = ('title_or_subject', 'type_message', 'enable')
    form = ValidationTagsForm

admin.site.register(CustomContent, CustomContentAdmin)
