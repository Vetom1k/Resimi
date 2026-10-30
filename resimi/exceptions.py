"""Exception hierarchy for the Resimi SDK."""


class ResimiError(Exception):
    """Base class for every error raised by the Resimi SDK.

    Raised directly for transport-level failures (DNS, connection refused,
    timeouts) and for invalid arguments caught before a request is sent.
    """


class ResimiAPIError(ResimiError):
    """The API answered, but with an error.

    Attributes:
        code: HTTP status code of the response, or ``None`` when the error was
            raised before a request was made.
        response: The decoded JSON body (usually ``{"error": "..."}``), or the
            raw response text when the body was not valid JSON.
    """

    def __init__(self, message, code=None, response=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.response = response


class ResimiAuthError(ResimiAPIError):
    """The API key is missing, invalid, or not allowed to use the API."""
