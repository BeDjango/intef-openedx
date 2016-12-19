"""
Admin site bindings for Geturl Black List
"""

from django.contrib import admin

from geturl_blacklist.models import GeturlBlackList


class GeturlBlackListAdmin(admin.ModelAdmin):
    list_display = ('black_url',)

admin.site.register(GeturlBlackList, GeturlBlackListAdmin)


