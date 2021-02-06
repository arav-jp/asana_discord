import asana
import json
import pprint
import threading
import time
import requests
from util import access_asana


class AsanaBot:
    """ 
    Discord Bot that filters asana tasks/events and creates announcements in it's target channel.
    
     Arguments:\n
        linker: Mode to run the script. It just changes the logger. "production" or "testing" \n
        logger: Your Discord token (str)\n
        asana_token: Your Asana account token (str)\n
        data: The target Asana workspace to search tasks from (str)\n
        
    """
    def __init__(self, linker, logger, discord_webhook_url, asana_token, asana_workspace):
        self.linker = linker
        self.logger = logger

        self.asana_token = asana_token
        self.asana_workspace = asana_workspace
        self.asana_client = None

        self.discord_webhook_url = discord_webhook_url

        self.overdue_tasks = [] # To save the tasks already announced
    
    def run(self):
        self.linker.register(self)

        # Login in asana
        self.asana_client = access_asana(self.asana_token)

    @staticmethod
    def start(linker, logger, discord_webhook_url, asana_token, asana_workspace):
        """ Starts the bot from a thread """
        bot = AsanaBot(linker, logger, discord_webhook_url, asana_token, asana_workspace)
        # print(bot.send_message("```\nStart asana_discord bot: " + str(time.time()) + "\n```"))
        bot.run()
    
    def announce_event(self, event_type, task):
        permalink_url = task["projects"][0]["permalink_url"]
        task_link = '/'.join(permalink_url.split('/')[0:len(permalink_url.split('/'))-1]) + '/' + task["gid"]
        """ Creates the announcements """
        if event_type == "completed":
            color = "ini"
            comment = "Task Completed!"
        elif event_type == "overdue":
            color = "css"
            comment = "Task Overdue!"
        elif event_type == "newtask":
            color = "fix"
            comment = "New task!"

        self.logger.debug("Announcing: " + comment)
        message = "{}\n```{}\n[ # {}: {} - {} ({})]```".format(
            task_link, 
            color, 
            comment, 
            task["name"], 
            task["projects"][0]["name"], 
            task["assignee"]
        )
        print(self.send_message(message))

    def send_message(self, msg):
        headers = {
            'Content-Type': 'application/json'
        }
        body = {
            'content': msg
        }
        return requests.request("POST", self.discord_webhook_url, headers=headers, json=body)
