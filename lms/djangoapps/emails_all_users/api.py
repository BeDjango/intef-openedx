import hashlib
import logging
import json
import psutil
from time import time, sleep
from uuid import uuid4
import dogstats_wrapper as dog_stats_api
from contextlib import contextmanager
from collections import Counter

from celery import Task, task
from celery.states import READY_STATES, SUCCESS, FAILURE, RETRY
from celery.exceptions import RetryTaskError  # pylint: disable=no-name-in-module, import-error

from smtplib import SMTPDataError

from django.utils.translation import ugettext as _
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction, reset_queries, DatabaseError
from django.utils.translation import ugettext_noop
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.cache import cache_control
from django.core.urlresolvers import reverse
from django.core.mail import EmailMultiAlternatives, get_connection
from instructor_task.views import get_task_completion_info
from instructor.views.api import require_post_params
from instructor_task.api_helper import _get_xmodule_instance_args
from instructor_task.subtasks import (_get_number_of_subtasks, SubtaskStatus,
                                      DuplicateTaskException, _acquire_subtask_lock,
                                      _release_subtask_lock)
from util.json_request import JsonResponse
# from util.db import outer_atomic

from bulk_email.models import EmailAllUsers
from bulk_email.tasks import (SINGLE_EMAIL_FAILURE_ERRORS, INFINITE_RETRY_ERRORS,
                              _submit_for_retry, LIMITED_RETRY_ERRORS,
                              BULK_EMAIL_FAILURE_ERRORS, _get_current_task)
from emails_all_users.models import EmailAllUsersTask
from emails_all_users.tasks import BaseTask


log = logging.getLogger(__name__)
# define different loggers for use within tasks and on client side
TASK_LOG = logging.getLogger('edx.celery.task')

MAX_DATABASE_LOCK_RETRIES = 5


class AlreadyRunningError(Exception):
    """Exception indicating that a background task is already running"""
    pass


@transaction.non_atomic_requests
@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
@require_post_params(subject="subject line", message="message text")
def send_email(request):
    # Hay que proteger que solo puedan acceder los administradores
    """
    Send an email to all the users.
    Query Parameters:
    - 'subject' specifies email's subject
    - 'message' specifies email's content
    """
    # course_id = SlashSeparatedCourseKey.from_deprecated_string(course_id)

    # if not bulk_email_is_enabled_for_course(course_id):
    #     return HttpResponseForbidden("Email is not enabled for this course.")

    # send_to = request.POST.get("send_to")
    subject = request.POST.get("subject")
    message = request.POST.get("message")
    template = request.POST.get("select_template")

    ##### Hay que tener en cuenta la posibilidad de enviar emails masivo en los microsites
    # template_name = microsite.get_value('course_email_template_name')
    # from_addr = microsite.get_value('course_email_from_addr')
    # if template_name is None and template != 'default-none':
    if template != 'default-none':
        template_name = template

    # Hay que hacer que se pueda no enviar un curso a CourseEmail, o crear un modelo que haga eso
    email = EmailAllUsers.create(
        request.user,
        subject, message,
        template_name=template_name,
        # from_addr=None,
        # custom_to_addr=custom_to_addr
    )

    # Submit the task, so that the correct InstructorTask object gets created (for monitoring purposes)
    submit_bulk_all_users_email(request, email.id)

    response_payload = {
        # 'course_id': course_id.to_deprecated_string(),
        'success': True
        # 'addresses_validation': addresses_validation
    }
    return JsonResponse(response_payload)


def submit_bulk_all_users_email(request, email_id):
    task_type = 'bulk_all_users_email'
    task_class = send_all_users_email_task

    task_input = {'email_id': email_id}
    task_key_stub = "{email_id}_all_users_email".format(email_id=email_id)
    # create the key value by using MD5 hash:
    task_key = hashlib.md5(task_key_stub).hexdigest()
    return submit_all_users_email_task(request, task_type, task_class, task_input, task_key)


def submit_all_users_email_task(request, task_type, task_class, task_input, task_key):
    # with outer_atomic():
    instructor_task = _reserve_all_users_email_task(task_type, task_key, task_input, request.user)

    # make sure all data has been committed before handing off task to celery.

    task_id = instructor_task.task_id
    task_args = [instructor_task.id, _get_xmodule_instance_args(request, task_id)]
    task_class.apply_async(task_args, task_id=task_id)

    return instructor_task


def _reserve_all_users_email_task(task_type, task_key, task_input, requester):
    """
    Creates a database entry to indicate that a task is in progress.

    Throws AlreadyRunningError if the task is already in progress.
    Includes the creation of an arbitrary value for task_id, to be
    submitted with the task call to celery.

    Note that there is a chance of a race condition here, when two users
    try to run the same task at almost exactly the same time.  One user
    could be after the check and before the create when the second user
    gets to the check.  At that point, both users are able to run their
    tasks simultaneously.  This is deemed a small enough risk to not
    put in further safeguards.
    """

    if _all_users_email_task_is_running(task_type, task_key):
        log.warning("Duplicate task found for task_type %s and task_key %s", task_type, task_key)
        raise AlreadyRunningError("requested task is already running")

    try:
        most_recent_id = EmailAllUsersTask.objects.latest('id').id
    except EmailAllUsersTask.DoesNotExist:
        most_recent_id = "None found"
    finally:
        log.warning(
            "No duplicate tasks found: task_type %s, task_key %s, and most recent task_id = %s",
            task_type,
            task_key,
            most_recent_id
        )

    # Create log entry now, so that future requests will know it's running.
    return EmailAllUsersTask.create(task_type, task_key, task_input, requester)


