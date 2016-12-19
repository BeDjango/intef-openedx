#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
from django.http import HttpResponse

CCAA = {"": u"--",
        "0": u"None",
        "1": u"Andalucía",
        "2": u"Aragón",
        "3": u"Asturias",
        "4": u"Baleares",
        "5": u"Canarias",
        "6": u"Cantabria",
        "7": u"Castilla y León",
        "8": u"Castilla - La Mancha",
        "9": u"Cataluña",
        "10": u"Extremadura",
        "11": u"Galicia",
        "12": u"Madrid",
        "13": u"Murcia",
        "14": u"Navarra",
        "15": u"País Vasco",
        "16": u"La Rioja",
        "17": u"Valencia",
        "18": u"Ceuta",
        "19": u"Melilla"}

DOCENTE = {"": u"--",
           "1": u"Sí",
           "2": u"No"}

TIPO_CENTRO = {"0": u"--",
               "1": u"Público",
               "2": u"Concertado",
               "3": u"Privado"}


def export_as_csv_action(description="Export selected objects as CSV file",
                         fields=None, exclude=None, header=True):
    """
    This function returns an export csv action
    'fields' and 'exclude' work like in django ModelForm
    'header' is whether or not to output the column names as the first row
    """
    def export_as_csv(modeladmin, request, queryset):
        """
        Generic csv export admin action.
        based on http://djangosnippets.org/snippets/1697/
        """
        opts = modeladmin.model._meta
        field_names = fields
        # if fields:
        #     field_names = field_names & fieldset
        # elif exclude:
        #     excludeset = set(exclude)
        #     field_names = field_names - excludeset

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s.csv' % unicode(opts).replace('.', '_')

        writer = csv.writer(response, delimiter=';')
        if header:

            cabecera = ['Nombre', 'Email', 'Curso',
                        'País', '¿Docente?', 'Comunidad autónoma',
                        'Ciudad', 'Centro educativo', 'Tipo de centro',
                        'Cuerpo docente', 'Especialidad', 'Función educativa']
            writer.writerow(cabecera)
        for obj in queryset:
            list_row = []
            profile_user = obj.user.profile
            for field in field_names:
                related_models = field.split('.')
                if len(related_models) == 3:
                    related_models = related_models[-1]
                    profile = profile_user
                else:
                    profile = None
                list_row.append(unicode(get_related_model(obj, related_models, profile)).encode("utf-8", "replace"))
            writer.writerow(list_row)
        return response
    export_as_csv.short_description = description
    return export_as_csv


def get_related_model(item, attr, profile=None):
    """
    This function return the value if the requested data is a relation of
    a relation of a relation... In example: 'user.profile.country'.
    Also, the function gives semantics to some attr that it are
    saved with integer values

    Arguments:
        item: query in django admin.
        attr: attribute to get.
        profile: user profile of the query.

    Returns:
        The value requested
    """
    if profile:
        if attr == 'comuni':
            return CCAA.get(getattr(profile, attr))
        elif attr == 'esdoce':
            return DOCENTE.get(getattr(profile, attr))
        elif attr == 'camp2':
            return TIPO_CENTRO.get(getattr(profile, attr))
        return getattr(profile, attr)
    else:
        if len(attr) > 1:
            item = getattr(item, attr[0])
            attr.pop(0)
            return get_related_model(item, attr)
        else:
            item = getattr(item, attr[0])
            return item
