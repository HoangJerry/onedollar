from django_redis import get_redis_connection

import paypalrestsdk, stripe

from paypalrestsdk import Payout, ResourceNotFound, PayoutItem
import random
import string
import logging

class PayPalPayment:
    def __init__(self, *args, **kwargs):
        mode = kwargs.get('mode', None)
        client_id = kwargs.get('client_id', None)
        client_secret = kwargs.get('client_secret', None)

        if not mode or not client_id or not client_secret:
            raise Exception('Invalid PayPal configuration')

        paypalrestsdk.configure({
            "mode": mode, 
            "client_id": client_id, 
            "client_secret": client_secret,
        })

    def verify_receipt(self, paypal_id):
        receipt = paypalrestsdk.Payment.find(paypal_id)
        receipt_data = receipt.to_dict()

        if receipt_data['state'] == 'approved':
            transaction = receipt_data['transactions'][0]
            if transaction:
                related_resource = transaction['related_resources'][0]
                if related_resource and related_resource['sale']['state'] == 'completed':
                    return receipt_data

        raise Exception('Invalid receipt')

    def pay_for_merchant(self,Item):
        sender_batch_id = ''.join(
            random.choice(string.ascii_uppercase) for i in range(12))

        payout = Payout({
            "sender_batch_header": {
                "sender_batch_id": sender_batch_id,
                "email_subject": "You have a payment"
            },
            "items": Item
        })

        if payout.create():
            print("payout[%s] created successfully" %
                  (payout.batch_header.payout_batch_id))

            logging.basicConfig(level=logging.INFO)
            try:
                payout_batch = Payout.find(payout.batch_header.payout_batch_id)
                return payout_batch.items[0].payout_item_id

            except ResourceNotFound as error:
                print("Web Profile Not Found")

            return 1
        else:
            print(payout.error)
            return 0

    def decode_transaction(self,payout_item_id):
        logging.basicConfig(level=logging.INFO)

        try:
            payout_item = PayoutItem.find(payout_item_id)
            return payout_item.transaction_id

        except ResourceNotFound as error:
            print("Payout Item Not Found")

class StripePayment:
    class StripePaymentException(Exception):
        pass

    def charge(self, *args, **kwargs):
        try:
            token = kwargs.get('token', None)
            amount = kwargs.get('amount', None)
            currency = kwargs.get('currency', None)

            if not token or not amount or not currency:
                raise Exception('Invalid Stripe params')

            charge = stripe.Charge.create(
                source=token,
                amount=amount,
                currency=currency
            )

            if charge.status == u'succeeded' and charge.amount == amount \
                and charge.currency == currency.lower() and charge.paid == True:
                return charge
        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            body = e.json_body
            err  = body['error']

            key = '{} - {} - {}'.format(err['type'], err['code'], err['message'])

            r = get_redis_connection()

            r.hincrby(settings.REDISKEYS_STRIPE_ERR, key+'##count', 1)
            r.hincrby(settings.REDISKEYS_STRIPE_ERR, key+'##total', amount)

            raise StripePayment.StripePaymentException()
        except stripe.error.RateLimitError as e:
            raise StripePayment.StripePaymentException()
        except stripe.error.InvalidRequestError as e:
            raise StripePayment.StripePaymentException()
        except stripe.error.AuthenticationError as e:
            raise StripePayment.StripePaymentException()
        except stripe.error.APIConnectionError as e:
            raise StripePayment.StripePaymentException()
        except stripe.error.StripeError as e:
            raise StripePayment.StripePaymentException()
        except Exception as e:
            raise e

        raise Exception('Stripe charge operation failed')