def _all_users_email_task_is_running(task_type, task_key):
    """Checks if a particular task is already running"""
    running_tasks = EmailAllUsersTask.objects.filter(task_type=task_type, task_key=task_key)
    # exclude states that are "ready" (i.e. not "running", e.g. failure, success, revoked):
    for state in READY_STATES:
        running_tasks = running_tasks.exclude(task_state=state)
    return len(running_tasks) > 0


# @task(base=BaseTask)
@task(base=BaseTask)
def send_all_users_email_task(entry_id, _xmodule_instance_args):
    # Translators: This is a past-tense verb that is inserted into task progress messages as {action}.
    action_name = ugettext_noop('emailed')
    visit_fcn = perform_delegate_email_batches
    return run_all_users_email_task(entry_id, visit_fcn, action_name)


def run_all_users_email_task(entry_id, task_fcn, action_name):
    """
    Applies the `task_fcn` to the arguments defined in `entry_id` InstructorTask.

    Arguments passed to `task_fcn` are:

     `entry_id` : the primary key for the InstructorTask entry representing the task.
     `course_id` : the id for the course.
     `task_input` : dict containing task-specific arguments, JSON-decoded from InstructorTask's task_input.
     `action_name` : past-tense verb to use for constructing status messages.

    If no exceptions are raised, the `task_fcn` should return a dict containing
    the task's result with the following keys:

          'attempted': number of attempts made
          'succeeded': number of attempts that "succeeded"
          'skipped': number of attempts that "skipped"
          'failed': number of attempts that "failed"
          'total': number of possible subtasks to attempt
          'action_name': user-visible verb to use in status messages.
              Should be past-tense.  Pass-through of input `action_name`.
          'duration_ms': how long the task has (or had) been running.

    """

    # Get the InstructorTask to be updated. If this fails then let the exception return to Celery.
    # There's no point in catching it here.
    #with outer_atomic():
    entry = EmailAllUsersTask.objects.get(pk=entry_id)
    entry.task_state = "PROGRESS"
    entry.save_now()

    # Get inputs to use in this task from the entry
    task_id = entry.task_id
    task_input = json.loads(entry.task_input)

    # Construct log message
    fmt = u'Task: {task_id}, EmailAllUsersTask ID: {entry_id}, Input: {task_input}'
    task_info_string = fmt.format(task_id=task_id, entry_id=entry_id, task_input=task_input)
    TASK_LOG.info(u'%s, Starting update (nothing %s yet)', task_info_string, action_name)

    # Check that the task_id submitted in the InstructorTask matches the current task
    # that is running.
    request_task_id = _get_current_task().request.id
    if task_id != request_task_id:
        fmt = u'{task_info}, Requested task did not match actual task "{actual_id}"'
        message = fmt.format(task_info=task_info_string, actual_id=request_task_id)
        TASK_LOG.error(message)
        raise ValueError(message)

    # CUIDADO
    with dog_stats_api.timer('instructor_tasks.time.overall', tags=[u'action:{name}'.format(name=action_name)]):
        task_progress = task_fcn(entry_id, task_input, action_name)

    # Release any queries that the connection has been hanging onto
    reset_queries()

    # Log and exit, returning task_progress info as task result
    TASK_LOG.info(u'%s, Task type: %s, Finishing task: %s', task_info_string, action_name, task_progress)
    return task_progress


