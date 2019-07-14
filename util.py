#!/usr/bin/env python3

import sys
import json
import os

def print_usage():
  #TODO
  usage_str ="""
  usage:
    util.py OPTION [ARGS]

  options:
    list - list all servers
    update NAME - update server NAME
    update-mods NAME - update the mods of NAME
    update-all NAME - update server and mods of NAME
  """
  print(usage_str)

def list_servers(SETTINGS):
  server_dirs = os.listdir(SETTINGS["serverdir"])
  for server in server_dirs:
    # list version and enabled mods
    print(server)
  return

def load_settings():
  try:
    with open("settings.json", "r") as s:
      settings = json.load(s)
  except:
    print("Could not load settings.json\n")
    raise

  return settings

def main():
  if len(sys.argv) < 2:
    print_usage()
    sys.exit(1)

  if sys.argv[1] == "help":
    print_usage()
    return

  SETTINGS = load_settings()

  if sys.argv[1] == "list":
    list_servers(SETTINGS)
    return

  # if we make it till here its an unknown option
  print(f"unknown option '{sys.argv[1]}'")
  print(f"run with no options for usage")
  sys.exit(1)

if __name__ == "__main__":
  main()
  sys.exit(0)
