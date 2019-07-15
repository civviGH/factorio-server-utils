"""
Factorio Server information:
  is_running
  version (up to date?)
  bindip
  port
  pid
  modlist + versionen (are updates available?)
  needed file existent?
    server-settings
    server-whitelist
  does --start-server-load-latest work? (eg save file existent?)

Options:
  start
  stop
  getinfo (__repr__)
  update
  update mods
"""

import psutil, re, subprocess, socket, os, jinja2, time, json, sys

class FactorioServer:

  used_ports = []

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
    print("started")
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
      print("stopped")
      return
    print(f"Server {self.name} is not running")
    return

  def update(self):
    #TODO
    return

  def update_mods(self):
    #TODO
    return

  def __repr__(self):
    #TODO pprint
    s_exists = "" if self.save_exists else " not"
    return f'''
    {self.name}
    Version: {self.version}
    (running={self.is_running} with pid {self.pid})
    Port: {self.port}
    Saves do{s_exists} exist
    '''
