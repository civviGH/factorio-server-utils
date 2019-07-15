#!/usr/bin/env python3

"""
factorio@factory:~/0.17-headless$ cat start_creative.sh
#!/bin/bash
creative/bin/x64/factorio --start-server creative/maps/creative.zip \
	--port 23451 \
	--bind 131.220.32.152 \
	--server-settings creative/server-settings.json \
	--server-whitelist creative/server-whitelist.json \
	--console-log creative/logs/server.log \
	--use-server-whitelist
"""

import sys, json, os, subprocess, re, psutil
from src.server import *

def print_usage():
  #TODO
  usage_str ="""
  usage:
    util.py OPTION [ARGS]

  options:
    list - list all servers
    start NAME - start server if its not running
    stop NAME - stop server if its running
    update NAME - update server NAME
    update-mods NAME - update the mods of NAME
    update-all NAME - update server and mods of NAME
  """
  print(usage_str)

def get_factorio_version(path_to_exe):
  """Returns the version of the factorio executable given by parameter"""
  exe_version = str(subprocess.check_output([path_to_exe, "--version"]))
  exe_version = re.search("Version: (\d+\.\d+\.\d+)", exe_version)
  exe_version = exe_version.group(1)
  return exe_version

def get_server_list(SETTINGS):
  """Lists version and enabled mods of all servers found in SETTINGS.serverdir"""
  factorio_servers = []
  server_dirs = os.listdir(SETTINGS["serverdir"])
  for server in server_dirs:
    # check if actual factorio server directory or not
    if not os.path.isdir(f"{SETTINGS['serverdir']}/{server}"):
      continue
    if not os.path.isfile(f"{SETTINGS['serverdir']}/{server}/bin/x64/factorio"):
      continue
    factorio_servers.append(server)
  if len(factorio_servers) == 0:
    print(f"No factorio servers found in {SETTINGS['serverdir']}")
    return []
  return factorio_servers

def load_settings():
  try:
    with open("settings.json", "r") as s:
      settings = json.load(s)
  except:
    print("Could not load settings.json\n")
    raise

  return settings

def check_if_server_is_running(servername):
  """check if a server named servername is running. returns pid if found, None else."""
  processes = [proc.as_dict(attrs=['exe','pid','connections']) for proc in psutil.process_iter(attrs=['name']) if 'factorio' in proc.info['name']]
  for p in processes:
    if p['exe'].find(f"/{servername}/bin/x64/factorio") != -1:
      return p['pid']
  return

def load_servers(SETTINGS):
  factorio_servers = get_server_list(SETTINGS)
  servers = []
  for f in factorio_servers:
    servers.append(FactorioServer(f, SETTINGS))
  return servers

def get_servername_from_argv():
  try:
    servername = sys.argv[2]
  except:
    print(f"cant parse second argument as servername")
    sys.exit(1)
  return servername

def main():
  if len(sys.argv) < 2:
    print_usage()
    sys.exit(1)

  if sys.argv[1] == "help":
    print_usage()
    return

  SETTINGS = load_settings()
  SERVERS = load_servers(SETTINGS)

  if sys.argv[1] == "list":
    for server in SERVERS:
      print(server)
    return

  servername = get_servername_from_argv()
  if sys.argv[1] == "stop":
    for server in SERVERS:
      if server.name == servername:
        server.stop()
        return
    print(f"No server named {servername} found.")
    return

  if sys.argv[1] == "start":
    for server in SERVERS:
      if server.name == servername:
        server.start()
        return
    return

  if sys.argv[1] == "restart":
    for server in SERVERS:
      if server.name == servername:
        server.restart()
        return
    return

  # if we make it till here its an unknown option
  print(f"unknown option '{sys.argv[1]}'")
  print(f"run with no options for usage")
  sys.exit(1)

if __name__ == "__main__":
  main()
  sys.exit(0)
