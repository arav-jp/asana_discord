import traceback
import time
import logging

import asana
from raven import Client
from raven.conf import setup_logging
from raven.handlers.logging import SentryHandler


logger = None

def access_asana(asana_token):
    try:
        asana_connection = asana.Client.access_token(asana_token)
        if asana_connection.session.authorized:
            logger.info('Asana access token authorized')
            return asana_connection

        else:
            logger.error('Asana failed to authenticate access token: %s', asana_token)
            return False

    except Exception:
        print(traceback.format_exc())
        return False

class DummyLogger():
    def __init__(self):
        pass

    def info(self, msg):
        print("[INFO] {}".format(msg))

    def log(self, msg):
        print("[LOG] {}".format(msg))

    def debug(self, msg):
        print("[DEBUG] {}".format(msg))

    def warn(self, msg):
        print("[WARN] {}".format(msg))

    def warning(self, msg):
        print("[WARN] {}".format(msg))

    def error(self, msg):
        print("[ERR] {}".format(msg))

def logger_pick(mode, sentry_url):
    """ Load the logger for the bot. """
    global logger

    if mode != "production":
        logger = DummyLogger()
        return logger

    client = Client(sentry_url)
    handler = SentryHandler(client)
    handler.setLevel(logging.DEBUG)
    setup_logging(handler)
    logger = logging.getLogger(__name__)
    return logger

def retry_wrapper(target, target_type, **kwargs):
    try:
        if target_type == "listener":
            target(kwargs["linker"], kwargs["logger"], kwargs["asana_token"], kwargs["project"])
        else:
            target(
                kwargs["linker"], 
                kwargs["logger"], 
                kwargs["discord_webhook_url"], 
                kwargs["asana_token"], 
                kwargs["asana_workspace"]
            )

    except asana.error.InvalidRequestError:
        logger.warning("AsanaListener for project {} ended. The project was deleted.".format(kwargs["project"]['name']))
        return False

    except (KeyboardInterrupt, SystemExit):
        raise

    except Exception:
        print(traceback.format_exc())
        time.sleep(20)
        retry_wrapper(target, target_type, **kwargs)
