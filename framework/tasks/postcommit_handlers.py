
import logging

logger = logging.getLevelName(__name__)

def postcommit_after_request(response):
    logger.error('Starting postcommit after request')
    import time
    now = time.time()
    with open('/Users/chriswisecarver/Desktop/ZZZZZ{}.txt'.format(now), 'w') as f:
        f.write(str(response))
    logger.error('Finishing postcommit after request')
    return response

handlers = {
    'after_request': postcommit_after_request,
}
