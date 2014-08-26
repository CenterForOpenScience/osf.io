import logging
import logging.config

try:
    import colorlog
    use_color = True
except ImportError:
    use_color = False

from website import settings

handler = logging.StreamHandler()

if settings.DEBUG_MODE and use_color:
    log_colors = colorlog.default_log_colors
    log_colors['DEBUG'] = 'cyan'

    formatter = colorlog.ColoredFormatter(
        '%(log_color)s[%(name)s]  %(levelname)s:%(reset)s %(message)s',
        reset=True,
        log_colors=log_colors,
    )
else:
    formatter = logging.Formatter(
        '[%(name)s]  %(levelname)s: %(message)s',
    )

handler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)