def perform_delegate_email_batches(entry_id, task_input, action_name):
    """
    Delegates emails by querying for the list of recipients who should
    get the mail, chopping up into batches of no more than settings.BULK_EMAIL_EMAILS_PER_TASK
    in size, and queueing up worker jobs.
    """
    entry = EmailAllUsersTask.objects.get(pk=entry_id)
    # Get inputs to use in this task from the entry.
    # user_id = entry.requester.id
    task_id = entry.task_id

    # Fetch the CourseEmail.
    email_id = task_input['email_id']
    try:
        # email_obj = EmailAllUsers.objects.get(id=email_id)
        EmailAllUsers.objects.get(id=email_id)
    except EmailAllUsers.DoesNotExist:
        # The CourseEmail object should be committed in the view function before the task
        # is submitted and reaches this point.
        log.warning(u"Task %s: Failed to get EmailAllUsers with id %s", task_id, email_id)
        raise

    # Check to see if email batches have already been defined.  This seems to
    # happen sometimes when there is a loss of connection while a task is being
    # queued.  When this happens, the same task gets called again, and a whole
    # new raft of subtasks gets queued up.  We will assume that if subtasks
    # have already been defined, there is no need to redefine them below.
    # So we just return right away.  We don't raise an exception, because we want
    # the current task to be marked with whatever it had been marked with before.
    if len(entry.subtasks) > 0 and len(entry.task_output) > 0:
        log.warning(u"Task %s has already been processed for email %s!  EmailAllUsersTask = %s", task_id, email_id, entry)
        progress = json.loads(entry.task_output)
        return progress

    # CUIDADO CON EL TO OPTION
    global_email_context = {'account_settings_url': 'https://{}{}'.format(settings.SITE_NAME, reverse('account_settings')),
                            'email_settings_url': 'https://{}{}'.format(settings.SITE_NAME, reverse('dashboard')),
                            'platform_name': settings.PLATFORM_NAME}

    recipient_qsets = []
    recipient_qsets.append(User.objects.none())
    recipient_qsets.append(User.objects.filter(is_active=True))
    recipient_fields = ['profile__name', 'email']

    log.info(u"Task %s: Preparing to queue subtasks for sending emails for all users")

    total_recipients = sum([recipient_queryset.count() for recipient_queryset in recipient_qsets])

    routing_key = settings.BULK_EMAIL_ROUTING_KEY
    # if there are few enough emails, send them through a different queue
    # to avoid large courses blocking emails to self and staff
    if total_recipients <= settings.BULK_EMAIL_JOB_SIZE_THRESHOLD:
        routing_key = settings.BULK_EMAIL_ROUTING_KEY_SMALL_JOBS

    def _create_send_email_subtask(to_list, initial_subtask_status):
        """Creates a subtask to send email to a given recipient list."""
        subtask_id = initial_subtask_status.task_id
        new_subtask = send_all_users_email.subtask(
            (
                entry_id,
                email_id,
                to_list,
                global_email_context,
                initial_subtask_status.to_dict(),
            ),
            task_id=subtask_id,
            routing_key=routing_key,
        )
        return new_subtask

    progress = queue_subtasks_for_query_all_users_email(
        entry,
        action_name,
        _create_send_email_subtask,
        recipient_qsets,
        recipient_fields,
        settings.BULK_EMAIL_EMAILS_PER_TASK,
        total_recipients,
    )

    # We want to return progress here, as this is what will be stored in the
    # AsyncResult for the parent task as its return value.
    # The AsyncResult will then be marked as SUCCEEDED, and have this return value as its "result".
    # That's okay, for the InstructorTask will have the "real" status, and monitoring code
    # should be using that instead.
    return progress


# pylint: disable=bad-continuation
def queue_subtasks_for_query_all_users_email(
    entry,
    action_name,
    create_subtask_fcn,
    item_querysets,
    item_fields,
    items_per_task,
    total_num_items,
):
    """
    Generates and queues subtasks to each execute a chunk of "items" generated by a queryset.

    Arguments:
        `entry` : the InstructorTask object for which subtasks are being queued.
        `action_name` : a past-tense verb that can be used for constructing readable status messages.
        `create_subtask_fcn` : a function of two arguments that constructs the desired kind of subtask object.
            Arguments are the list of items to be processed by this subtask, and a SubtaskStatus
            object reflecting initial status (and containing the subtask's id).
        `item_querysets` : a list of query sets that define the "items" that should be passed to subtasks.
        `item_fields` : the fields that should be included in the dict that is returned.
            These are in addition to the 'pk' field.
        `items_per_task` : maximum size of chunks to break each query chunk into for use by a subtask.
        `total_num_items` : total amount of items that will be put into subtasks

    Returns:  the task progress as stored in the InstructorTask object.

    """
    task_id = entry.task_id

    # Calculate the number of tasks that will be created, and create a list of ids for each task.
    total_num_subtasks = _get_number_of_subtasks(total_num_items, items_per_task)
    subtask_id_list = [str(uuid4()) for _ in range(total_num_subtasks)]

    # Update the InstructorTask  with information about the subtasks we've defined.
    TASK_LOG.info(
        "Task %s: updating EmailAllUsersTask %s with subtask info for %s subtasks to process %s items.",
        task_id,
        entry.id,
        total_num_subtasks,
        total_num_items,
    )
    # Make sure this is committed to database before handing off subtasks to celery.
    #with outer_atomic():
    progress = initialize_all_users_email_subtask_info(entry, action_name, total_num_items, subtask_id_list)

    # Construct a generator that will return the recipients to use for each subtask.
    # Pass in the desired fields to fetch for each recipient.
    item_list_generator = _generate_items_for_all_users_email_subtask(
        item_querysets,
        item_fields,
        total_num_items,
        items_per_task,
        total_num_subtasks,
    )

    # Now create the subtasks, and start them running.
    TASK_LOG.info(
        "Task %s: creating %s subtasks to process %s items.",
        task_id,
        total_num_subtasks,
        total_num_items,
    )
    num_subtasks = 0
    for item_list in item_list_generator:
        subtask_id = subtask_id_list[num_subtasks]
        num_subtasks += 1
        subtask_status = SubtaskStatus.create(subtask_id)
        new_subtask = create_subtask_fcn(item_list, subtask_status)
        new_subtask.apply_async()

    # Subtasks have been queued so no exceptions should be raised after this point.

    # Return the task progress as stored in the InstructorTask object.
    return progress


