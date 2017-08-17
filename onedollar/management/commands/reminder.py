# -*- encoding: utf8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from onedollar.models import *

class Command(BaseCommand):
    help = 'If users haven’t used all their Free $ after 7 days, we send a reminder email.'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        users = OneDollarUser.objects.get_users_not_use_free_dollar()

        for user in users:
            if user.email:
                self.stdout.write('\nProcessing user %d - "%s"' % (user.id, user.get_full_name()))

                subject = 'OneDollar - You still have Free $ waiting for you in the app'
                html_content = render_to_string('email/reminder.html', {'name': user.get_full_name()})
                tasks.send_email(subject, html_content, [user.email])
            else:
                self.stdout.write('\nSkipping user %d - "%s"' % (user.id, user.get_full_name()))

