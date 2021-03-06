import asana
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
    def __init__(self, linker, logger, discord_token, discord_channel, asana_token, asana_workspace):
        self.linker = linker
        self.logger = logger

        self.asana_token = asana_token
        self.asana_workspace = asana_workspace
        self.asana_client = None

        self.discord_token = discord_token
        self.discord_channel = discord_channel

        self.overdue_tasks = [] # To save the tasks already announced
    
    def run(self):
        self.linker.register(self)

        # Login in asana
        self.asana_client = access_asana(self.asana_token)

    @staticmethod
    def start(linker, logger, discord_token, discord_channel, asana_token, asana_workspace):
        """ Starts the bot from a thread """
        bot = AsanaBot(linker, logger, discord_token, discord_channel, asana_token, asana_workspace)
        bot.run()
    
    def announce_event(self, event_type, task):
        """ Creates the announcements """
        if event_type == "completed":
            self.logger.debug("Announcing completion of a task")
            if task["assignee"]:
                message = "```css\n # Task Completed! - {} ({})```".format(
                    task["name"], 
                    task["assignee"]["name"]
                )
            else: # Non asigned
                message = "```css\n # Task Completed! - {}```".format(task["name"])  
            self.send_message(message)

        elif event_type == "overdue":
            self.logger.debug("Announcing overdue of a task")
            if task["assignee"]:
                message = "```glsl\n # Task Overdue! - {} ({})```".format(
                    task["name"], 
                    task["assignee"]["name"]
                )
            else: # Non asigned
                message = "```glsl\n # Task Overdue! - {}```".format(task["name"])
            self.send_message(message)

    def send_message(self, msg):
        """ Message utility """
        url = "https://discordapp.com/api/v6/channels/{}/messages".format(self.discord_channel)

        headers = {
            "Authorization": "Bot {}".format(self.discord_token),
            "Content-Type": "application/json",
        }
        body = {
            "content": msg
        }
        return requests.request("POST", url, headers=headers, json=body)
      