def _generate_items_for_all_users_email_subtask(
    item_querysets,  # pylint: disable=bad-continuation
    item_fields,
    total_num_items,
    items_per_task,
    total_num_subtasks,
):
    """
    Generates a chunk of "items" that should be passed into a subtask.

    Arguments:
        `item_querysets` : a list of query sets, each of which defines the "items" that should be passed to subtasks.
        `item_fields` : the fields that should be included in the dict that is returned.
            These are in addition to the 'pk' field.
        `total_num_items` : the result of summing the count of each queryset in `item_querysets`.
        `items_per_query` : size of chunks to break the query operation into.
        `items_per_task` : maximum size of chunks to break each query chunk into for use by a subtask.
        `course_id` : course_id of the course. Only needed for the track_memory_usage context manager.

    Returns:  yields a list of dicts, where each dict contains the fields in `item_fields`, plus the 'pk' field.

    Warning:  if the algorithm here changes, the _get_number_of_subtasks() method should similarly be changed.
    """
    num_items_queued = 0
    all_item_fields = list(item_fields)
    all_item_fields.append('pk')
    num_subtasks = 0

    items_for_task = []

    # Cuidado
    with track_memory_usage_all_users_email('course_email.subtask_generation.memory'):
        for queryset in item_querysets:
            for item in queryset.values(*all_item_fields).iterator():
                if len(items_for_task) == items_per_task and num_subtasks < total_num_subtasks - 1:
                    yield items_for_task
                    num_items_queued += items_per_task
                    items_for_task = []
                    num_subtasks += 1
                items_for_task.append(item)

        # yield remainder items for task, if any
        if items_for_task:
            num_items_queued += len(items_for_task)
            yield items_for_task

    # Note, depending on what kind of DB is used, it's possible for the queryset
    # we iterate over to change in the course of the query. Therefore it's
    # possible that there are more (or fewer) items queued than were initially
    # calculated. It also means it's possible that the last task contains
    # more items than items_per_task allows. We expect this to be a small enough
    # number as to be negligible.
    if num_items_queued != total_num_items:
        TASK_LOG.info("Number of items generated by chunking %s not equal to original total %s", num_items_queued, total_num_items)


@contextmanager
def track_memory_usage_all_users_email(metric):
    """
    Context manager to track how much memory (in bytes) a given process uses.
    Metrics will look like: 'course_email.subtask_generation.memory.rss'
    or 'course_email.subtask_generation.memory.vms'.
    """
    memory_types = ['rss', 'vms']
    process = psutil.Process()
    baseline_memory_info = process.get_memory_info()
    baseline_usages = [getattr(baseline_memory_info, memory_type) for memory_type in memory_types]
    yield
    for memory_type, baseline_usage in zip(memory_types, baseline_usages):
        total_memory_info = process.get_memory_info()
        total_usage = getattr(total_memory_info, memory_type)
        memory_used = total_usage - baseline_usage
        dog_stats_api.increment(
            metric + "." + memory_type,
            memory_used,
            # tags=["course_id:{}".format(course_id)],
        )


def initialize_all_users_email_subtask_info(entry, action_name, total_num, subtask_id_list):
    """
    Store initial subtask information to InstructorTask object.

    The InstructorTask's "task_output" field is initialized.  This is a JSON-serialized dict.
    Counters for 'attempted', 'succeeded', 'failed', 'skipped' keys are initialized to zero,
    as is the 'duration_ms' value.  A 'start_time' is stored for later duration calculations,
    and the total number of "things to do" is set, so the user can be told how much needs to be
    done overall.  The `action_name` is also stored, to help with constructing more readable
    task_progress messages.

    The InstructorTask's "subtasks" field is also initialized.  This is also a JSON-serialized dict.
    Keys include 'total', 'succeeded', 'retried', 'failed', which are counters for the number of
    subtasks.  'Total' is set here to the total number, while the other three are initialized to zero.
    Once the counters for 'succeeded' and 'failed' match the 'total', the subtasks are done and
    the InstructorTask's "status" will be changed to SUCCESS.

    The "subtasks" field also contains a 'status' key, that contains a dict that stores status
    information for each subtask.  The value for each subtask (keyed by its task_id)
    is its subtask status, as defined by SubtaskStatus.to_dict().

    This information needs to be set up in the InstructorTask before any of the subtasks start
    running.  If not, there is a chance that the subtasks could complete before the parent task
    is done creating subtasks.  Doing so also simplifies the save() here, as it avoids the need
    for locking.

    Monitoring code should assume that if an InstructorTask has subtask information, that it should
    rely on the status stored in the InstructorTask object, rather than status stored in the
    corresponding AsyncResult.
    """
    task_progress = {
        'action_name': action_name,
        'attempted': 0,
        'failed': 0,
        'skipped': 0,
        'succeeded': 0,
        'total': total_num,
        'duration_ms': int(0),
        'start_time': time()
    }
    entry.task_output = EmailAllUsersTask.create_output_for_success(task_progress)
    entry.task_state = "PROGRESS"

    # Write out the subtasks information.
    num_subtasks = len(subtask_id_list)
    # Note that may not be necessary to store initial value with all those zeroes!
    # Write out as a dict, so it will go more smoothly into json.
    subtask_status = {subtask_id: (SubtaskStatus.create(subtask_id)).to_dict() for subtask_id in subtask_id_list}
    subtask_dict = {
        'total': num_subtasks,
        'succeeded': 0,
        'failed': 0,
        'status': subtask_status
    }
    entry.subtasks = json.dumps(subtask_dict)

    # and save the entry immediately, before any subtasks actually start work:
    entry.save_now()
    return task_progress


