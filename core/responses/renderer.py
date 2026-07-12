from core.constants.languages import DEFAULT_RESPONSE_LANGUAGE, SUPPORTED_RESPONSE_LANGUAGES
from core.responses.messages import get_message

try:
    from rest_framework.response import Response
except ImportError:
    Response = None


def resolve_response_language(request=None) -> str:
    if request is None:
        return DEFAULT_RESPONSE_LANGUAGE

    header_language = resolve_accept_language_header(request)
    if header_language:
        return header_language

    query_params = getattr(request, "query_params", {})
    query_language = query_params.get("lang") if query_params else None
    if query_language in SUPPORTED_RESPONSE_LANGUAGES:
        return query_language

    return DEFAULT_RESPONSE_LANGUAGE


def resolve_accept_language_header(request) -> str | None:
    headers = getattr(request, "headers", {})
    accept_language = headers.get("Accept-Language", "") if headers else ""
    language_preferences = []

    for index, language_range in enumerate(accept_language.split(",")):
        language_parts = language_range.strip().split(";")
        language = language_parts[0].split("-")[0].strip().lower()
        quality = 1.0

        for parameter in language_parts[1:]:
            key, _, value = parameter.strip().partition("=")
            if key == "q":
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0

        if language in SUPPORTED_RESPONSE_LANGUAGES:
            language_preferences.append((quality, index, language))

    if language_preferences:
        language_preferences.sort(key=lambda item: (-item[0], item[1]))
        return language_preferences[0][2]

    return None


def render_response(*, success, code, message, status_code, data=None, errors=None, meta=None):
    payload = {
        "success": success,
        "code": code,
        "message": message,
        "data": data,
        "errors": errors,
        "meta": meta,
    }

    if Response is None:
        return payload

    return Response(payload, status=status_code)


def success_response(*, request=None, code, status_code=200, data=None, meta=None, **message_params):
    language = resolve_response_language(request)
    message = get_message(code, language=language, **message_params)

    return render_response(
        success=True,
        code=code,
        message=message,
        status_code=status_code,
        data=data if data is not None else {},
        errors=None,
        meta=meta,
    )


def error_response(*, request=None, code, status_code=400, errors=None, data=None, **message_params):
    language = resolve_response_language(request)
    message = get_message(code, language=language, **message_params)

    return render_response(
        success=False,
        code=code,
        message=message,
        status_code=status_code,
        data=data,
        errors=errors if errors is not None else {},
        meta=None,
    )


def paginated_response(*, request=None, code, data, pagination, status_code=200, **message_params):
    meta = {
        "count": getattr(pagination, "count", None),
        "page": getattr(pagination, "page", None),
        "pageSize": getattr(pagination, "page_size", None),
    }

    return success_response(
        request=request,
        code=code,
        status_code=status_code,
        data=data,
        meta=meta,
        **message_params,
    )
