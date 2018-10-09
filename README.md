# Asana-Discord
An integration of Asana with Discord, creates anouncements in the given channel when
a task is completed or expired.

[Blubber thread](https://blubber.fatwhale.com/d/254-asana-discord-integration)
[Asana project](https://app.asana.com/0/638996721805425/board)

## Status
The project is ready for production.

## Configuration
Configuration is handled via environment variables.
It needs the following env_vars:
```
mode: <mode> ["testing", "production"] # For the logger
discord_token: <string>     # The discord token of the bot to use
discord_channel: <int>      # The discord channel to post the anouncements
asana_token: <string>       # The token of an asana account
asana_workspace: <int>      # The id of the asana workspace to get the projects and task from
sentry_url: <string>        # The url token for sentry
```

To start the bot use: `python main.py`
