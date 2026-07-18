"""Application entry point.

Defines :func:`main`, the ``dont_serve_together`` console-script target and
what runs on ``python -m dont_serve_together``.
"""

import contextlib
import locale

from dont_serve_together.ui import DontServeTogetherApp


def main() -> None:
    """Run the application."""
    # Python starts in the C locale; adopt the user's OS time formats so
    # displayed timestamps (e.g. Last loaded) match their regional settings.
    with contextlib.suppress(locale.Error):
        locale.setlocale(locale.LC_TIME, "")
    DontServeTogetherApp().run()


if __name__ == "__main__":
    main()
