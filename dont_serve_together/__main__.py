"""Application entry point.

Defines :func:`main`, the ``dont_serve_together`` console-script target and
what runs on ``python -m dont_serve_together``.
"""

from dont_serve_together.ui import DontServeTogetherApp


def main() -> None:
    """Run the application."""
    DontServeTogetherApp().run()


if __name__ == "__main__":
    main()
