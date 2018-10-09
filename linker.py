class Linker:
    """ Creates a link between AsanaBot and the AsanaListeners"""
    def __init__(self):
        self.bot = None

    def register(self, bot):
        """
        Registers the AsanaBot, enabling events to be sent to the bot.
        """
        self.bot = bot

    def push(self, event_type, task):
        """
        Ingests an event from a given listener and routes it through AsanaBot.
        The event_types are "completed" or "overdue"
        """
        self.bot.announce_event(event_type, task)