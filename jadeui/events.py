"""
JadeUI Event System

Centralized event system for handling window events, app events, and custom events.
"""

import ctypes
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from .core import DLLManager

logger = logging.getLogger(__name__)


class EventEmitter:
    """Centralized event emitter for JadeUI

    Provides a flexible event system with support for:
    - Multiple listeners per event
    - One-time listeners (once)
    - Listener removal
    - Event chaining with decorators

    Example:
        emitter = EventEmitter()

        @emitter.on('my-event')
        def handler(data):
            print(f"Received: {data}")

        emitter.emit('my-event', 'Hello!')
    """

    def __init__(self):
        self._listeners: Dict[str, List[Callable[..., Any]]] = defaultdict(list)
        self._once_listeners: set[Callable[..., Any]] = set()

    def on(self, event: str, callback: Optional[Callable[..., Any]] = None) -> Callable[..., Any]:
        """Register an event listener

        Can be used as a method or decorator:

        As method:
            emitter.on('event', callback)

        As decorator:
            @emitter.on('event')
            def callback():
                pass

        Args:
            event: Event name to listen for
            callback: Function to call when event is emitted

        Returns:
            The callback function (for decorator usage)
        """
        if callback is None:
            # Used as decorator
            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                self._listeners[event].append(fn)
                logger.debug(f"Registered listener for event: {event}")
                return fn

            return decorator
        else:
            # Used as method
            self._listeners[event].append(callback)
            logger.debug(f"Registered listener for event: {event}")
            return callback

    def off(self, event: str, callback: Optional[Callable[..., Any]] = None) -> None:
        """Remove an event listener

        Args:
            event: Event name
            callback: The callback function to remove.
                     If None, removes all listeners for the event.
        """
        if callback is None:
            # Remove all listeners for this event
            if event in self._listeners:
                self._listeners[event].clear()
                logger.debug(f"Removed all listeners for event: {event}")
        else:
            # Remove specific listener
            if callback in self._listeners[event]:
                self._listeners[event].remove(callback)
                self._once_listeners.discard(callback)
                logger.debug(f"Removed listener for event: {event}")

    def emit(self, event: str, *args: Any, **kwargs: Any) -> bool:
        """Emit an event to all registered listeners

        Args:
            event: Event name
            *args: Positional arguments to pass to listeners
            **kwargs: Keyword arguments to pass to listeners

        Returns:
            True if any listeners were called
        """
        if event not in self._listeners or not self._listeners[event]:
            return False

        listeners_called = False
        # Copy list to avoid modification during iteration
        for callback in list(self._listeners[event]):
            try:
                callback(*args, **kwargs)
                listeners_called = True

                # Remove if it was a once listener
                if callback in self._once_listeners:
                    self._listeners[event].remove(callback)
                    self._once_listeners.discard(callback)
            except Exception as e:
                logger.error(f"Error in {event} callback: {e}")

        return listeners_called

    def once(self, event: str, callback: Optional[Callable[..., Any]] = None) -> Callable[..., Any]:
        """Register a one-time event listener

        The listener will be removed after the first event emission.

        Args:
            event: Event name
            callback: Function to call once when event is emitted

        Returns:
            The callback function (for decorator usage)
        """
        if callback is None:
            # Used as decorator
            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                self._listeners[event].append(fn)
                self._once_listeners.add(fn)
                logger.debug(f"Registered one-time listener for event: {event}")
                return fn

            return decorator
        else:
            # Used as method
            self._listeners[event].append(callback)
            self._once_listeners.add(callback)
            logger.debug(f"Registered one-time listener for event: {event}")
            return callback

    def remove_all_listeners(self, event: Optional[str] = None) -> None:
        """Remove all listeners for an event or all events

        Args:
            event: Specific event to clear listeners for, or None for all events
        """
        if event:
            self._listeners[event].clear()
            logger.debug(f"Cleared all listeners for event: {event}")
        else:
            self._listeners.clear()
            self._once_listeners.clear()
            logger.debug("Cleared all event listeners")

    def listener_count(self, event: str) -> int:
        """Get the number of listeners for an event

        Args:
            event: Event name

        Returns:
            Number of registered listeners
        """
        return len(self._listeners[event])

    def event_names(self) -> list[str]:
        """Get all event names with registered listeners

        Returns:
            List of event names
        """
        return [name for name, listeners in self._listeners.items() if listeners]

    def has_listeners(self, event: str) -> bool:
        """Check if an event has any listeners

        Args:
            event: Event name

        Returns:
            True if event has listeners
        """
        return bool(self._listeners[event])


class GlobalEventManager:
    """Manager for DLL-level global events

    Handles registration and management of global events with the JadeView DLL,
    such as 'app-ready', 'window-all-closed', etc.
    """

    def __init__(self, dll_manager: "DLLManager"):
        self.dll_manager = dll_manager
        self._callbacks: Dict[str, Any] = {}  # Store ctypes callbacks

    def register(self, event: str, callback: Callable) -> None:
        """Register a global event handler with the DLL

        Args:
            event: Event name (e.g., 'app-ready', 'window-all-closed')
            callback: ctypes callback function
        """
        # Store reference to prevent garbage collection
        self._callbacks[event] = callback

        # Register with DLL
        self.dll_manager.jade_on(
            event.encode("utf-8"),
            ctypes.cast(callback, ctypes.c_void_p),
        )
        logger.info(f"Registered global event: {event}")

    def unregister(self, event: str) -> None:
        """Unregister a global event handler

        Args:
            event: Event name
        """
        if event in self._callbacks:
            self.dll_manager.jade_off(event.encode("utf-8"))
            del self._callbacks[event]
            logger.info(f"Unregistered global event: {event}")

    def list_events(self) -> list[str]:
        """Get list of registered global events

        Returns:
            List of event names
        """
        return list(self._callbacks.keys())


# Standard event names
class Events:
    """Standard event name constants"""

    # App lifecycle events
    APP_READY = "app-ready"
    WINDOW_ALL_CLOSED = "window-all-closed"
    BEFORE_QUIT = "before-quit"

    # Window events
    WINDOW_CREATED = "window-created"
    WINDOW_CLOSED = "window-closed"
    WINDOW_FOCUS = "window-focus"
    WINDOW_BLUR = "window-blur"
    WINDOW_RESIZE = "window-resize"
    WINDOW_MOVE = "window-move"
    WINDOW_MAXIMIZE = "window-maximize"
    WINDOW_MINIMIZE = "window-minimize"
    WINDOW_RESTORE = "window-restore"

    # Page events
    PAGE_LOADED = "page-loaded"
    PAGE_LOADING = "page-loading"
    PAGE_ERROR = "page-error"

    # File events
    FILE_DROP = "file-drop"
    FILE_DROP_HOVER = "file-drop-hover"
    FILE_DROP_CANCELLED = "file-drop-cancelled"

    # IPC events
    IPC_MESSAGE = "ipc-message"