@task(default_retry_delay=settings.BULK_EMAIL_DEFAULT_RETRY_DELAY, max_retries=settings.BULK_EMAIL_MAX_RETRIES)
def send_all_users_email(entry_id, email_id, to_list, global_email_context, subtask_status_dict):
    subtask_status = SubtaskStatus.from_dict(subtask_status_dict)
    current_task_id = subtask_status.task_id
    num_to_send = len(to_list)
    log.info((u"Preparing to send email %s to %d recipients as subtask %s "
              u"for email for all users task %d: context = %s, status=%s"),
             email_id, num_to_send, current_task_id, entry_id, global_email_context, subtask_status)

    check_all_users_email_subtask_is_valid(entry_id, current_task_id, subtask_status)

    send_exception = None
    new_subtask_status = None
    try:
        # course_title = global_email_context['course_title']
        # ENTENDER LOS PARAMETROS DEL TIMER
        with dog_stats_api.timer('course_email.single_task.time.overall'):
            new_subtask_status, send_exception = _send_all_users_email(
                entry_id,
                email_id,
                to_list,
                global_email_context,
                subtask_status,
            )
    except Exception:
        log.exception("Send-email task %s for email %s: failed unexpectedly!", current_task_id, email_id)
        subtask_status.increment(failed=num_to_send, state=FAILURE)
        update_subtask_status(entry_id, current_task_id, subtask_status)
        raise

    if send_exception is None:
        log.info("Send-email task %s for email %s: succeeded", current_task_id, email_id)
        update_subtask_status(entry_id, current_task_id, new_subtask_status)
    elif isinstance(send_exception, RetryTaskError):
        log.warning("Send-email task %s for email %s: being retried", current_task_id, email_id)
        raise send_exception  # pylint: disable=raising-bad-type
    else:
        log.error("Send-email task %s for email %s: failed: %s", current_task_id, email_id, send_exception)
        update_subtask_status(entry_id, current_task_id, new_subtask_status)
        raise send_exception  # pylint: disable=raising-bad-type

    log.info("Send-email task %s for email %s: returning status %s", current_task_id, email_id, new_subtask_status)
    return new_subtask_status.to_dict()


def check_all_users_email_subtask_is_valid(entry_id, current_task_id, new_subtask_status):
    # Confirm that the InstructorTask actually defines subtasks.
    entry = EmailAllUsersTask.objects.get(pk=entry_id)
    if len(entry.subtasks) == 0:
        format_str = "Unexpected task_id '{}': unable to find subtasks of email for all users task '{}': rejecting task {}"
        msg = format_str.format(current_task_id, entry, new_subtask_status)
        TASK_LOG.warning(msg)
        dog_stats_api.increment('instructor_task.subtask.duplicate.nosubtasks')
        raise DuplicateTaskException(msg)

    # Confirm that the InstructorTask knows about this particular subtask.
    subtask_dict = json.loads(entry.subtasks)
    subtask_status_info = subtask_dict['status']
    if current_task_id not in subtask_status_info:
        format_str = "Unexpected task_id '{}': unable to find status for subtask of email for all users task '{}': rejecting task {}"
        msg = format_str.format(current_task_id, entry, new_subtask_status)
        TASK_LOG.warning(msg)
        dog_stats_api.increment('instructor_task.subtask.duplicate.unknown')
        raise DuplicateTaskException(msg)

    # Confirm that the InstructorTask doesn't think that this subtask has already been
    # performed successfully.
    subtask_status = SubtaskStatus.from_dict(subtask_status_info[current_task_id])
    subtask_state = subtask_status.state
    if subtask_state in READY_STATES:
        format_str = "Unexpected task_id '{}': already completed - status {} for subtask of email for all users task '{}': rejecting task {}"
        msg = format_str.format(current_task_id, subtask_status, entry, new_subtask_status)
        TASK_LOG.warning(msg)
        dog_stats_api.increment('instructor_task.subtask.duplicate.completed')
        raise DuplicateTaskException(msg)

    # Confirm that the InstructorTask doesn't think that this subtask is already being
    # retried by another task.
    if subtask_state == RETRY:
        # Check to see if the input number of retries is less than the recorded number.
        # If so, then this is an earlier version of the task, and a duplicate.
        new_retry_count = new_subtask_status.get_retry_count()
        current_retry_count = subtask_status.get_retry_count()
        if new_retry_count < current_retry_count:
            format_str = "Unexpected task_id '{}': already retried - status {} for subtask of email for all users task '{}': rejecting task {}"
            msg = format_str.format(current_task_id, subtask_status, entry, new_subtask_status)
            TASK_LOG.warning(msg)
            dog_stats_api.increment('instructor_task.subtask.duplicate.retried')
            raise DuplicateTaskException(msg)

    # Now we are ready to start working on this.  Try to lock it.
    # If it fails, then it means that another worker is already in the
    # middle of working on this.
    if not _acquire_subtask_lock(current_task_id):
        format_str = "Unexpected task_id '{}': already being executed - for subtask of email for all users task '{}'"
        msg = format_str.format(current_task_id, entry)
        TASK_LOG.warning(msg)
        dog_stats_api.increment('instructor_task.subtask.duplicate.locked')
        raise DuplicateTaskException(msg)


