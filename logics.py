import paramiko
import requests
import json
import subprocess
import asyncio
import os


async def startserver(server):
    if server == "rgb":
        server_ip = "192.168.178.201"
        location = '/home/ridderleeuw/wakeonlan/wakonrgb.run'
    elif server == "old":
        server_ip = "192.168.178.202"
        location = '/home/ridderleeuw/wakeonlan/wakonold.run'

    if await server_status(server_ip):
        print("Server is al online.")
        return True

    print("Server is offline, start wake-on-lan script...")
    proc = await asyncio.create_subprocess_exec(   #wake on lan script
        '/bin/bash', location,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL)
    await proc.wait()

    # Wacht tot server online komt
    print("Wacht tot server online komt...")
    start_time = asyncio.get_event_loop().time()
    timeout = 240
    while asyncio.get_event_loop().time() - start_time < timeout:
        if await server_status(server_ip):
            print("Server is nu online.")
            await asyncio.sleep(10)
            return True
        await asyncio.sleep(3)

    print("Timeout bereikt. Server kwam niet online.")
    return False

async def server_status(server_ip):
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", server_ip,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        return proc.returncode == 0
    except Exception:
        return False




rgbToken = None
oldToken = None

def tokens(rgb, old):
    global rgbToken, oldToken
    rgbToken = rgb
    oldToken = old

async def ssh_request_async(server, command): #wrapper voor de ssh_request
        if server == "rgb":
            password = rgbToken
            ip = "192.168.178.201"
            keylocation = '/home/ridderleeuw/.ssh_key/new_server_scriprunner/scriprunner'
            user = 'scriprunner'
        elif server == "old":
            password = oldToken
            ip = "192.168.178.202"
            keylocation = '/home/ridderleeuw/.ssh_key/old_server/old_server_key'
            user = 'ridderleeuw'
        else: #catch
            return None, "Server not found."
        status_result = await server_status(ip)
        if not status_result:
            print(f"Server {server} is offline.")
            return None, "Server is offline."
        print(f"stuurt command naar ssh_request. Inhoud: {server}: {command}")
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, ssh_request, ip, user, keylocation, password, command)


def ssh_request(ip, user, keylocation, password, command): #wrapper ^^ daarom geen async
    print(f"command binnen bij ssh {ip}: {command}") #kaan ook geen async ivm paramiko

    
    try: #ssh connection
        print(f"SSH verbinding maken met {ip} als {user}, server {ip}")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        private_key = paramiko.RSAKey.from_private_key_file(keylocation, password=password)
        ssh_client.connect(ip, 22, user, pkey=private_key)


        stdin, stdout, stderr = ssh_client.exec_command(command, get_pty=False)
        exit_status = stdout.channel.recv_exit_status()
        stdout_data = stdout.read().decode('utf-8').strip()
        stderr_data = stderr.read().decode('utf-8').strip()
        ssh_client.close()

        if exit_status == 0:
            print(f"SSH succesvol uitgevoerd met exit code {exit_status}.\nstdout: {stdout_data}\nstderr: {stderr_data}")
            return stdout_data, None
        else:
            print(f"SSH mislukt met exit code {exit_status}.\nstdout: {stdout_data}\nstderr: {stderr_data}")
            return None, f"SSH mislukt met exit code {exit_status}.\nstdout: {stdout_data}\nstderr: {stderr_data}"
    except Exception as e:
        return None, f"Fout tijdens SSH-verbinding: {str(e)}"
    
async def shutdownserver(server):
    if server == "rgb":
        stdout, error = await ssh_request_async("rgb", "sudo shutdown +1")
        print("rgb server is nu uitgeschakeld.")
        return stdout, error

    elif server == "old":
        stdout, error = await ssh_request_async("old", "sudo shutdown +1")
        print("old server is nu uitgeschakeld.")
        return stdout, error

    elif server == "m1": #local
        subprocess.run(["shutdown", "-h", "+1"])
        print("m1 server is nu uitgeschakeld.")
        return None, None

    else:  # ongeldige servernaam
        return None, "Server niet gevonden."

async def screen_check():
    output, error = await ssh_request_async("rgb", "screen -list")
    if error:
        print(f"Fout bij het ophalen van screen-sessies: {error}")
        return False

    active_session = []
    for line in output.splitlines():
        if '\t' in line and ('Detached' in line or 'Attached' in line):
            parts = line.strip().split('\t')
            if parts:
                active_session.append(parts[0])

    if active_session:
        print("Actieve screen-sessies gevonden:", active_session)
        return True, active_session
    else:
        print("Geen actieve screen-sessies gevonden.")
        return False

