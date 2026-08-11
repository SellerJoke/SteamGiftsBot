from rich.console import Console

# noinspection PyProtectedMember
from src.requests.non_browser_client import _NON_BROWSER_CLIENT, NonBrowserClient
from src.util.avoid_circle_import import _CONSOLE

CONSOLE: Console = _CONSOLE
NON_BROWSER_CLIENT: NonBrowserClient = _NON_BROWSER_CLIENT
