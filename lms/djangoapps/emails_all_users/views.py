from edxmako.shortcuts import render_to_response
from django.contrib.admin.views.decorators import staff_member_required
from django.core.context_processors import csrf
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

from .forms import EmailForm
from .api import send_email


@staff_member_required
def emails_all_users(request):

    data = None
    if request.method == 'POST':
        data = request.POST
    form = EmailForm(data=data)
    if form.is_valid():
        send_email(request)
        # messages.success(request, 'Su email ha sido guardado satisfactoriamente')
        return HttpResponseRedirect(reverse('emails_all_users'))
    csrf_token = csrf(request)['csrf_token']
    return render_to_response('email_all_users_dashboard.html',
                              {'form': form,
                               'csrf': csrf_token})

