import datetime
import pprint
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
        self.fields = [
            "gid",
            "resource_type",
            "created_at",
            "created_by",
            "resource_subtype",
            "text",
            "html_text",
            "is_pinned",
            "assignee",
            "dependency",
            "duplicate_of",
            "duplicated_from",
            "follower",
            "hearted",
            "hearts",
            "is_edited",
            "liked",
            "likes",
            "new_approval_status",
            "new_dates",
            "new_enum_value",
            "new_name",
            "new_number_value",
            "new_resource_subtype",
            "new_section",
            "new_text_value",
            "num_hearts",
            "num_likes",
            "old_approval_status",
            "old_dates",
            "old_enum_value",
            "old_name",
            "old_number_value",
            "old_resource_subtype",
            "old_section",
            "old_text_value",
            "preview",
            "project",
            "source",
            "story",
            "tag",
            "target",
            "task"
        ]

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
            project["gid"], 
            iterator_type=None, 
            opt_expand="name,projects,parent,workspace,id,assignee,assignee_status,completed,completed_at,due_on,due_at,external,modified_at"
        )
        # pprint.pprint(tasks[0])

        # Add all the tasks to the tasks list
        for task in tasks:
            task["initial"] = True
            temp_stories = self.asana_client.stories.get_stories_for_task(
                task["gid"], 
                opt_expand=",".join(self.fields), 
                opt_pretty=True
            )
            stories = list(temp_stories)
            stories_len = len(stories)
            task["last_stories_len"] = stories_len
            task["last_story_html_text"] = stories[stories_len-1]['html_text']
            task["last_created_by_name"] = stories[stories_len-1]['created_by']['name']
            self.tasks[task["gid"]] = task

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
                project["gid"], 
                iterator_type=None, 
                opt_expand="name,projects,parent,workspace,id,assignee,assignee_status,completed,completed_at,due_on,due_at,external,modified_at"
            )

            # Update the tasks list
            for task in tasks:
                temp_stories = self.asana_client.stories.get_stories_for_task(
                    task["gid"], 
                    opt_expand=",".join(self.fields), 
                    opt_pretty=True
                )
                stories = list(temp_stories)
                stories_len = len(stories)

                # Check if the task exists already in the current tasks list
                if task["gid"] in self.tasks:
                    # New Story
                    last_story = stories[stories_len-1]
                    self.tasks[task["gid"]]["last_story_html_text"] = last_story['html_text']
                    self.tasks[task["gid"]]["last_created_by_name"] = last_story['created_by']['name']
                    if self.tasks[task["gid"]]["last_stories_len"] != stories_len:
                        # pprint.pprint(last_story)
                        # print(self.tasks[task["gid"]]["last_stories_len"], stories_len)
                        self.linker.push("newstory", self.tasks[task["gid"]])

                    # Check if it's completed
                    if task["completed"]:
                        # Check if we already have sent the announcement
                        if not task["gid"] in self.completed_tasks:
                            # Checks that the task was just completed
                            saved_task_completed = self.tasks[task["gid"]]["completed"]
                            if not saved_task_completed:
                                self.linker.push("completed", task)
                                self.completed_tasks.append(task["gid"])
                                
                            # Checks that the task was saved completed
                            elif saved_task_completed and not self.tasks[task["gid"]].get("initial"):
                                self.linker.push("completed", task)
                                self.completed_tasks.append(task["gid"])

                    # Check if it's overdue
                    elif task["due_on"]:
                        # Check if we already have sent the announcement
                        if not task["gid"] in self.overdued_tasks:
                            # Check the timestamp depending of the deadline style
                            due_on_len = len(task["due_on"])
                            initial_task = self.tasks[task["gid"]].get("initial")
                            
                            if due_on_len == 10 and not initial_task:
                                task_timestamp = int(datetime.datetime.strptime(task["due_on"], "%Y-%m-%d").timestamp())
                                real_overdue_timestamp = int(task_timestamp + 24*60*60) # Adds one day to the timestamp
    
                                # Check if the overdue is correct
                                if int(time.time()) > real_overdue_timestamp:
                                    self.overdued_tasks.append(task["gid"])
                                    self.linker.push("overdue", task)

                elif task["name"]:
                    # Save the new task
                    self.tasks[task["gid"]] = task
                    self.linker.push("newtask", task)

                if task["gid"] in self.tasks:
                    self.tasks[task["gid"]]["last_stories_len"] = stories_len

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
