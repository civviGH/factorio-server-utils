#!/usr/bin/env python2

import requests
import json
import os

with open("settings.json", "r") as s:
    settings = json.load(s)
username = settings["username"]
token = settings["token"]
mod_directory = settings["mod_directory"]

# get name of every mod
with open(mod_directory + "mod-list.json", "r") as modfile:
    mods_json = json.load(modfile)

mod_names = []

for mod in mods_json["mods"]:
    if mod["name"] != "base":
        mod_names.append(mod["name"])

print("[+] found the following mods in mod-list.json:")
for mod in mod_names:
    print("    " + mod)

delete_us = []
print("\n[+] check if mods are up to date")
for mod in mod_names:
    print("\n[+] " + mod)
    url = "https://mods.factorio.com/api/mods?page_size=max&namelist=" + mod
    response = requests.get(url)
    mod_json = json.loads(response.content)
    releases = mod_json["results"][0]["releases"]
    latest_release = max(releases)
    if os.path.isfile(mod_directory + latest_release["file_name"]):
        print("    up to date")
    else:
        for modfile in os.listdir(mod_directory):
            if modfile.find(mod) != -1:
                print("    flagging " + modfile + " for removal")
                delete_us.append(modfile)
        print("    downloading " + latest_release["file_name"])
        response = requests.get("https://mods.factorio.com/" + latest_release["download_url"] + "?username=" + username + "&token=" + token)
        with open(mod_directory + latest_release["file_name"], "wb") as downloaded_mod:
            downloaded_mod.write(response.content)
print("\n[+] deleting old mod files")
for modfile in delete_us:
    print("    " + modfile)
    os.remove(mod_directory + modfile)
print("[+] done. exiting")
