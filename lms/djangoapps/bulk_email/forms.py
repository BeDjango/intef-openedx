"""
Defines a form for providing validation of CourseEmail templates.
"""
import logging

from django import forms
from django.core.exceptions import ValidationError

from bulk_email.models import CourseEmailTemplate, COURSE_EMAIL_MESSAGE_BODY_TAG, CourseAuthorization

from opaque_keys import InvalidKeyError
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.django import modulestore
from opaque_keys.edx.keys import CourseKey
from opaque_keys.edx.locations import SlashSeparatedCourseKey

log = logging.getLogger(__name__)


class CourseEmailTemplateForm(forms.ModelForm):
    """Form providing validation of CourseEmail templates."""

    name = forms.CharField(required=False)

    class Meta(object):
        model = CourseEmailTemplate
        fields = ('html_template', 'plain_template', 'name', 'microsite_target', 'type_of_email', 'default_selected')

    def _validate_template(self, template):
        """Check the template for required tags."""
        index = template.find(COURSE_EMAIL_MESSAGE_BODY_TAG)
        if index < 0:
            msg = 'Missing tag: "{}"'.format(COURSE_EMAIL_MESSAGE_BODY_TAG)
            log.warning(msg)
            raise ValidationError(msg)
        if template.find(COURSE_EMAIL_MESSAGE_BODY_TAG, index + 1) >= 0:
            msg = 'Multiple instances of tag: "{}"'.format(COURSE_EMAIL_MESSAGE_BODY_TAG)
            log.warning(msg)
            raise ValidationError(msg)
        # TODO: add more validation here, including the set of known tags
        # for which values will be supplied.  (Email will fail if the template
        # uses tags for which values are not supplied.)

    def clean_default_selected(self):
        """Validate the Default selected."""
        default_selected = self.cleaned_data["default_selected"]
        # No validation
        return default_selected

    def clean_type_of_email(self):
        """Validate the type_of_email."""
        type_of_email = self.cleaned_data["type_of_email"]
        # No validation
        return type_of_email

    def clean_html_template(self):
        """Validate the HTML template."""
        template = self.cleaned_data["html_template"]
        self._validate_template(template)
        return template

    def clean_plain_template(self):
        """Validate the plaintext template."""
        template = self.cleaned_data["plain_template"]
        self._validate_template(template)
        return template


    def clean_microsite_target_template(self):
        """Validate the plaintext template."""
        template = self.cleaned_data["microsite_target"]
        self._validate_template(template)
        return template

    def clean_name(self):
        """Validate the name field. Enforce uniqueness constraint on 'name' field"""

        # Note that we get back a blank string in the Form for an empty 'name' field
        # we want those to be set to None in Python and NULL in the database
        name = self.cleaned_data.get("name").strip() or None

        # if we are creating a new CourseEmailTemplate, then we need to
        # enforce the uniquess constraint as part of the Form validation
        if not self.instance.pk:
            try:
                CourseEmailTemplate.get_template(name)
                # already exists, this is no good
                raise ValidationError('Name of "{}" already exists, this must be unique.'.format(name))
            except CourseEmailTemplate.DoesNotExist:
                # this is actually the successful validation
                pass
        return name


class CourseAuthorizationAdminForm(forms.ModelForm):
    """Input form for email enabling, allowing us to verify data."""

    class Meta(object):
        model = CourseAuthorization
        fields = '__all__'

    def clean_course_id(self):
        """Validate the course id"""
        cleaned_id = self.cleaned_data["course_id"]
        try:
            course_key = CourseKey.from_string(cleaned_id)
        except InvalidKeyError:
            try:
                course_key = SlashSeparatedCourseKey.from_deprecated_string(cleaned_id)
            except InvalidKeyError:
                msg = u'Course id invalid.'
                msg += u' --- Entered course id was: "{0}". '.format(cleaned_id)
                msg += 'Please recheck that you have supplied a valid course id.'
                raise forms.ValidationError(msg)

        if not modulestore().has_course(course_key):
            msg = u'COURSE NOT FOUND'
            msg += u' --- Entered course id was: "{0}". '.format(course_key.to_deprecated_string())
            msg += 'Please recheck that you have supplied a valid course id.'
            raise forms.ValidationError(msg)

        # Now, try and discern if it is a Studio course - HTML editor doesn't work with XML courses
        is_studio_course = modulestore().get_modulestore_type(course_key) != ModuleStoreEnum.Type.xml
        if not is_studio_course:
            msg = "Course Email feature is only available for courses authored in Studio. "
            msg += '"{0}" appears to be an XML backed course.'.format(course_key.to_deprecated_string())
            raise forms.ValidationError(msg)

        return course_key
