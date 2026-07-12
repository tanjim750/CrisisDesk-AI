from core.exceptions.exceptions import ApplicationError
from core.responses.codes import ResponseCode
from core.responses.renderer import error_response

try:
    from django.core.exceptions import PermissionDenied
    from django.http import Http404
    from rest_framework import exceptions, status
    from rest_framework.views import exception_handler
except ImportError:
    PermissionDenied = None
    Http404 = None
    exceptions = None
    status = None
    exception_handler = None


def custom_exception_handler(exc, context):
    request = context.get("request") if context else None

    if isinstance(exc, ApplicationError):
        return error_response(
            request=request,
            code=exc.code,
            status_code=exc.status_code,
            errors=exc.errors,
            **exc.message_params,
        )

    if exception_handler is None:
        raise exc

    drf_response = exception_handler(exc, context)

    if drf_response is None:
        if Http404 is not None and isinstance(exc, Http404):
            return error_response(
                request=request,
                code=ResponseCode.REPORT_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if PermissionDenied is not None and isinstance(exc, PermissionDenied):
            return error_response(
                request=request,
                code=ResponseCode.PERMISSION_DENIED,
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return error_response(
            request=request,
            code=ResponseCode.INTERNAL_SERVER_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if exceptions is not None and isinstance(exc, exceptions.ValidationError):
        return error_response(
            request=request,
            code=ResponseCode.VALIDATION_ERROR,
            status_code=drf_response.status_code,
            errors=drf_response.data,
        )

    if exceptions is not None and isinstance(exc, exceptions.NotAuthenticated):
        return error_response(
            request=request,
            code=ResponseCode.AUTHENTICATION_REQUIRED,
            status_code=drf_response.status_code,
            errors=drf_response.data,
        )

    if exceptions is not None and isinstance(exc, exceptions.PermissionDenied):
        return error_response(
            request=request,
            code=ResponseCode.PERMISSION_DENIED,
            status_code=drf_response.status_code,
            errors=drf_response.data,
        )

    return error_response(
        request=request,
        code=ResponseCode.INTERNAL_SERVER_ERROR,
        status_code=drf_response.status_code,
        errors=drf_response.data,
    )
