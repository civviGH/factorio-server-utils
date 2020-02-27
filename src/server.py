import psutil, re, subprocess, socket, os, jinja2, time, json, sys
import requests

class FactorioServer:

  used_ports = []
  updater_url = "https://updater.factorio.com/get-available-versions"
  download_url = "https://updater.factorio.com/get-download-link"
  mod_url = "https://mods.factorio.com/api/mods?page_size=max&namelist="
  multiplayer_api = "https://multiplayer.factorio.com/get-game-details/"
  latest_version = None

  #
  #
  #

  def get_latest_modrelease_by_modname(modname):
    url = f"{FactorioServer.mod_url}{modname}"
    response = requests.get(url)
    try:
      mod_json = json.loads(response.content)
      releases = mod_json["results"][0]["releases"]
      # this assumes that the API provides the version in an ordered fashion
      # may change in the future
      return releases[-1]
    except:
      return None

  #
  #
  #

  def get_playercount(self):
    if not self.is_running:
      return 0
    response = requests.get(f"{FactorioServer.multiplayer_api}{self.game_id}")
    server_description = json.loads(response.content)
    try:
      return len(server_description['players'])
    except:
      return 0

  def check_if_updates_folder_is_ready(self):
    # check if updates/ exists
    if not os.path.isdir("updates/"):
      print("no updates/ folder found")
      return False
    # check if its empty
    for f in os.listdir("updates/"):
      if not f.startswith("."):
        return False
    return True

  def get_process_information(self):
    """gathers process information for server"""
    processes = [proc.as_dict(attrs=['exe','pid','connections']) for proc in psutil.process_iter(attrs=['name']) if 'factorio' in proc.info['name']]
    for p in processes:
      if p['exe'].find(f"/{self.name}/bin/x64/factorio") != -1:
        # server is running
        # get port from server logs
        regex = re.compile(r'--port\" \"(\d+)\"')
        with open(f"{self.dir}/factorio-current.log") as f:
          for line in f:
            result = regex.search(line)
            if result is not None:
              port = int(result.group(1))
              return p['pid'], True, port
        return p['pid'], True, None
    return None, False, None

  def get_factorio_version(self):
    """Returns the version of the factorio executable"""
    return re.search("Version: (\d+\.\d+\.\d+)", str(subprocess.check_output([f"{self.exe_dir}/factorio", "--version"]))).group(1)

  def check_if_port_is_open(self, port):
    if port in FactorioServer.used_ports:
      return False
    return True

  def get_free_port(self):
    if self.portrange is None:
      return self.get_free_port_from_os()
    for i in range(self.portrange[0], self.portrange[1]+1):
      if self.check_if_port_is_open(i):
        return i
    return None

  def find_latest_version(self):
    if FactorioServer.latest_version is not None:
      return FactorioServer.latest_version
    exe_major = self.version.split(".")[1]
    available_updates = json.loads(requests.get(FactorioServer.updater_url).content)["core-linux_headless64"][:-1]
    minor_updates = []
    for update in available_updates:
      up_to = update["to"]
      if up_to.split(".")[1] == exe_major:
        minor_updates.append(int(up_to.split(".")[-1]))
    FactorioServer.latest_version = ".".join(self.version.split(".")[:-1]) + "." + str(max(minor_updates))
    return FactorioServer.latest_version

  def get_free_port_from_os(self):
    # shouldnt this be a UDP socket instead of a TCP?
    udp_connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_connection.bind(('', 0))
    addr, port = udp_connection.getsockname()
    udp_connection.close()
    return port

  def create_server_settings(self):
    j2 = jinja2.Environment(loader=jinja2.FileSystemLoader(f"{os.getcwd()}/templates"))
    settings_template = j2.get_template("server-settings.jj")
    data = {}
    data['servername'] = self.name
    data['username'] = self.settings['username']
    data['token'] = self.settings['token']
    server_settings_content = settings_template.render(data)
    with open(f"{self.dir}/server-settings.json", "w") as sfile:
      sfile.write(server_settings_content)
    return

  def check_if_save_exists(self):
    if not os.path.isdir(f"{self.dir}/saves"):
      return False
    if len(os.listdir(f"{self.dir}/saves/")) > 0:
      return True
    return False

  def get_game_id_from_log(self):
    regex = re.compile(r'Matching server game `(\d*)` has been created')
    with open(f"{self.dir}/factorio-current.log") as f:
      for line in f:
        result = regex.search(line)
        if result is not None:
          return result.group(1)
    return None
  
  def get_modlist(self):
    # check if modlist file exists
    modlist_path = f"{self.dir}/mods/mod-list.json"
    if not os.path.isfile(modlist_path):
      return []
    # parse json file
    with open(modlist_path, "r") as f:
      modlist = json.loads(f.read())["mods"]
    returnlist = []
    for mod in modlist:
      if mod["name"] == "base":
        continue
      if mod["enabled"]:
        returnlist.append(mod["name"])
    return returnlist
    # sort the modlist
    
  def __init__(self, servername, settings):
    self.name = servername
    self.settings = settings
    self.dir = f"{self.settings['serverdir']}/{self.name}"
    self.exe_dir = f"{self.dir}/bin/x64"
    self.pid, self.is_running, self.port = self.get_process_information()
    if self.is_running:
      FactorioServer.used_ports.append(self.port)
    self.version = self.get_factorio_version()
    self.modlist = None
    self.save_exists = self.check_if_save_exists()
    try:
      self.portrange = [int(i) for i in self.settings['portrange'].split(":")]
    except:
      self.portrange = None
    if self.is_running:
      self.game_id = self.get_game_id_from_log()
    else:
      self.game_id = None
    self.modlist = self.get_modlist()

    return

  def start(self):
    print(f"trying to start server '{self.name}'")
    if not self.save_exists:
      print(f"Server {self.name} does not have a save file. Please provide one in")
      print(f" {self.dir}/saves")
      return
    if os.path.isfile(f"{self.dir}/.lock"):
      print(f"found .lock file in {self.dir}. Can not start server.")
      print("is the server already running?")
      return
    self.port = self.get_free_port()
    if self.port is None:
      print("Could not find open port. exiting")
      sys.exit(1)
    if not os.path.isfile(f"{self.dir}/server-settings.json"):
      self.create_server_settings()
    with open(f"{self.dir}/server-whitelist.json", "w") as wfile:
      wfile.write(json.dumps(self.settings['whitelist']))
    subprocess.Popen(f"{self.exe_dir}/factorio --start-server-load-latest --port {self.port} --server-settings {self.dir}/server-settings.json --server-whitelist {self.dir}/server-whitelist.json --use-server-whitelist".split(), stdout=subprocess.DEVNULL)
    time.sleep(2)
    self.pid, self.is_running, self.port = self.get_process_information()
    if self.is_running:
      FactorioServer.used_ports.append(self.port)
      print(f"started '{self.name}' on port {self.port}")
    else:
      print(f"cant find process for '{self.name}'")
      print(f"read {self.dir}/factorio-current.log")
      return
    return

  def restart(self):
    if self.is_running:
      self.stop()
      self.start()
    else:
      print(f"server {self.name} is not running. Not going to restart it")
    return

  def stop(self):
    if self.is_running:
      print(f"stopping server '{self.name}'")
      p = psutil.Process(self.pid)
      p.terminate()
      while p.is_running():
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(0.2)
      print(f"stopped")
      FactorioServer.used_ports = [port for port in FactorioServer.used_ports if port != self.port]
      return
    print(f"Server {self.name} is not running")
    return

  def update(self):
    print(f"updating '{self.name}'")
    was_running = False
    if not self.check_if_updates_folder_is_ready():
      return
    if self.find_latest_version() == self.version:
      print("server is already up to date")
      return
    if self.is_running:
      was_running = True
      print("server is running. stopping it")
      self.stop()
    # get list of updates
    current_version = self.version
    available_updates = json.loads(requests.get(FactorioServer.updater_url).content)["core-linux_headless64"][:-1]
    download_links = []
    while current_version != self.find_latest_version():
      for update in available_updates:
        if update["from"] == current_version:
          download_links.append(f"{FactorioServer.download_url}?username={self.settings['username']}&token={self.settings['token']}&apiVersion=2&from={update['from']}&to={update['to']}&package=core-linux_headless64")
          current_version = update["to"]
    # actually download the updates
    num_updates = len(download_links)
    i = 0
    for download_link in download_links:
      print(" downloading patch {}/{}".format(i+1, num_updates))
      response = requests.get(download_link)
      update_link = json.loads(response.content)[0]
      response = requests.get(update_link)
      with open("updates/" + str(i) + ".zip", "wb") as update_download:
        update_download.write(response.content)
      i = i + 1
    # apply the updates
    for j in range(i):
        try:
            print(" patching {}/{}".format(j+1,num_updates))
            subprocess.check_output(f"{self.exe_dir}/factorio --apply-update updates/{j}.zip".split())
        except subprocess.CalledProcessError as ex:
            print(ex.output)
            raise
        os.remove(f"updates/{j}.zip")
    print("Finished. Printing executable version:")
    print(self.get_factorio_version())
    if was_running:
      print("server was running prior to updates. starting it again")
      self.start()
    return

  def update_mods(self):
    mods_changed = 0
    print(f"updating mods of '{self.name}'")
    # check if any mods need to be updated
    if not os.path.isfile(f"{self.dir}/mods/mod-list.json"):
      print(f" - no mod-list.json found. cant update mods")
      return
    with open(f"{self.dir}/mods/mod-list.json", "r") as mlf:
      mod_names = [mod["name"] for mod in json.load(mlf)["mods"] if mod["name"] != "base" and mod["enabled"] == True]
    for mod in mod_names:
      latest_version = FactorioServer.get_latest_modrelease_by_modname(mod)
      if latest_version is None:
        print(f" - error retrieving latest version of '{mod}'. not updating")
        continue
      if os.path.isfile(f"{self.dir}/mods/{latest_version['file_name']}"):
        continue
      # download latest version. if successful, delete other versions
      print(f" - updating {mod}")
      try:
        response = requests.get(f"https://mods.factorio.com/{latest_version['download_url']}?username={self.settings['username']}&token={self.settings['token']}")
        with open(f"{self.dir}/mods/{latest_version['file_name']}", "wb") as downloaded_mod:
          downloaded_mod.write(response.content)
          mods_changed = mods_changed + 1
      except:
        print(f" - there was an error downloading {mod}. aborting update")
        continue
      for installed_mod in [m for m in os.listdir(f"{self.dir}/mods") if m.find(latest_version['file_name']) == -1]:
        if installed_mod.startswith(f"{mod}_"):
          os.remove(f"{self.dir}/mods/{installed_mod}")
    if mods_changed == 0:
      print(f"- no mods to update")
      return
    if self.is_running:
      print(f"- {self.name} is running. restart to make {mods_changed} mod updates take effect")
    return

  def __repr__(self):
    repr_lines = []

    s_running_short = "-" if not self.is_running else f"R"
    repr_lines.append(
      f"[{s_running_short}] {self.name}"
    )

    s_version = "" if self.version == self.find_latest_version() else f" update to {self.find_latest_version()} available"
    repr_lines.append(
      f"Version: {self.version}{s_version}"
    )

    repr_lines.append(
      f"Port: {self.port} | GameId: {self.game_id}"
    )

    if not self.save_exists:
      repr_lines.append(
        f"no savefile found in {self.dir}/saves"
      )

    if self.is_running:
      repr_lines.append(
        f"Players: {self.get_playercount()}"
      )

    if len(self.modlist) > 0:
      repr_lines.append("Mods: ")
      # repr_lines.append(",".join(self.modlist))
      for mod in self.modlist:
        repr_lines.append(f"  {mod}")

    repr_lines.append("")
    return "\n".join(repr_lines)