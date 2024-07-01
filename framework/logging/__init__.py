import colorlog
from logging import Formatter, StreamHandler, getLogger
from website import settings

handler = StreamHandler()

if settings.DEBUG_MODE and settings.USE_COLOR:
    log_colors = colorlog.default_log_colors.copy()
    log_colors['DEBUG'] = 'cyan'

    formatter = colorlog.ColoredFormatter(
        '%(log_color)s[%(name)s]  %(levelname)s:%(reset)s %(message)s',
        reset=True,
        log_colors=log_colors,
    )
else:
    formatter = Formatter(
        '[%(name)s]  %(levelname)s: %(message)s',
    )

handler.setFormatter(formatter)

logger = getLogger()
logger.addHandler(handler)
logger.setLevel(settings.LOG_LEVEL)
