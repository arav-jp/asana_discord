import threading
import time
import os

import click
import asana

from util import DummyLogger, retry_wrapper, logger_pick, access_asana
from asana_discord import AsanaBot
from asana_event import AsanaListener
from linker import Linker     


def project_starter(linker, logger, asana_token, asana_workspace):
    '''
    Start all of the listeners and AsanaBot in separate threads to not block 
    the main thread. Give them each a reference to the linker so that they can 
    send events to AsanaBot.
    '''
    started_projects = []
    loops = 0               # Number of times that the while loop has runned
    asana_client = None

    while True:
        # Restart asana_client each 60 mins
        if loops >= 60 or not asana_client:
            # Authorize in asana 
            asana_client = access_asana(asana_token)
            if not asana_client:
                break

            loops = 0
            
        # Search for projects
        projects = asana_client.projects.find_by_workspace(asana_workspace, iterator_type=None) # pylint: disable=E1101
        if not projects:
            logger.warning('There are no projects to follow in your workspace')

        for project in projects:
            # Check if we need to start the project
            if project["id"] in started_projects:
                continue
            else:
                listener_thread = threading.Thread(
                    target=retry_wrapper,
                    kwargs={
                        'target': AsanaListener.start,
                        'target_type': "listener",
                        'linker': linker,
                        'logger': logger,
                        'asana_token': asana_token,
                        'project': project
                    }
                ) 
                listener_thread.start()
                started_projects.append(project["id"])
                time.sleep(5) # Giving 5s of time space between each thread
        loops += 1
        time.sleep(60)

@click.command()
@click.argument('mode',             envvar="MODE",              type=click.STRING)
@click.argument('discord_token',    envvar="DISCORD_TOKEN",     type=click.STRING)
@click.argument('discord_channel',  envvar="DISCORD_CHANNEL",   type=click.INT)
@click.argument('asana_token',      envvar="ASANA_TOKEN",       type=click.STRING)
@click.argument('asana_workspace',  envvar="ASANA_WORKSPACE",   type=click.INT)
@click.argument('sentry_url',       envvar="SENTRY_URL",        type=click.STRING)
def main(mode, discord_token, discord_channel, asana_token, asana_workspace, sentry_url):
    """
    Starts AsanaBot and AsanaListener in separated threads. 

    Arguments:\n
        MODE: Mode to run the script. It just changes the logger. "production" or "testing" \n
        DISCORD_TOKEN: Your Discord token (str)\n
        DISCORD_CHANNEL: Target channel to post the announcements (int)\n
        ASANA_TOKEN: Your Asana account token (str)\n
        ASANA_WORKSPACE: The target Asana workspace to search tasks from (str)\n
        SENTRY_URL: Your Sentry application url token (str)\n
    """
    
    logger = logger_pick(mode, sentry_url) 
    linker = Linker() # A class that links the discord bot with the asana listeners

    # Start project_starter thread
    project_starter_thread = threading.Thread(
        target=project_starter,
        kwargs={
            'linker': linker,
            'logger': logger,
            'asana_token': asana_token,
            'asana_workspace': asana_workspace
        }
    )
    project_starter_thread.start()

    # Start AsanaBot thread
    bot_thread = threading.Thread(
        target=retry_wrapper,
        kwargs={
            'target': AsanaBot.start,
            'target_type': "bot",
            'linker': linker,
            'logger': logger,
            'discord_token': discord_token,
            'discord_channel': discord_channel,
            'asana_token': asana_token,
            'asana_workspace': asana_workspace
        }
    )
    bot_thread.start()

    logger.info('All the threads are running.')

if __name__ == '__main__':
    main() # pylint: disable=E1120