def _send_all_users_email(entry_id, email_id, to_list, global_email_context, subtask_status):
    """
    Performs the email sending task.

    Sends an email to a list of recipients.

    Inputs are:
      * `entry_id`: id of the InstructorTask object to which progress should be recorded.
      * `email_id`: id of the CourseEmail model that is to be emailed.
      * `to_list`: list of recipients.  Each is represented as a dict with the following keys:
        - 'profile__name': full name of User.
        - 'email': email address of User.
        - 'pk': primary key of User model.
      * `global_email_context`: dict containing values that are unique for this email but the same
        for all recipients of this email.  This dict is to be used to fill in slots in email
        template.  It does not include 'name' and 'email', which will be provided by the to_list.
      * `subtask_status` : object of class SubtaskStatus representing current status.

    Sends to all addresses contained in to_list that are not also in the Optout table.
    Emails are sent multi-part, in both plain text and html.

    Returns a tuple of two values:
      * First value is a SubtaskStatus object which represents current progress at the end of this call.

      * Second value is an exception returned by the innards of the method, indicating a fatal error.
        In this case, the number of recipients that were not sent have already been added to the
        'failed' count above.
    """
    # Get information from current task's request:
    parent_task_id = EmailAllUsersTask.objects.get(pk=entry_id).task_id
    task_id = subtask_status.task_id
    total_recipients = len(to_list)
    recipient_num = 0
    total_recipients_successful = 0
    total_recipients_failed = 0
    recipients_info = Counter()

    log.info(
        "BulkEmail ==> Task: %s, SubTask: %s, EmailId: %s, TotalRecipients: %s",
        parent_task_id,
        task_id,
        email_id,
        total_recipients
    )

    try:
        all_users_email = EmailAllUsers.objects.get(id=email_id)
    except EmailAllUsers.DoesNotExist as exc:
        log.exception(
            "BulkEmail ==> Task: %s, SubTask: %s, EmailId: %s, Could not find email to send.",
            parent_task_id,
            task_id,
            email_id
        )
        raise

    # Esto tiene en cuenta los usuarios que se han borrado de recibir emails de un curso. NO SIRVE PARA ESTE CASO
    # if subtask_status.get_retry_count() == 0:
    #     to_list, num_optout = _filter_optouts_from_recipients(to_list, course_email.course_id)
    #     subtask_status.increment(skipped=num_optout)

    # use the email from address in the CourseEmail, if it is present, otherwise compute it
    from_addr = "%s <%s>" % (settings.BULK_ALL_USERS_EMAIL_FROM_NAME, settings.BULK_EMAIL_DEFAULT_FROM_EMAIL)
    # use the CourseEmailTemplate that was associated with the CourseEmail
    all_users_email_template = all_users_email.get_template()
    try:
        connection = get_connection()
        connection.open()

        # Define context values to use in all course emails:
        email_context = {'name': '', 'email': ''}
        email_context.update(global_email_context)

        while to_list:
            # Update context with user-specific values from the user at the end of the list.
            # At the end of processing this user, they will be popped off of the to_list.
            # That way, the to_list will always contain the recipients remaining to be emailed.
            # This is convenient for retries, which will need to send to those who haven't
            # yet been emailed, but not send to those who have already been sent to.
            recipient_num += 1
            current_recipient = to_list[-1]
            email = current_recipient['email']
            email_context['email'] = email
            email_context['name'] = current_recipient['profile__name']
            email_context['user_id'] = current_recipient['pk']

            # Construct message content using templates and context:
            plaintext_msg = all_users_email_template.render_plaintext(all_users_email.text_message, email_context)
            html_msg = all_users_email_template.render_htmltext(all_users_email.html_message, email_context)

            # Create email:
            email_msg = EmailMultiAlternatives(
                all_users_email.subject,
                plaintext_msg,
                from_addr,
                [email],
                connection=connection
            )
            email_msg.attach_alternative(html_msg, 'text/html')

            # Throttle if we have gotten the rate limiter.  This is not very high-tech,
            # but if a task has been retried for rate-limiting reasons, then we sleep
            # for a period of time between all emails within this task.  Choice of
            # the value depends on the number of workers that might be sending email in
            # parallel, and what the SES throttle rate is.
            if subtask_status.retried_nomax > 0:
                sleep(settings.BULK_EMAIL_RETRY_DELAY_BETWEEN_SENDS)

            try:
                log.info(
                    "BulkEmail ==> Task: %s, SubTask: %s, EmailId: %s, Recipient num: %s/%s, \
                    Recipient name: %s, Email address: %s",
                    parent_task_id,
                    task_id,
                    email_id,
                    recipient_num,
                    total_recipients,
                    current_recipient['profile__name'],
                    email
                )
                # Cuidado
                with dog_stats_api.timer('course_email.single_send.time.overall'):
                    connection.send_messages([email_msg])

            except SMTPDataError as exc:
                # According to SMTP spec, we'll retry error codes in the 4xx range.  5xx range indicates hard failure.
                total_recipients_failed += 1
                log.error(
                    "BulkEmail ==> Status: Failed(SMTPDataError), Task: %s, SubTask: %s, EmailId: %s, \
                    Recipient num: %s/%s, Email address: %s",
                    parent_task_id,
                    task_id,
                    email_id,
                    recipient_num,
                    total_recipients,
                    email
                )
                if exc.smtp_code >= 400 and exc.smtp_code < 500:
                    # This will cause the outer handler to catch the exception and retry the entire task.
                    raise exc
                else:
                    # This will fall through and not retry the message.
                    log.warning(
                        'BulkEmail ==> Task: %s, SubTask: %s, EmailId: %s, Recipient num: %s/%s, \
                        Email not delivered to %s due to error %s',
                        parent_task_id,
                        task_id,
                        email_id,
                        recipient_num,
                        total_recipients,
                        email,
                        exc.smtp_error
                    )
                    # Cuidado
                    dog_stats_api.increment('course_email.error')
                    subtask_status.increment(failed=1)

            except SINGLE_EMAIL_FAILURE_ERRORS as exc:
                # This will fall through and not retry the message.
                total_recipients_failed += 1
                log.error(
                    "BulkEmail ==> Status: Failed(SINGLE_EMAIL_FAILURE_ERRORS), Task: %s, SubTask: %s, \
                    EmailId: %s, Recipient num: %s/%s, Email address: %s, Exception: %s",
                    parent_task_id,
                    task_id,
                    email_id,
                    recipient_num,
                    total_recipients,
                    email,
                    exc
                )
                dog_stats_api.increment('course_email.error')
                subtask_status.increment(failed=1)

            else:
                total_recipients_successful += 1
                log.info(
                    "BulkEmail ==> Status: Success, Task: %s, SubTask: %s, EmailId: %s, \
                    Recipient num: %s/%s, Email address: %s,",
                    parent_task_id,
                    task_id,
                    email_id,
                    recipient_num,
                    total_recipients,
                    email
                )
                # Cuidado
                dog_stats_api.increment('course_email.sent')
                if settings.BULK_EMAIL_LOG_SENT_EMAILS:
                    log.info('Email with id %s sent to %s', email_id, email)
                else:
                    log.debug('Email with id %s sent to %s', email_id, email)
                subtask_status.increment(succeeded=1)

            # Pop the user that was emailed off the end of the list only once they have
            # successfully been processed.  (That way, if there were a failure that
            # needed to be retried, the user is still on the list.)
            recipients_info[email] += 1
            to_list.pop()

        log.info(
            "BulkEmail ==> Task: %s, SubTask: %s, EmailId: %s, Total Successful Recipients: %s/%s, \
            Failed Recipients: %s/%s",
            parent_task_id,
            task_id,
            email_id,
            total_recipients_successful,
            total_recipients,
            total_recipients_failed,
            total_recipients
        )
        duplicate_recipients = ["{0} ({1})".format(email, repetition)
                                for email, repetition in recipients_info.most_common() if repetition > 1]
        if duplicate_recipients:
            log.info(
                "BulkEmail ==> Task: %s, SubTask: %s, EmailId: %s, Total Duplicate Recipients [%s]: [%s]",
                parent_task_id,
                task_id,
                email_id,
                len(duplicate_recipients),
                ', '.join(duplicate_recipients)
            )

    except INFINITE_RETRY_ERRORS as exc:
        # Cuidado
        dog_stats_api.increment('course_email.infinite_retry')
        # Increment the "retried_nomax" counter, update other counters with progress to date,
        # and set the state to RETRY:
        subtask_status.increment(retried_nomax=1, state=RETRY)
        return _submit_for_retry(
            entry_id, email_id, to_list, global_email_context, exc, subtask_status, skip_retry_max=True
        )

    except LIMITED_RETRY_ERRORS as exc:
        # Errors caught here cause the email to be retried.  The entire task is actually retried
        # without popping the current recipient off of the existing list.
        # Errors caught are those that indicate a temporary condition that might succeed on retry.
        dog_stats_api.increment('course_email.limited_retry')
        # Increment the "retried_withmax" counter, update other counters with progress to date,
        # and set the state to RETRY:
        subtask_status.increment(retried_withmax=1, state=RETRY)
        return _submit_for_retry(
            entry_id, email_id, to_list, global_email_context, exc, subtask_status, skip_retry_max=False
        )

    except BULK_EMAIL_FAILURE_ERRORS as exc:
        dog_stats_api.increment('course_email.error')
        num_pending = len(to_list)
        log.exception(('Task %s: email with id %d caused send_course_email task to fail '
                       'with "fatal" exception.  %d emails unsent.'),
                      task_id, email_id, num_pending)
        # Update counters with progress to date, counting unsent emails as failures,
        # and set the state to FAILURE:
        subtask_status.increment(failed=num_pending, state=FAILURE)
        return subtask_status, exc

    except Exception as exc:  # pylint: disable=broad-except
        # Errors caught here cause the email to be retried.  The entire task is actually retried
        # without popping the current recipient off of the existing list.
        # These are unexpected errors.  Since they might be due to a temporary condition that might
        # succeed on retry, we give them a retry.
        # Cuidado
        dog_stats_api.increment('course_email.limited_retry')
        log.exception(('Task %s: email with id %d caused send_course_email task to fail '
                       'with unexpected exception.  Generating retry.'),
                      task_id, email_id)
        # Increment the "retried_withmax" counter, update other counters with progress to date,
        # and set the state to RETRY:
        subtask_status.increment(retried_withmax=1, state=RETRY)
        return _submit_for_retry(
            entry_id, email_id, to_list, global_email_context, exc, subtask_status, skip_retry_max=False
        )

    else:
        # All went well.  Update counters with progress to date,
        # and set the state to SUCCESS:
        subtask_status.increment(state=SUCCESS)
        # Successful completion is marked by an exception value of None.
        return subtask_status, None
    finally:
        # Clean up at the end.
        connection.close()


