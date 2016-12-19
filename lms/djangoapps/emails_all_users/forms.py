from django import forms
from django.utils.translation import ugettext_lazy as _

from bulk_email.models import CourseEmailTemplate


class EmailForm(forms.Form):

    select_template = forms.ChoiceField(label=_("Select template:"))
    subject = forms.CharField(label=_("Subject: "), max_length=100)
    message = forms.CharField(label=_("Message:"), widget=forms.Textarea(attrs={'class': 'tiny-mce'}))

    def __init__(self, *args, **kwargs):
        super(EmailForm, self).__init__(*args, **kwargs)
        list_options = []
        for template in CourseEmailTemplate.objects.filter(type_of_email='email_all_users'):
            single_option = [template.name, template.name]
            list_options.append(single_option)
        self.fields['select_template'].choices = list_options

