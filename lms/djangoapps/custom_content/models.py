"""
Models for the custom content module
"""
from django.db import models
from django.utils.translation import ugettext_lazy as _


class CustomContent(models.Model):
    """ Model used to store the messages that notify the user registration and the need to
    activate his account via email and displayed on screen, this model have a title of screen messages or subject of emails
    and body of all type of messages, the language of this and the platform that is used (activation email, resend email or screen).
    """

    title_or_subject = models.CharField(_('Title or subject'),
                                        max_length=200,
                                        blank=False,
                                        help_text=_(u'In Screen Messages, this field is the title of it, in Email Messages, '
                                                    u'this field is the subject of Email you send, you can use the {platform_name} '
                                                    u"and {email} tags where you want show your platform name and user's email."))
    body = models.TextField(_('Cuerpo'),
                            blank=False,
                            help_text=_(u'This field is the body in all messages, '
                                        u'you can use the {platform_name} '
                                        u"and {email} tags where you want show your platform name and user's email."))
    ENGLISH = 'en'
    SPANISH = 'es'
    LANGUAGE_CHOICES = (
        (ENGLISH, _('English')),
        (SPANISH, _('Spanish')),
    )
    language = models.CharField(_('Language'),
                                max_length=7,
                                blank=False,
                                choices=LANGUAGE_CHOICES,
                                default=ENGLISH,
                                help_text=_(u'You can use this field to indicate the language of message, the platform will use '
                                            u"one language or another depending of the user's language preferences."))
    ACTIVATION_EMAIL = 'Activation Email'
    RESEND_EMAIL = 'Resend Email'
    SCREEN = 'Screen'
    TYPE_MESSAGE_CHOICES = (
        (ACTIVATION_EMAIL, _('Activation Email')),
        (RESEND_EMAIL, _('Resend Email')),
        (SCREEN, _('Screen')),
    )
    type_message = models.CharField(_('Type message'),
                                    max_length=16,
                                    blank=False,
                                    choices=TYPE_MESSAGE_CHOICES,
                                    default=SCREEN,
                                    help_text=_(u'In this case, you can choose between different types of messages:</br>'
                                                u"- Screen: is the messages that the platform will show in screen for welcome messages.</br>"
                                                u"- Activation Email: The platform will use this type for send to user wellcome email.</br>"
                                                u"- Resend Email: These emails will send to user when the user login without activate her account.</br>"))

    enable = models.BooleanField(_('Enable'),
                                 default=False,
                                 help_text=_(u'For different types of messages, you should enable only one for each type of message, '
                                             u'if no enabled will show which is default on the platform, if you select enable attribute '
                                             u'and others elements with equal languages and types was enabled, your element will be enabled '
                                             u'and others elements will be disabled.'))

    def save(self, *args, **kwargs):
        if self.enable is True:
            CustomContent.objects.filter(type_message=self.type_message, language=self.language).update(enable=False)
            super(CustomContent, self).save(*args, **kwargs)
        else:
            super(CustomContent, self).save(*args, **kwargs)

    class Meta:
        verbose_name = _('Custom Content')

    def __str__(self):
        return self.title_or_subject

    def __unicode__(self):
        return '%s' % (self.title_or_subject)
