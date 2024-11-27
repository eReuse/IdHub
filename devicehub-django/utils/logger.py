import logging
from django.conf import settings

# Colors
RED = "\033[91m"
PURPLE = "\033[95m"
YELLOW = "\033[93m"
RESET = "\033[0m"


class CustomFormatter(logging.Formatter):
    def format(self, record):
        if record.levelname == "ERROR":
            color = RED
        elif record.levelname == "WARNING":
            color = YELLOW
        elif record.levelname in ["INFO", "DEBUG"]:
            color = PURPLE
        else:
            color = RESET

        record.levelname = f"{color}{record.levelname}{RESET}"

        if record.args:
            try:
                record.msg = record.msg % record.args
                record.args = ()
            except (TypeError, ValueError):
                record.msg = f"{color}{record.msg}{RESET}"

        # Highlight the final formatted message
        record.msg = self.highlight_message(record.msg, color)

        # provide trace when DEBUG config
        if settings.DEBUG:
            import traceback
            print(traceback.format_exc())

        return super().format(record)

    def highlight_message(self, message, color):
        return f"{color}{message}{RESET}"
