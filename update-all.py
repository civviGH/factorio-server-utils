#!/usr/bin/env python2

# imports
import sys
import os
import json
import subprocess
import re
import requests

def print_usage():
  usage_str ="""
  usage: update-all.py FOLDERNAME
  """
  print(usage_str)

def find_latest_version(exe_version, updates):
  #exe_minor = int(exe_version.split(".")[-1])
  exe_major = exe_version.split(".")[1]
  update_minors = []
  for update in updates:
    up_to = update["to"]
    if up_to.split(".")[1] == exe_major:
      update_minors.append(int(up_to.split(".")[-1]))
  return ".".join(exe_version.split(".")[:-1]) + "." + str(max(update_minors))

# get factorio installation folder from cmdline
if len(sys.argv) <= 1:
  print_usage()
  sys.exit(1)

try:
  FACTORIO_PATH = str(sys.argv[1])
except:
  print("Could not parse first argument to string. exiting.")
  sys.exit(1)

# check if path actually exists
if not os.path.isdir(FACTORIO_PATH):
  print("{} does not exists. exiting.".format(FACTORIO_PATH))
  sys.exit(1)

FACTORIO_BINARY = FACTORIO_PATH + "/bin/x64/factorio"
if not os.path.isfile(FACTORIO_BINARY):
  print("No binary found at {}. exiting.".format(FACTORIO_BINARY))
  sys.exit(1)

# open settings for username and token
with open("settings.json", "r") as s:
  settings = json.load(s)
username = settings["username"]
token = settings["token"]

# get version of own executable
exe_version = subprocess.check_output([FACTORIO_BINARY, "--version"])
exe_version = re.search("Version: (\d+\.\d+\.\d+)", exe_version)
exe_version = exe_version.group(1)
print("Auto detected binary version as {}".format(exe_version))
print("Looking for updates only for this major release.")

# check most recent version. if executable is up to date, exit
url = "https://updater.factorio.com/get-available-versions"
response = requests.get(url)
versions_json = json.loads(response.content)
updates_json = versions_json["core-linux_headless64"][:-1]
latest_version = find_latest_version(exe_version, updates_json)
print("Latest version detected as {}".format(latest_version))

if (exe_version == latest_version):
  print("Executable is up to date.")

# version sanity check
if int(exe_version.split(".")[2]) > int(latest_version.split(".")[2]):
  print("Exe version somehow bigger than latest update? exiting.")
  sys.exit(1)

# get list of updates to download
working_version = exe_version
download_links = []
while working_version != latest_version:
    for update in updates_json:
        if update["from"] == working_version:
            download_links.append("https://updater.factorio.com/get-download-link?username={}&token={}&apiVersion=2&from={}&to={}&package=core-linux_headless64".format(username, token, update["from"], update["to"]))
            working_version = update["to"]
            print("Need update from {} to {}".format(update["from"], update["to"]))

# actually download updates
num_updates = len(download_links)
i = 0
for download_link in download_links:
    print("downloading patch {}/{}".format(i+1, num_updates))
    response = requests.get(download_link)
    update_link = json.loads(response.content)[0]
    response = requests.get(update_link)
    with open("updates/" + str(i) + ".zip", "wb") as update_download:
        update_download.write(response.content)
    i = i + 1

# apply all updates
for j in range(i):
    try:
        print("patching {}/{}".format(j+1,num_updates))
        subprocess.check_output([FACTORIO_BINARY, "--apply-update", "updates/" + str(j) + ".zip"])
    except subprocess.CalledPorcessError as ex:
        print(ex.output)
        raise
    os.remove("updates/" + str(j) + ".zip")
print("Finished. Printing executable version:")
print(subprocess.check_output([FACTORIO_BINARY , "--version"]))

print("-")
print("Updating mods")
FACTORIO_MOD_PATH = FACTORIO_PATH + "/mods"
# check if path actually exists
if not os.path.isdir(FACTORIO_MOD_PATH):
  print("{} does not exists. exiting.".format(FACTORIO_MOD_PATH))
  sys.exit(1)

# get name of every mod
with open(FACTORIO_MOD_PATH + "/mod-list.json", "r") as modfile:
    mods_json = json.load(modfile)
mod_names = []
for mod in mods_json["mods"]:
    if mod["name"] != "base":
        mod_names.append(mod["name"])
print("found the following mods in mod-list.json:")
for mod in mod_names:
    print(" " + mod)

delete_us = []
print("check if mods are up to date")
for mod in mod_names:
    print(mod)
    url = "https://mods.factorio.com/api/mods?page_size=max&namelist=" + mod
    response = requests.get(url)
    mod_json = json.loads(response.content)
    releases = mod_json["results"][0]["releases"]
    latest_release = max(releases)
    if os.path.isfile(FACTORIO_MOD_PATH + "/" + latest_release["file_name"]):
        print(" up to date")
    else:
        for modfile in os.listdir(FACTORIO_MOD_PATH):
            if modfile.find(mod) != -1:
                print("flagging " + modfile + " for removal")
                delete_us.append(modfile)
        print("downloading " + latest_release["file_name"])
        response = requests.get("https://mods.factorio.com/" + latest_release["download_url"] + "?username=" + username + "&token=" + token)
        with open(FACTORIO_MOD_PATH + "/" + latest_release["file_name"], "wb") as downloaded_mod:
            downloaded_mod.write(response.content)
print("deleting old mod files")
for modfile in delete_us:
    print(" " + modfile)
    os.remove(FACTORIO_MOD_PATH + "/" + modfile)
print("done. exiting")
