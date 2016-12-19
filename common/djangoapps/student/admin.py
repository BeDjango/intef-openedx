#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Django admin pages for student app """
from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.utils.translation import pgettext

from ratelimitbackend import admin
from xmodule.modulestore.django import modulestore
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey

from config_models.admin import ConfigurationModelAdmin
from student.actions import export_as_csv_action
from student.models import (
    UserProfile, UserTestGroup, CourseEnrollmentAllowed, DashboardConfiguration, CourseEnrollment, Registration,
    PendingNameChange, CourseAccessRole, LinkedInAddToProfileConfiguration
)
from student.roles import REGISTERED_ACCESS_ROLES


class CourseAccessRoleForm(forms.ModelForm):
    """Form for adding new Course Access Roles view the Django Admin Panel."""

    class Meta(object):
        model = CourseAccessRole
        fields = '__all__'

    email = forms.EmailField(required=True)
    COURSE_ACCESS_ROLES = [(role_name, role_name) for role_name in REGISTERED_ACCESS_ROLES.keys()]
    role = forms.ChoiceField(choices=COURSE_ACCESS_ROLES)

    def clean_course_id(self):
        """
        Checking course-id format and course exists in module store.
        This field can be null.
        """
        if self.cleaned_data['course_id']:
            course_id = self.cleaned_data['course_id']

            try:
                course_key = CourseKey.from_string(course_id)
            except InvalidKeyError:
                raise forms.ValidationError(u"Invalid CourseID. Please check the format and re-try.")

            if not modulestore().has_course(course_key):
                raise forms.ValidationError(u"Cannot find course with id {} in the modulestore".format(course_id))

            return course_key

        return None

    def clean_org(self):
        """If org and course-id exists then Check organization name
        against the given course.
        """
        if self.cleaned_data.get('course_id') and self.cleaned_data['org']:
            org = self.cleaned_data['org']
            org_name = self.cleaned_data.get('course_id').org
            if org.lower() != org_name.lower():
                raise forms.ValidationError(
                    u"Org name {} is not valid. Valid name is {}.".format(
                        org, org_name
                    )
                )

        return self.cleaned_data['org']

    def clean_email(self):
        """
        Checking user object against given email id.
        """
        email = self.cleaned_data['email']
        try:
            user = User.objects.get(email=email)
        except Exception:
            raise forms.ValidationError(
                u"Email does not exist. Could not find {email}. Please re-enter email address".format(
                    email=email
                )
            )

        return user

    def clean(self):
        """
        Checking the course already exists in db.
        """
        cleaned_data = super(CourseAccessRoleForm, self).clean()
        if not self.errors:
            if CourseAccessRole.objects.filter(
                    user=cleaned_data.get("email"),
                    org=cleaned_data.get("org"),
                    course_id=cleaned_data.get("course_id"),
                    role=cleaned_data.get("role")
            ).exists():
                raise forms.ValidationError("Duplicate Record.")

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super(CourseAccessRoleForm, self).__init__(*args, **kwargs)
        if self.instance.user_id:
            self.fields['email'].initial = self.instance.user.email


class CourseAccessRoleAdmin(admin.ModelAdmin):
    """Admin panel for the Course Access Role. """
    form = CourseAccessRoleForm
    raw_id_fields = ("user",)
    exclude = ("user",)

    fieldsets = (
        (None, {
            'fields': ('email', 'course_id', 'org', 'role',)
        }),
    )

    list_display = (
        'id', 'user', 'org', 'course_id', 'role',
    )
    search_fields = (
        'id', 'user__username', 'user__email', 'org', 'course_id', 'role',
    )

    def save_model(self, request, obj, form, change):
        obj.user = form.cleaned_data['email']
        super(CourseAccessRoleAdmin, self).save_model(request, obj, form, change)


class LinkedInAddToProfileConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for the LinkedIn Add to Profile configuration. """

    class Meta(object):
        model = LinkedInAddToProfileConfiguration

    # Exclude deprecated fields
    exclude = ('dashboard_tracking_code',)


class CourseEnrollmentAdmin(admin.ModelAdmin):
    """ Admin interface for the CourseEnrollment model. """
    list_display = ('id', 'course_id', 'mode', 'user', 'is_active',)
    list_filter = ('mode', 'is_active',)
    raw_id_fields = ('user',)
    search_fields = ('course_id', 'mode', 'user__username',)

    def queryset(self, request):
        return super(CourseEnrollmentAdmin, self).queryset(request).select_related('user')

    class Meta(object):
        model = CourseEnrollment


class UserProfileAdmin(admin.ModelAdmin):
    """ Admin interface for UserProfile model. """
    list_display = ('user', 'name',)
    raw_id_fields = ('user',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'name',)

    def get_readonly_fields(self, request, obj=None):
        # The user field should not be editable for an existing user profile.
        if obj:
            return self.readonly_fields + ('user',)
        return self.readonly_fields

    class Meta(object):
        model = UserProfile


class LocalizadorDeUsuario(CourseEnrollment):
    class Meta:
        proxy = True


class CourseFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('Course')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'course_id'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        from course_api import api
        all_courses = []
        for course in api.list_courses(request, request.user.username):
            all_courses.append((course.id, course.id))
        return all_courses

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        try:
            course_key = CourseKey.from_string(request.GET.get('course_id'))
        except InvalidKeyError:
            course_key = None
        # if not modulestore().has_course(course_key):
        #     raise forms.ValidationError(u"Cannot find course with id {} in the modulestore".format(course_id))
        if course_key is None:
            return queryset
        else:
            return queryset.filter(course_id=course_key)


class ComuniFilter(admin.SimpleListFilter):
    title = _('Autonomous community')
    parameter_name = 'comuni'

    def lookups(self, request, model_admin):
        """
        Es necesario sacar las comunidades autonomas en el settings e importarlas desde ahi.
        Se esta repitiendo demasiado codigo
        """
        return (("", "--"),
                ("0", pgettext("female no one", "None")),
                ("1", "Andalucía"),
                ("2", "Aragón"),
                ("3", "Asturias"),
                ("4", "Baleares"),
                ("5", "Canarias"),
                ("6", "Cantabria"),
                ("7", "Castilla y León"),
                ("8", "Castilla - La Mancha"),
                ("9", "Cataluña"),
                ("10", "Extremadura"),
                ("11", "Galicia"),
                ("12", "Madrid"),
                ("13", "Murcia"),
                ("14", "Navarra"),
                ("15", "País Vasco"),
                ("16", "La Rioja"),
                ("17", "Valencia"),
                ("18", "Ceuta"),
                ("19", "Melilla"))

    def queryset(self, request, queryset):
        id_comuni = request.GET.get('comuni', None)
        if id_comuni is None:
            return queryset
        else:
            return queryset.filter(user__profile__comuni=id_comuni)


class EsdoceFilter(admin.SimpleListFilter):
    title = _('Instructor')
    parameter_name = 'esdoce'

    def lookups(self, request, model_admin):
        return (("", "--"),
                ("1", _("Yes")),
                ("2", _("No")))

    def queryset(self, request, queryset):
        id_esdoce = request.GET.get('esdoce', None)
        if id_esdoce is None:
            return queryset
        else:
            return queryset.filter(user__profile__esdoce=id_esdoce)


class CountryFilter(admin.SimpleListFilter):
    title = _('Country')
    parameter_name = 'country'
    countries = [("ES", _("Spain")),
                 ("AR", _("Argentina")),
                 ("MX", _("Mexico")),
                 ("UY", _("Uruguay")),
                 ("VE", _("Venezuela")),
                 ("CO", _("Colombia")),
                 ]

    def lookups(self, request, model_admin):
        return self.countries + [("others", _("Others"))]

    def queryset(self, request, queryset):
        id_country = request.GET.get('country', None)
        if id_country is None:
            return queryset
        else:
            if id_country == 'others':
                code_countries = [x[0] for x in self.countries]
                return queryset.exclude(user__profile__country__in=code_countries)
            else:
                return queryset.filter(user__profile__country=id_country)


class LocalizadorDeUsuarioAdmin(CourseEnrollmentAdmin):
    list_display = ('user', 'name', 'email', 'is_active', 'course_id', 'country', 'city', 'profile_comuni', 'esdoce', 'camp1', 'camp2', 'camp3', 'camp4', 'camp5')
    list_filter = (CourseFilter, CountryFilter, ComuniFilter, EsdoceFilter, 'is_active')
    search_fields = ('course_id', 'user__username', 'user__email', 'user__profile__name')
    can_delete = False
    actions = [export_as_csv_action("CSV Export", fields=['user.profile.name', 'user.email', 'course_id',
                                                          'user.profile.country', 'user.profile.esdoce', 'user.profile.comuni',
                                                          'user.profile.city', 'user.profile.camp1', 'user.profile.camp2',
                                                          'user.profile.camp3', 'user.profile.camp4', 'user.profile.camp5']), ]

    def email(self, item):
        return item.user.email
    email.short_description = _("Email")

    def name(self, item):
        return item.user.profile.name
    name.short_description = _("Name")

    def country(self, item):
        return item.user.profile.country.name
    country.short_description = _("Country")
    country.admin_order_field = 'user__profile__country'

    def city(self, item):
        return item.user.profile.city
    city.short_description = _("City")

    def profile_comuni(self, item):
        ccaa = {"": "--",
                "0": pgettext("female no one", "None"),
                "1": "Andalucía",
                "2": "Aragón",
                "3": "Asturias",
                "4": "Baleares",
                "5": "Canarias",
                "6": "Cantabria",
                "7": "Castilla y León",
                "8": "Castilla - La Mancha",
                "9": "Cataluña",
                "10": "Extremadura",
                "11": "Galicia",
                "12": "Madrid",
                "13": "Murcia",
                "14": "Navarra",
                "15": "País Vasco",
                "16": "La Rioja",
                "17": "Valencia",
                "18": "Ceuta",
                "19": "Melilla"}
        return ccaa.get(item.user.profile.comuni)
    profile_comuni.short_description = _("Autonomous community")

    def esdoce(self, item):
        options = {"": "--",
                   "1": _("Yes"),
                   "2": _("No")}
        return options.get(item.user.profile.esdoce)
    esdoce.short_description = _("Instructor?")

    def camp1(self, item):
        return item.user.profile.camp1
    camp1.short_description = _("Educational institution")

    def camp2(self, item):
        center_type = {"0": "--",
                       "1": pgettext('Educational institution', 'State'),
                       "2": _('Subsidized'),
                       "3": _('Private')}
        return center_type.get(item.user.profile.camp2)
    camp2.short_description = _("Type of institution")

    def camp3(self, item):
        return item.user.profile.camp3
    camp3.short_description = _("Instructing staff")

    def camp4(self, item):
        return item.user.profile.camp4
    camp4.short_description = _("Specialization")

    def camp5(self, item):
        return item.user.profile.camp5
    camp5.short_description = _("Educational role")

    def get_queryset(self, request):
        return self.model.objects.all().select_related("user__profile")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(UserTestGroup)

admin.site.register(CourseEnrollmentAllowed)

admin.site.register(Registration)

admin.site.register(PendingNameChange)

admin.site.register(CourseAccessRole, CourseAccessRoleAdmin)

admin.site.register(DashboardConfiguration, ConfigurationModelAdmin)

admin.site.register(LinkedInAddToProfileConfiguration, LinkedInAddToProfileConfigurationAdmin)

admin.site.register(CourseEnrollment, CourseEnrollmentAdmin)

admin.site.register(UserProfile, UserProfileAdmin)

admin.site.register(LocalizadorDeUsuario, LocalizadorDeUsuarioAdmin)
