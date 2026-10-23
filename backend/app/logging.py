"""Logging setup. Question and answer text never reach a log (NFR-4), nor do secrets (NFR-6).

The openai client and its HTTP layer log full request bodies, which contain the question,
at DEBUG. They are held at WARNING whatever LOG_LEVEL says. openai 3.x sends through
httpx2/httpcore2; the httpx/httpcore names are kept in case another client uses them.
"""

import logging

QUIET_LOGGERS = ("openai", "httpx", "httpcore", "httpx2", "httpcore2")


def configure_logging(level: str | None) -> None:
    if level:
        logging.basicConfig(level=level.upper())
    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
