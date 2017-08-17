from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from onedollar.models import *

class Command(BaseCommand):
    help = 'Check for all due products and draw the winner'

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)

    def handle(self, *args, **options):
        products = Product.get_due_products()
        print 'Found %d products due' % len(products)

        for product in products:
            self.stdout.write('\nProcessing product %d - "%s"' % (product.id, product.title))

            bet = product.draw_winners()

            if bet is None:
                self.stderr.write(' !! No bet on the product. Cannot draw the winner!')
            else:
                self.stdout.write(' => Winner %s (ID: %d) with winner number %d' % 
                        (bet.user.get_full_name(), bet.user_id, bet.number))

