# -*- encoding: utf8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.core.urlresolvers import set_script_prefix
from django.conf import settings

from onedollar.models import *

class Command(BaseCommand):
    help = 'Every 5 days sent an email to aftersales@onedollarapp.biz (product delivery status = ‘’PENDING’’ (address is filled))'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        products = SoldProduct.get_pending_products()

        self.stdout.write('\n%d pending products found' % (len(products),))
        if products:
            subject = 'Pending for delivery'
            html_content = render_to_string('email/reminder_pending_products.html', {
                'SITE_URL': settings.SITE_URL[:-1], 'products': products, 'products_count': len(products)})
            tasks.send_email(subject, html_content, ['aftersales@onedollarapp.biz',])