def update_subtask_status(entry_id, current_task_id, new_subtask_status, retry_count=0):
    try:
        _update_subtask_status(entry_id, current_task_id, new_subtask_status)
    except DatabaseError:
        # If we fail, try again recursively.
        retry_count += 1
        if retry_count < MAX_DATABASE_LOCK_RETRIES:
            TASK_LOG.info("Retrying to update status for subtask %s of email for all users task %d with status %s:  retry %d",
                          current_task_id, entry_id, new_subtask_status, retry_count)
            dog_stats_api.increment('instructor_task.subtask.retry_after_failed_update')
            update_subtask_status(entry_id, current_task_id, new_subtask_status, retry_count)
        else:
            TASK_LOG.info("Failed to update status after %d retries for subtask %s of email for all users task %d with status %s",
                          retry_count, current_task_id, entry_id, new_subtask_status)
            dog_stats_api.increment('instructor_task.subtask.failed_after_update_retries')
            raise
    finally:
        # Only release the lock on the subtask when we're done trying to update it.
        # Note that this will be called each time a recursive call to update_subtask_status()
        # returns.  Fortunately, it's okay to release a lock that has already been released.
        _release_subtask_lock(current_task_id)


@transaction.atomic
def _update_subtask_status(entry_id, current_task_id, new_subtask_status):
    TASK_LOG.info("Preparing to update status for subtask %s for email for all users task %d with status %s",
                  current_task_id, entry_id, new_subtask_status)

    try:
        entry = EmailAllUsersTask.objects.select_for_update().get(pk=entry_id)
        subtask_dict = json.loads(entry.subtasks)
        subtask_status_info = subtask_dict['status']
        if current_task_id not in subtask_status_info:
            # unexpected error -- raise an exception
            format_str = "Unexpected task_id '{}': unable to update status for subtask of email for all users task '{}'"
            msg = format_str.format(current_task_id, entry_id)
            TASK_LOG.warning(msg)
            raise ValueError(msg)

        # Update status:
        subtask_status_info[current_task_id] = new_subtask_status.to_dict()

        task_progress = json.loads(entry.task_output)
        start_time = task_progress['start_time']
        prev_duration = task_progress['duration_ms']
        new_duration = int((time() - start_time) * 1000)
        task_progress['duration_ms'] = max(prev_duration, new_duration)

        new_state = new_subtask_status.state
        if new_subtask_status is not None and new_state in READY_STATES:
            for statname in ['attempted', 'succeeded', 'failed', 'skipped']:
                task_progress[statname] += getattr(new_subtask_status, statname)

        if new_state == SUCCESS:
            subtask_dict['succeeded'] += 1
        elif new_state in READY_STATES:
            subtask_dict['failed'] += 1
        num_remaining = subtask_dict['total'] - subtask_dict['succeeded'] - subtask_dict['failed']

        if num_remaining <= 0:
            entry.task_state = SUCCESS
        entry.subtasks = json.dumps(subtask_dict)
        entry.task_output = EmailAllUsersTask.create_output_for_success(task_progress)

        TASK_LOG.debug("about to save....")
        entry.save()
        TASK_LOG.info("Task output updated to %s for subtask %s of email for all users task %d",
                      entry.task_output, current_task_id, entry_id)
    except Exception:
        TASK_LOG.exception("Unexpected error while updating EmailAllUsersTask.")
        dog_stats_api.increment('instructor_task.subtask.update_exception')
        raise


