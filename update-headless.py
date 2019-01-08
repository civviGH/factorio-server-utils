#!/usr/bin/env python2

import requests
import json
import os
import subprocess
import sys
import re

with open("settings.json", "r") as s:
    settings = json.load(s)
username = settings["username"]
token = settings["token"]
exe_directory = settings["exe_directory"]

# get version of own executable
exe_version = subprocess.check_output([exe_directory + "/factorio", "--version"])
exe_version = re.search("Version: (\d+\.\d+\.\d+)", exe_version)
exe_version = exe_version.group(1)
print("Auto detected binary version as {}".format(exe_version))

# check most recent version. if executable is up to date, exit
url = "https://updater.factorio.com/get-available-versions"
response = requests.get(url)
versions_json = json.loads(response.content)
updates_json = versions_json["core-linux_headless64"][:-1]
latest_version = versions_json["core-linux_headless64"][-1]["stable"]
print("Latest version detected as {}".format(latest_version))

if (exe_version == latest_version):
    print("Executable is up to date.")
    sys.exit(0)

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
        subprocess.check_output([exe_directory + "/factorio", "--apply-update", "updates/" + str(j) + ".zip"])
    except subprocess.CalledPorcessError as ex:
        print(ex.output)
        raise
    os.remove("updates/" + str(j) + ".zip")
print("Finished. Printing executable version:")
print(subprocess.check_output([exe_directory + "/factorio" , "--version"]))
