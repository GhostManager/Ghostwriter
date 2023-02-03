"""This contains all of the custom exceptions for the Ghostwriter application."""


class MissingTemplate(Exception):
    """
    Exception raised when a report template is missing for a report.

    **Attributes**

    ``message``
        Error message to be displayed
    """

    def __init__(self, message="No report template selected"):
        self.message = message
        super().__init__(self.message)


class InvalidFilterValue(Exception):
    """
    Exception raised when an invalid value is passed to a report template filter.

    **Attributes**

    ``message``
        Error message to be displayed
    """

    def __init__(self, message="Invalid value provided to filter"):
        self.message = message
        super().__init__(self.message)
