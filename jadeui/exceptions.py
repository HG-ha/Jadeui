"""
JadeUI SDK Exceptions

Custom exception classes for JadeUI operations.
"""


class JadeUIError(Exception):
    """Base exception for all JadeUI errors"""

    pass


class DLLLoadError(JadeUIError):
    """Failed to load JadeView DLL"""

    pass


class WindowCreationError(JadeUIError):
    """Failed to create window"""

    pass


class IPCError(JadeUIError):
    """IPC communication error"""

    pass


class ServerError(JadeUIError):
    """Local server error"""

    pass


class InitializationError(JadeUIError):
    """SDK initialization error"""

    pass
