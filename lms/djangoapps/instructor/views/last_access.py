"""
Grade book view for instructor and pagination work (for grade book)
which is currently use by ccx and instructor apps.
"""
import math

from django.core.urlresolvers import reverse
from django.db import transaction
from django.views.decorators.cache import cache_control

from opaque_keys.edx.keys import CourseKey

from edxmako.shortcuts import render_to_response
from courseware.courses import get_course_with_access
from instructor.views.api import require_level
from student.models import CourseEnrollment



# Grade book: max students per page
MAX_STUDENTS_PER_PAGE_GRADE_BOOK = 50


def calculate_page_info(offset, total_students):
    """
    Takes care of sanitizing the offset of current page also calculates offsets for next and previous page
    and information like total number of pages and current page number.

    :param offset: offset for database query
    :return: tuple consist of page number, query offset for next and previous pages and valid offset
    """

    # validate offset.
    if not (isinstance(offset, int) or offset.isdigit()) or int(offset) < 0 or int(offset) >= total_students:
        offset = 0
    else:
        offset = int(offset)

    # calculate offsets for next and previous pages.
    next_offset = offset + MAX_STUDENTS_PER_PAGE_GRADE_BOOK
    previous_offset = offset - MAX_STUDENTS_PER_PAGE_GRADE_BOOK

    # calculate current page number.
    page_num = ((offset / MAX_STUDENTS_PER_PAGE_GRADE_BOOK) + 1)

    # calculate total number of pages.
    total_pages = int(math.ceil(float(total_students) / MAX_STUDENTS_PER_PAGE_GRADE_BOOK)) or 1

    if previous_offset < 0 or offset == 0:
        # We are at first page, so there's no previous page.
        previous_offset = None

    if next_offset >= total_students:
        # We've reached the last page, so there's no next page.
        next_offset = None

    return {
        "previous_offset": previous_offset,
        "next_offset": next_offset,
        "page_num": page_num,
        "offset": offset,
        "total_pages": total_pages
    }


def get_last_access_user_page(request, course_key):
    """
    Get student records per page along with page information i.e current page, total pages and
    offset information.
    """
    # Unsanitized offset
    current_offset = request.GET.get('offset', 0)
    enrollments = CourseEnrollment.objects.filter(
        course_id=course_key,
        is_active=True
    ).order_by('last_access', 'user__email').select_related("user__profile")

    total_students = enrollments.count()

    page = calculate_page_info(current_offset, total_students)

    offset = page["offset"]
    total_pages = page["total_pages"]

    if total_pages > 1:
        # Apply limit on queryset only if total number of students are greater then MAX_STUDENTS_PER_PAGE_GRADE_BOOK.
        enrollments = enrollments[offset: offset + MAX_STUDENTS_PER_PAGE_GRADE_BOOK]

    enrollments_info = [
        {
            'email': enroll.user.email,
            'name': enroll.user.profile.name,
            'username': enroll.user.username,
            'last_access': enroll.last_access,
        }
        for enroll in enrollments
    ]
    return enrollments_info, page


@transaction.non_atomic_requests
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_level('staff')
def get_all_last_access(request, course_id):
    """
    Show the last_access for the users enrolled in this course:
    Only displayed to course staff
    """
    course_key = CourseKey.from_string(course_id)
    course = get_course_with_access(request.user, 'staff', course_key, depth=None)
    enrollments_info, page = get_last_access_user_page(request, course_key)

    # student_info, page = get_grade_book_page(request, course, course_key)
    return render_to_response('courseware/last_access.html', {
        'page': page,
        'page_url': reverse('last_access', kwargs={'course_id': unicode(course_key)}),
        'course': course,
        'enrollments': enrollments_info
    })
