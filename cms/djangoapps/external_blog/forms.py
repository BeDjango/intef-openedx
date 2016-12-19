from django import forms
from django.utils.translation import ugettext as _


class ExternalLinkTabForm(forms.Form):
    name = forms.CharField(label=_('Name tab'), max_length=100)
    link_value = forms.CharField(label=_('Link'), max_length=100)

    def clean(self):
        cleaned_data = super(ExternalLinkTabForm, self).clean()
        link_value = cleaned_data.get('link_value')

        if not (link_value.startswith('http://') or link_value.startswith('https://')):
            raise forms.ValidationError(_("It's necessary to include the 'http://' or "
                                        "'https://' in the address link.")
                                        )
