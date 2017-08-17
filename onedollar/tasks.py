import json, httplib, os, requests

from email.MIMEImage import MIMEImage

from django.conf import settings
from django.core import mail

def send_pushnotifs(channels, message, auto_increment=True):
    print '>>> task send_pushnotifs running with channels "{}" and message "{}"'.format(channels, message)

    from onedollar.models import OneDollarUserToken

    url = "https://fcm.googleapis.com/fcm/send"

    tokens = list(OneDollarUserToken.get_tokens_of_users(channels))

    data = dict(message)
    message['title'] = 'One Dollar'
    message['click_action'] = 'ACTION_CLICK_NOTIFY'

    push_data = json.dumps({
        "registration_ids": tokens,
        "notification": message,
        "data": data,
    })

    headers = {
        'content-type': "application/json",
        'authorization': "key=AIzaSyC_wnchqs8pio0IeWDqoGcI1v6zLONFais",
        'project_id': "26835176988",
    }

    response = requests.request("POST", url, data=push_data, headers=headers)

def send_pushnotifs1(channels, message, auto_increment=True):
    print '>>> task send_pushnotifs running with channels "{}" and message "{}"'.format(channels, message)

    connection = httplib.HTTPSConnection('api.parse.com', 443)
    connection.connect()

    try:
        message.setdefault("action", "com.nng.onedollar")
        if auto_increment:
            message.setdefault("badge", "Increment")
    except:
        pass

    push_data = json.dumps({
        "channels": list(channels),
        "data": message,
    })

    connection.request('POST', '/1/push', push_data, {
        "X-Parse-Application-Id": settings.PARSE_APPLICATION_ID,
        "X-Parse-REST-API-Key": settings.PARSE_REST_API_KEY,
        "Content-Type": "application/json"
    })

    result = json.loads(connection.getresponse().read())

    if result and result['result']:
        return result.get('result', False)

    return False


def send_email(subject, html_content, emails, from_email=None):
    if from_email is None:
        from_email = settings.EMAIL_FROM

    msg = mail.EmailMessage(subject, html_content, from_email, emails)
    msg.content_subtype = "html"  # Main content is now text/html
    msg.mixed_subtype = 'related'
    fp = open(os.path.join(settings.BASE_DIR, 'emailheader.png'))
    msg_img = MIMEImage(fp.read())
    fp.close()
    msg_img.add_header('Content-ID', '<emailheader.png>')
    msg.attach(msg_img)

    msg.send()

def send_sms(phone,code):
    connection = httplib.HTTPSConnection('api.smsapi.com', 443)
    connection.connect()
    url = '/sms.do?username=gpanot@giinger.com&password=ceac99e637c6ecb1e64740355e65f416&encoding=utf-8&to=%s&message=%s' %(phone,code)
    connection.request('GET', url)
    result = connection.getresponse().read()
    return True

def refund_paypal(transaction_id):
    url = "https://api-3t.sandbox.paypal.com/nvp"
    # url = " https://api-3t.paypal.com/nvp" #live

    push_data = {
        "USER": 'hhh+merchant_api1.nng.bz',
        "PWD": 'Q8D42RQ4983CQK8P',
        "SIGNATURE": 'AFcWxV21C7fd0v3bYYYRCpSSRl31AurlRYgTvul7Pvoq-MLEnIAuAkdq',
        "METHOD": 'RefundTransaction',
        "VERSION": 94,
        "TRANSACTIONID": transaction_id,
        "REFUNDTYPE" : 'Full'
    }

    headers = {}

    response = requests.request("POST", url, data=push_data, headers=headers)

    print response

# def payment_paypal(transaction_id):
#     url = "https://api-3t.sandbox.paypal.com/nvp"
#     # url = " https://api-3t.paypal.com/nvp" #live

#     push_data = {
#         "USER": 'hhh+merchant_api1.nng.bz',
#         "PWD": 'Q8D42RQ4983CQK8P',
#         "SIGNATURE": 'AFcWxV21C7fd0v3bYYYRCpSSRl31AurlRYgTvul7Pvoq-MLEnIAuAkdq',
#         "METHOD": 'RefundTransaction',
#         "VERSION": 94,
#         "TRANSACTIONID": transaction_id,
#         "REFUNDTYPE" : 'Full'
#     }

#     headers = {}

#     response = requests.request("POST", url, data=push_data, headers=headers)

#     print response
