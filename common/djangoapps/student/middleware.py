"""
Middleware that checks user standing for the purpose of keeping users with
disabled accounts from accessing the site.
"""
from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.utils.translation import ugettext as _
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment, UserStanding


class UserStandingMiddleware(object):
    """
    Checks a user's standing on request. Returns a 403 if the user's
    status is 'disabled'.
    """
    def process_request(self, request):
        user = request.user
        try:
            user_account = UserStanding.objects.get(user=user.id)
            # because user is a unique field in UserStanding, there will either be
            # one or zero user_accounts associated with a UserStanding
        except UserStanding.DoesNotExist:
            pass
        else:
            if user_account.account_status == UserStanding.ACCOUNT_DISABLED:
                msg = _(
                    'Your account has been disabled. If you believe '
                    'this was done in error, please contact us at '
                    '{support_email}'
                ).format(
                    support_email=u'<a href="mailto:{address}?subject={subject_line}">{address}</a>'.format(
                        address=settings.DEFAULT_FEEDBACK_EMAIL,
                        subject_line=_('Disabled Account'),
                    ),
                )
                return HttpResponseForbidden(msg)


class LastCourseAccessMiddleware(object):
    """
    Saves the last access datetime for a user in a course. It is necessary the user visits
    any page of the course, except course info.
    """
    def process_view(self, request, view_func, view_args, view_kwargs):
        if not (request.user.is_anonymous() or view_func.func_name == 'course_info' or view_kwargs.get('course_id') is None):
            course_id = CourseKey.from_string(view_kwargs.get('course_id'))
            enrollment = CourseEnrollment.get_enrollment(user=request.user, course_key=course_id)
            if enrollment:
                enrollment.update_enrollment(last_access=timezone.now())
