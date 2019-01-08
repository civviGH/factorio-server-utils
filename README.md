# factorio-server-utils

script to manage factorio headless servers

## requirements
python 2
modules: requests, json, os, subprocess, sys, re

## usage
copy settings-example.json to settings.json
fill in needed information
username: your factorio username
token: used to authenticate against the factorio servers. found in your factorio.com profile
mod\_directory: absolute path of mod directory. make sure it starts and ends with a "/", eg: "/home/factorio/mods/"
exe\_directory: absolute path of exe directory. make sure it start and ends with a "/", eg: "/home/factorio/bin/x64/"

then just run the scripts.
update-mods.py updates all mods in the mod folder to the latest version.
update-headless.py updates the executable of the headless to the latest version.

## limitations
those scripts are just made to work, not to bring a lot of QoL. do not try to patch a binary thats before version 0.14.0 as
there is no patch from 0.13 to 0.14.
if your setup differs from mine you may have to edit a line or two of code. its just plain python though, no magic involved.
