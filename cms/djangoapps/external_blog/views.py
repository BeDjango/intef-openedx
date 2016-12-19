from opaque_keys.edx.keys import CourseKey
from student.auth import has_course_author_access
from django.core.exceptions import PermissionDenied
from xmodule.modulestore.django import modulestore
from xmodule.tabs import CourseTabList
from lms.djangoapps.courseware.tabs import ExternalLinkCourseTab
from .forms import ExternalLinkTabForm

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from edxmako.shortcuts import render_to_response
from django.core.context_processors import csrf


def redirect_view(request, course_key_string=None):
    course_key = CourseKey.from_string(course_key_string)
    if not has_course_author_access(request.user, course_key):
        raise PermissionDenied()

    course_item = modulestore().get_course(course_key)

    if request.method == 'GET':
        for tab in CourseTabList.iterate_displayable(course_item, inline_collections=False):
            if isinstance(tab, ExternalLinkCourseTab):
                data = {'name': tab.name, 'link_value': tab.link_value}
                form = ExternalLinkTabForm(data=data)
                csrf_token = csrf(request)['csrf_token']
                return render_to_response('external_blog.html',
                                          {'form': form, 'csrf': csrf_token})
    elif request.method == 'POST':
        for tab in CourseTabList.iterate_displayable(course_item, inline_collections=False):
            if isinstance(tab, ExternalLinkCourseTab):
                data = request.POST
                form = ExternalLinkTabForm(data=data)
                if form.is_valid():
                    tab.link_value = form.cleaned_data.get('link_value')
                    tab.name = form.cleaned_data.get('name')
                    modulestore().update_item(course_item, request.user.id)
                    return HttpResponseRedirect(reverse('contentstore.views.tabs_handler', kwargs={'course_key_string': course_key_string}))
                csrf_token = csrf(request)['csrf_token']
                return render_to_response('external_blog.html',
                                          {'form': form, 'csrf': csrf_token})
