from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException


def custom_exception_handler(exc):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc)

    # Now add the HTTP status code to the response.
    if response is not None:
        response.data['status_code'] = response.status_code

    return response


class BadRequest(APIException):
    status_code = 400
    default_detail = 'Bad requests'

class InternalServerError(APIException):
    status_code = 500
    default_detail = 'Internal Server Error'
