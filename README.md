# factorio-server-utils

script to manage factorio headless servers

## requirements

- python3.6 or higher
- modules: see requirements file

Install python3 requirements e.g. via `python3 -m pip install -r requirements --user`

## usage

Copy the settings.json.template to settings.json and fill in the needed information.

Example:
```
{
	"_comment_username": "Your factorio username. Used to retrieve updates",
	"username": "name1",
	"_comment_token": "The token for your username, used for authentication instead of password. See factorio.com user account",
	"token": "YOURTOKENHERE",
	"_comment_serverdir": "The directory where your headless server folders are. Absolute path",
	"serverdir": "/path/to/factorio/servers",
  "_comment_whitelist": "The server whitelist used. Contains a list of strings. Create whitelist file if none is found",
  "whitelist": [
    "name1",
    "name2",
    "name3"
  ],
  "_comment_portrange": "Range from which possible ports to bind to are chosen. Important for firewall
  configurations. If left empty, the os will choose the ports",
  "portrange": "34197:34220"
}

```

Then simply run `factorio-server-utility help` on how to use it.

## limitations

This tool is just made to work, not to bring a lot of QoL. Dont patch major versions with this. Dont expect every corner-case to be considered.

If your setup differs from mine you may have to edit a line or two of code. Its just plain python though, no magic involved.
