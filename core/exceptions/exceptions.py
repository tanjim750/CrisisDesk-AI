from core.responses.codes import ResponseCode


class ApplicationError(Exception):
    code = ResponseCode.INTERNAL_SERVER_ERROR
    status_code = 500
    message_params = None
    errors = None

    def __init__(self, *, message_params=None, errors=None):
        self.message_params = message_params or {}
        self.errors = errors
        super().__init__(self.code)


class ReportNotFoundError(ApplicationError):
    code = ResponseCode.REPORT_NOT_FOUND
    status_code = 404


class InvalidStatusTransitionError(ApplicationError):
    code = ResponseCode.INVALID_STATUS_TRANSITION
    status_code = 400


class AIProcessingError(ApplicationError):
    code = ResponseCode.AI_PROCESSING_FAILED
    status_code = 503
