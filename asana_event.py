import datetime
import time
import traceback

import asana
from util import access_asana


muted_projects = ["Dashboard"]


class AsanaListener:
    """ 
    Asana client that keeps a connection getting task events for the target Asana project
    
    Arguments:\n
        linker: An instance of linker (connection between AsanaListeners and AsanaBot) \n
        logger: A logger instance \n
        asana_token: Your Asana account token (str)\n
        project: The target Asana project to search tasks from (dic)\n
    """
    def __init__(self, linker, logger, asana_token, project):
        self.linker = linker
        self.logger = logger
        self.asana_token = asana_token
        self.asana_client = None
        self.project = project
        self.tasks = {}
        self.asana_restart_loops = 120
        self.overdued_tasks = []
        self.completed_tasks = []

    def listen_events(self, project):
        """ Listens for events from the target project """
        self.logger.info("Streaming events for " + project['name'])
        if project['name'] in muted_projects:
            self.logger.debug("Muting events from {}".format(project['name']))
            return

        # Create a first run for old tasks
        # Authorize in asana 
        self.asana_client = access_asana(self.asana_token)
        if not self.asana_client:
            return
            
        # Get all the tasks in the project
        tasks = self.asana_client.tasks.find_by_project(
            project['id'], 
            iterator_type=None, 
            opt_expand="name,projects,parent,workspace,id,assignee,assignee_status,completed,completed_at,due_on,due_at,external,modified_at"
        )

        # Add all the tasks to the tasks list
        for task in tasks:
            task["initial"] = True
            self.tasks[task["id"]] = task

        # Loop that checks for new tasks, completion of tasks and overdue of tasks.
        loops = 0 
        while True:
            # Restart asana_client each self.asana_restart_loops mins
            if loops >= self.asana_restart_loops or not self.asana_client:
                # Authorize in asana 
                self.asana_client = access_asana(self.asana_token)
                loops = 0
                if not self.asana_client:
                    break
                
            # Get all the tasks in the project
            tasks = self.asana_client.tasks.find_by_project(
                project['id'], 
                iterator_type=None, 
                opt_expand="name,projects,parent,workspace,id,assignee,assignee_status,completed,completed_at,due_on,due_at,external,modified_at"
            )

            # Update the tasks list
            for task in tasks:
                # Check if the task exists already in the current tasks list
                if task["id"] in self.tasks:
                    # Check if it's completed
                    if task["completed"]:
                        # Check if we already have sent the announcement
                        if task["id"] in self.completed_tasks:
                            continue

                        # Checks that the task was just completed
                        saved_task_completed = self.tasks[task["id"]]["completed"]
                        if not saved_task_completed:
                            self.linker.push("completed", task)
                            self.completed_tasks.append(task["id"])
                            
                        # Checks that the task was saved completed
                        elif saved_task_completed and not self.tasks[task["id"]].get("initial"):
                            self.linker.push("completed", task)
                            self.completed_tasks.append(task["id"])

                    # Check if it's overdue
                    elif task["due_on"]:
                        
                        # Check if we already have sent the announcement
                        if task["id"] in self.overdued_tasks:
                            continue
                        
                        # Check the timestamp depending of the deadline style
                        due_on_len = len(task["due_on"])
                        initial_task = self.tasks[task["id"]].get("initial")
                        
                        if due_on_len == 10 and not initial_task:
                            task_timestamp = int(datetime.datetime.strptime(task["due_on"], "%Y-%m-%d").timestamp())
                            real_overdue_timestamp = int(task_timestamp + 24*60*60) # Adds one day to the timestamp

                            # Check if the overdue is correct
                            if int(time.time()) > real_overdue_timestamp:
                                self.overdued_tasks.append(task["id"])
                                self.linker.push("overdue", task)
                else:
                    # Save the new task
                    self.tasks[task["id"]] = task
                
            loops += 1
            time.sleep(15)
            
    def run(self):
        """ Starts asana and blocks the thread by getting events from the target project """

        # Start a local asana asana_client
        self.asana_client = access_asana(self.asana_token)
        
        # Start getting events
        self.listen_events(self.project)

    @staticmethod
    def start(linker, logger, asana_token, project):
        """ Starts itself from a thread """
        bot = AsanaListener(linker, logger, asana_token, project)
        bot.run()
