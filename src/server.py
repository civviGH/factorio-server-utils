import psutil, re, subprocess, socket, os, jinja2, time, json, sys
import requests

class FactorioServer:

  used_ports = []
  updater_url = "https://updater.factorio.com/get-available-versions"
  download_url = "https://updater.factorio.com/get-download-link"
  latest_version = None

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
        regex = re.compile(r'--port\" \"\d+\"')
        with open(f"{self.dir}/factorio-current.log") as f:
          for line in f:
            result = regex.search(line)
            if result is not None:
              port = int(result.group(0).split()[1].strip("\""))
              return p['pid'], True, port
        return p['pid'], True, None
    return None, False, None

  def get_factorio_version(self):
    """Returns the version of the factorio executable"""
    return re.search("Version: (\d+\.\d+\.\d+)", str(subprocess.check_output([f"{self.exe_dir}/factorio", "--version"]))).group(1)

  def check_if_port_is_open(self, port):
    if port in FactorioServer.used_ports:
      print(f"port {port} in use. trying {port+1}")
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
    tcp_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_connection.bind(('', 0))
    addr, port = tcp_connection.getsockname()
    tcp_connection.close()
    return port

  def create_server_settings(self):
    j2 = jinja2.Environment(loader=jinja2.FileSystemLoader(f"{os.getcwd()}"))
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
    return

  def start(self):
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
    print(f"started server {self.name} on port {self.port}")
    FactorioServer.used_ports.append(self.port)
    return

  def restart(self):
    if self.is_running:
      self.stop()
    time.sleep(3)
    self.start()
    return

  def stop(self):
    if self.is_running:
      psutil.Process(self.pid).terminate()
      print(f"stopped server {self.name}")
      FactorioServer.used_ports = [port for port in FactorioServer.used_ports if port != self.port]
      return
    print(f"Server {self.name} is not running")
    return

  def update(self):
    print(f"updated '{self.name}'")
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
      print("downloading patch {}/{}".format(i+1, num_updates))
      response = requests.get(download_link)
      update_link = json.loads(response.content)[0]
      response = requests.get(update_link)
      with open("updates/" + str(i) + ".zip", "wb") as update_download:
        update_download.write(response.content)
      i = i + 1
    # apply the updates
    for j in range(i):
        try:
            print("patching {}/{}".format(j+1,num_updates))
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
    #TODO
    return

  def __repr__(self):
    #TODO pprint
    s_exists = "" if self.save_exists else " not"
    s_version = "" if self.version == self.find_latest_version() else f" update to {self.find_latest_version()} available"
    s_running = "stopped" if not self.is_running else f"STARTED with pid {self.pid}"
    return f'''
{self.name}
Version: {self.version}{s_version}
{s_running}
Port: {self.port}
Saves do{s_exists} exist
    '''