@ensure_csrf_cookie
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def list_emails_for_all_users_tasks(request):
    """
    List of emails for all users tasks.
    """
    # student = request.GET.get('unique_student_identifier', None)
    # if student is not None:
    #     student = get_student_from_identifier(student)

    tasks = get_running_instructor_tasks()

    response_payload = {
        'tasks': map(extract_task_features, tasks),
    }
    return JsonResponse(response_payload)


def get_running_instructor_tasks():
    """
    Returns a query of EmailAllUsersTask objects of running tasks for a given course.

    Used to generate a list of tasks to display on the instructor dashboard.
    """
    instructor_tasks = EmailAllUsersTask.objects.all()
    # exclude states that are "ready" (i.e. not "running", e.g. failure, success, revoked):
    for state in READY_STATES:
        instructor_tasks = instructor_tasks.exclude(task_state=state)
    return instructor_tasks.order_by('-id')


def extract_task_features(task):
    """
    Convert task to dict for json rendering.
    Expects tasks have the following features:
    * task_type (str, type of task)
    * task_input (dict, input(s) to the task)
    * task_id (str, celery id of the task)
    * requester (str, username who submitted the task)
    * task_state (str, state of task eg PROGRESS, COMPLETED)
    * created (datetime, when the task was completed)
    * task_output (optional)
    """
    # Pull out information from the task
    features = ['task_type', 'task_input', 'task_id', 'requester', 'task_state']
    task_feature_dict = {feature: str(getattr(task, feature)) for feature in features}
    # Some information (created, duration, status, task message) require additional formatting
    task_feature_dict['created'] = task.created.isoformat()

    # Get duration info, if known
    duration_sec = 'unknown'
    if hasattr(task, 'task_output') and task.task_output is not None:
        try:
            task_output = json.loads(task.task_output)
        except ValueError:
            log.error("Could not parse task output as valid json; task output: %s", task.task_output)
        else:
            if 'duration_ms' in task_output:
                duration_sec = int(task_output['duration_ms'] / 1000.0)
    task_feature_dict['duration_sec'] = duration_sec

    # Get progress status message & success information
    success, task_message = get_task_completion_info(task)
    status = _("Complete") if success else _("Incomplete")
    task_feature_dict['status'] = status
    task_feature_dict['task_message'] = task_message

    return task_feature_dict
