This is the main edX platform which consists of LMS and Studio.


Installation
------------

You need a fullstack dogwood instance of Open edX to install this repo.

1. Log in with edxapp user
::
   
   sudo -H -u edxapp bash
   cd /edx/app/edxapp

2. Activate virtualenv
::
   
   source edxapp_env

3. Backup of the current edx-platform repo
::

   mv edx-platform/ edx-platform-default/
4. Clone this repo in edx-platform
::
   git clone https://github.com/BeDjango/intef-openedx edx-platform/
5. Override the next variables in your lms.env.json file
::

   "REGISTRATION_EXTRA_FIELDS": {
      "city": "optional",
      "country": "required",
      "gender": "hidden",
      "goals": "hidden",
      "honor_code": "required",
      "level_of_education": "optional",
      "mailing_address": "hidden",
      "year_of_birth": "optional",
      "comuni": "required",
      "esdoce": "required",
      "camp1": "optional",
      "camp2": "optional",
      "camp3": "optional",
      "camp4": "optional",
      "camp5": "optional"
   },

::

   "ENABLE_COMBINED_LOGIN_REGISTRATION": false,
6. Install node nodules
::
   cd edx-platform/
   npm install

7. Update the database model
::
   paver update_db
8. Update assets
::
   paver update_assets lms --settings=aws
   paver update_assets cms --settings=aws
9. Restart all services
::
   exit
   sudo /edx/bin/supervisorctl restart all
   sudo service nginx restart



License
-------

The code in this repository is licensed under version 3 of the AGPL
unless otherwise noted. Please see the `LICENSE`_ file for details.

.. _LICENSE: https://github.com/edx/edx-platform/blob/master/LICENSE


The Open edX Portal
---------------------

See the `Open edX Portal`_ to learn more about Open edX. You can find
information about the edX roadmap, as well as about hosting, extending, and
contributing to Open edX. In addition, the Open edX Portal provides product
announcements, the Open edX blog, and other rich community resources.

To comment on blog posts or the edX roadmap, you must create an account and log
in. If you do not have an account, follow these steps.

#. Visit `open.edx.org/user/register`_.
#. Fill in your personal details.
#. Select **Create New Account**. You are then logged in to the `Open edX
   Portal`_.

.. _Open edX Portal: https://open.edx.org
.. _open.edx.org/user/register: https://open.edx.org/user/register

Documentation
-------------

Documentation is managed in the `edx-documentation`_ repository. Documentation
is built using `Sphinx`_: you can `view the built documentation on
ReadTheDocs`_.

You can also check out `Confluence`_, our wiki system. Once you sign up for
an account, you'll be able to create new pages and edit existing pages, just
like in any other wiki system. You only need one account for both Confluence
and `JIRA`_, our issue tracker.

.. _Sphinx: http://sphinx-doc.org/
.. _view the built documentation on ReadTheDocs: http://docs.edx.org/
.. _edx-documentation: https://github.com/edx/edx-documentation
.. _Confluence: http://openedx.atlassian.net/wiki/
.. _JIRA: https://openedx.atlassian.net/


Getting Help
------------

If you’re having trouble, we have several different mailing lists where
you can ask for help:

-  `openedx-ops`_: everything related to *running* Open edX. This
   includes installation issues, server management, cost analysis, and
   so on.
-  `openedx-translation`_: everything related to *translating* Open edX
   into other languages. This includes volunteer translators, our
   internationalization infrastructure, issues related to Transifex, and
   so on.
-  `openedx-analytics`_: everything related to *analytics* in Open edX.
-  `edx-code`_: anything else related to Open edX. This includes feature
   requests, idea proposals, refactorings, and so on.

You can also join our IRC channel: `#edx-code on Freenode`_.

.. _openedx-ops: https://groups.google.com/forum/#!forum/openedx-ops
.. _openedx-translation: https://groups.google.com/forum/#!forum/openedx-translation
.. _openedx-analytics: https://groups.google.com/forum/#!forum/openedx-analytics
.. _edx-code: https://groups.google.com/forum/#!forum/edx-code
.. _#edx-code on Freenode: http://webchat.freenode.net/?channels=edx-code


Issue Tracker
-------------

`We use JIRA for our issue tracker`_, not GitHub Issues. To file a bug
or request a new feature, please make a free account on our JIRA and
create a new issue! If you’re filing a bug, we’d appreciate it if you
would follow `our guidelines for filing high-quality, actionable bug
reports`_. Thanks!

.. _We use JIRA for our issue tracker: https://openedx.atlassian.net/
.. _our guidelines for filing high-quality, actionable bug reports: https://openedx.atlassian.net/wiki/display/SUST/How+to+File+a+Quality+Bug+Report


How to Contribute
-----------------

Contributions are very welcome, but for legal reasons, you must submit a
signed `individual contributor’s agreement`_ before we can accept your
contribution. See our `CONTRIBUTING`_ file for more information – it
also contains guidelines for how to maintain high code quality, which
will make your contribution more likely to be accepted.


Reporting Security Issues
-------------------------

Please do not report security issues in public. Please email
security@edx.org

.. _individual contributor’s agreement: http://open.edx.org/sites/default/files/wysiwyg/individual-contributor-agreement.pdf
.. _CONTRIBUTING: https://github.com/edx/edx-platform/blob/master/CONTRIBUTING.rst