# controlleer of er nog speler op de server zit.
async def check_players():         ##werkt niet omdat de screen output niet gestreamline kan worden naar de script. (de ssh klopt ook niet heeft geen screen name)
    output, error = await ssh_request_async("rgb", "screen -r -X stuff 'list\n'")
    if error:
        print(f"Fout bij het ophalen van spelers: {error}")
        return None

    if output == None:
        print("Geen spelers gevonden.")
        return False
    if output != None:
        print("Geen spelers gevonden.")
        return True



async def whitelist_logic(playername):
    url = f'https://api.mojang.com/users/profiles/minecraft/{playername}'
    response = requests.get(url)

    if response.status_code == 200:
        player_data = response.json()
        whitelist = []
        if os.path.exists('whitelist.json'):
            with open('whitelist.json', 'r') as file:
                try:
                    whitelist = json.load(file)
                except json.JSONDecodeError:
                    whitelist = []

        # Check of speler al in whitelist staat (op naam of id)
        whitelist = [entry for entry in whitelist if isinstance(entry, dict)]
        already_in_whitelist = any(
            entry.get('name') == player_data['name'] or entry.get('id') == player_data['id']
            for entry in whitelist
        )


        if already_in_whitelist:
            return f"Player {player_data['name']} staat al in de whitelist."

        whitelist.append(player_data)
        with open('whitelist.json', 'w') as file:
            json.dump(whitelist, file, indent=4)

        if not await server_status("rgb"):
            print("RGB offline, save in whitelist.json")
            return f"Player data saved to whitelist.json: {player_data}"
        else:
            await whitelist_update()
        return f"Player data saved to whitelist.json: {player_data}"
    else:
        return f"Failed to fetch player data. Status code: {response.status_code}"

async def whitelist_update():  # Update whitelist.json on the RGB server
    servers = await discover_Minecraft_servers(purpose="whitelist")  # Get all whitelist.json paths on the server

    if not servers:
        print("No servers found to update whitelist.json.")
        return

    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        private_key = paramiko.RSAKey.from_private_key_file('/home/ridderleeuw/.ssh_key/rgb_server/rgb_server_key', password=rgbToken)
        ssh_client.connect("192.168.178.201", 22, "scriprunner", pkey=private_key)

        # SFTP setup
        sftp = ssh_client.open_sftp()

        # Upload whitelist.json to each server directory
        for servername, remote_path in servers.items():
            print(f"Updating whitelist.json for server: {servername}")
            try:
                sftp.put('whitelist.json', remote_path)  # Upload the file
                print(f"Successfully updated whitelist.json for {servername}.")
            except Exception as e:
                print(f"Failed to update whitelist.json for {servername}: {str(e)}")

        # Close SFTP and SSH connections
        sftp.close()
        ssh_client.close()

    except Exception as e:
        print(f"Error during whitelist update: {str(e)}")


async def discover_Minecraft_servers(purpose):
    
    servers = {}
    # Get the directory tree from RGB server
    output, error = await ssh_request_async("rgb", "tree -fiL 2 /home/ridderleeuw/minecraft")
    print("Output from RGB:", output)

    if error and not output:
        print("Error during SSH:", error)
        return error

    if purpose == "minecraft_autodiscovery":
        for line in output.splitlines():
            if "start.sh" in line or "run.sh" in line:
                full_path = line.strip()
                script_name = "start.sh" if "start.sh" in full_path else "run.sh"
                servername = os.path.basename(os.path.dirname(full_path))
                if servername not in servers:
                    servers[servername] = full_path
                    print(f"Server {servername} gevonden met script {script_name}.")

        try:
            if servers != await load_discovered_servers():
                print("New servers discovered:", servers)
                await save_discovered_servers(servers)
        except Exception as e:
            print("Fout bij opslaan discovered servers:", e)

    if purpose == "whitelist":
        for line in output.splitlines():
            if "whitelist.json" in line:
                full_path = line.strip()
                servername = os.path.basename(os.path.dirname(full_path))
                if servername not in servers:
                    servers[servername] = full_path
                    print(f"Server {servername} gevonden met whitelist.json op pad: {full_path}")
    return servers

# autodiscovery of servers 
async def load_discovered_servers():
    try:
        with open("discover_mc_server.json", "r") as f:
            content = f.read()
            if not content.strip():  # bestand is leeg
                print("discover_mc_server.json is leeg.")
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Fout bij laden van JSON: {e}")
        return {}

        
async def save_discovered_servers(servers):
    with open("discover_mc_server.json", "w") as f:
        json.dump(servers, f, indent=4)


# steam
async def palword():
    await ssh_request_async("old, ")
    print("palword")
