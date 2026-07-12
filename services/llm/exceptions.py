class LLMError(Exception):
    pass


class LLMTimeoutError(LLMError):
    pass


class LLMRateLimitError(LLMError):
    pass


class LLMInvalidOutputError(LLMError):
    pass


class LLMProviderUnavailableError(LLMError):
    pass
