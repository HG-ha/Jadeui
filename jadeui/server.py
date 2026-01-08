"""
JadeUI Local Server

Built-in HTTP server for serving web content.
"""

import logging
import ctypes
from typing import Optional

from .core import DLLManager
from .exceptions import ServerError

logger = logging.getLogger(__name__)


class LocalServer:
    """Local HTTP server for serving web content

    Provides a built-in HTTP server that can serve static web content
    to the WebView. Falls back to file:// protocol if server creation fails.

    Example:
        server = LocalServer()
        url = server.start("./web", "myapp")
        print(f"Server running at: {url}")
    """

    def __init__(self, dll_manager: Optional[DLLManager] = None):
        """Initialize local server

        Args:
            dll_manager: DLL manager instance (uses global if None)
        """
        self.dll_manager = dll_manager or DLLManager()
        if not self.dll_manager.is_loaded():
            self.dll_manager.load()

        self._root_path: Optional[str] = None
        self._app_name: Optional[str] = None
        self._url: Optional[str] = None
        self._running = False

    def start(self, root_path: str, app_name: str = "app") -> str:
        """Start the local server

        Args:
            root_path: Root directory to serve files from
            app_name: Application name identifier

        Returns:
            Server URL if successful, file:// URL as fallback

        Raises:
            ServerError: If server creation fails and fallback is not available
        """
        import os

        if not os.path.exists(root_path):
            raise ServerError(f"Root path does not exist: {root_path}")

        self._root_path = os.path.abspath(root_path)
        self._app_name = app_name

        # Try to create local server
        url_buffer = ctypes.create_string_buffer(128)

        result = self.dll_manager.create_local_server(
            self._root_path.encode("utf-8"),
            app_name.encode("utf-8"),
            url_buffer,
            ctypes.sizeof(url_buffer),
        )

        if result == 1:
            self._url = url_buffer.value.decode("utf-8")
            self._running = True
            logger.info(f"Local server started at: {self._url}")
            return self._url
        else:
            # Fallback to file:// protocol
            logger.warning(
                "Local server creation failed, falling back to file:// protocol"
            )
            return self._fallback_url()

    def stop(self) -> None:
        """Stop the local server"""
        # Note: DLL doesn't provide a stop function, server stops with app cleanup
        self._running = False
        self._url = None
        logger.info("Local server stopped")

    def get_url(self, path: str = "index.html") -> str:
        """Get the full URL for a path

        Args:
            path: Relative path to the file

        Returns:
            Full URL to the file
        """
        if self._url and self._running:
            return f"{self._url}/{path}"
        else:
            # Fallback URL
            return self._fallback_url(path)

    def _fallback_url(self, path: str = "index.html") -> str:
        """Generate fallback file:// URL

        Args:
            path: Relative path to the file

        Returns:
            file:// URL
        """
        import os

        if self._root_path:
            file_path = os.path.join(self._root_path, path)
            abs_path = os.path.abspath(file_path)
            # Convert backslashes to forward slashes for file:// URL
            url_path = abs_path.replace(os.sep, "/")
            return f"file:///{url_path}"
        else:
            raise ServerError("No root path set for fallback URL")

    @property
    def is_running(self) -> bool:
        """Check if server is running"""
        return self._running

    @property
    def url(self) -> Optional[str]:
        """Get the server URL"""
        return self._url

    def __repr__(self) -> str:
        status = "running" if self._running else "stopped"
        return f"LocalServer(status={status}, url={self._url})"
