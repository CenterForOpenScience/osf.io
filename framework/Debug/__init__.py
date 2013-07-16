import logging; 
logging.basicConfig(level=logging.DEBUG); 

def loggerDebug(label, message):
    logger = logging.getLogger(label)
    logger.debug(message)