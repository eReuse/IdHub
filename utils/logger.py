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
            record.msg = self.highlight_args(record.msg, record.args, color)
            record.args = ()
            
        # provide trace when DEBUG config
        if settings.DEBUG:
            import traceback
            print(traceback.format_exc())

        return super().format(record)

    def highlight_args(self, message, args, color):
        highlighted_args = tuple(f"{color}{arg}{RESET}" for arg in args)
        return message % highlighted_args
