from custom_content import models
from django.conf import settings
from edxmako.shortcuts import render_to_string
from microsite_configuration import microsite


class CustomContentsService():
    """
    This class has one method, it recieves 5 parameters with differents options this methods make use of 'rendering'
    function to return the string that will be used in each case.The parameters used are language, templates ok or not ok,
    and dictionary context with different parameter (email, platform_name...)
    """

    @classmethod
    def construct_message(cls, language, type_message, template_no_ok, template_ok, context):
        """
        The function of this method is to extract model messages are sending by email or showing into screen,
        return a number of parameters and data depending on whether the query was successful or not.
        In this case the parameters returned are the template no ok where the default messages is rendering if query wasn't succesful,
        or template ok if query was succesful for screen messages. For email messages return the template no ok where the default message
        is rendering if query wasn't succesful, if query is ok, the function rendering is calling for return the finally String.
        """
        custom_message = ''
        if len(language) > 2:
            language = language[:2]
        custom_message = models.CustomContent.objects.filter(type_message=type_message, language=language, enable=True)
        if len(custom_message) > 0:
            custom_message = custom_message[0]
        else:
            custom_message = ''
        message = rendering(template_ok, template_no_ok, type_message, custom_message, context)
        return message


def rendering(template_ok, template_no_ok, type_message, custom_message, context):
    """
    This function receives 5 parameters and return the templates and strings where the data will be rendered.
    2 types of treatments, messages displayed on screen and texts to be sent by email.
    """
    message = ''
    subject = ''
    if type_message == 'Screen':
        if custom_message == '':
            message = render_to_string(
                template_no_ok,
                context
            )
            return message
        else:
            message = render_to_string(
                template_ok,
                context,
                {'custom_message': custom_message}
            )
            return message
    elif type_message == 'Activation Email' or type_message == 'Resend Email':
        if custom_message == '':
            message = render_to_string(
                template_no_ok,
                context
            )
            subject = render_to_string('emails/activation_email_subject.txt', context)
            subject = ''.join(subject.splitlines())
            return message, subject
        else:
            domain = microsite.get_value("SITE_NAME", settings.SITE_NAME)
            subject = custom_message.title_or_subject.format(email=context['email'], platform_name=context['platform_name'])
            message += custom_message.body.format(email=context['email'], platform_name=context['platform_name'])
            message += '\n\n'
            message += 'http://' + domain + '/activate/' + context['key']
            return message, subject
