# SAMP.py

SAMP.py is a GTA SA:MP RCON and query client for Python.

# Installation

```bash
pip install samp-python
```

# Usage

You can initalize a client like this:

```py
from samp_py.client import SampClient

with SampClient(address='localhost', port=7777) as client:
    print(client.get_server_info())
```

To run RCON commands:

```py
with SampClient(address='localhost', port=7777, rcon_password='password') as client:
    client.rcon_cmdlist()
```

Query and RCON responses can be accessed following the native route:

```py
with SampClient(address='localhost', port=7777, rcon_password='password') as client:
    info = client.get_server_info()
    print(info)
    print(info.gamemode)
    print(client.rcon_get_hostname())
    print(client.rcon_players()[0].ping)
```

There are not many exceptions:

- SampError
- RconError
- InvalidRconPassword
- ConnectionError

Here is an whole example of a SAMP.py script

```py
import sys
from builtins import input

from samp_py.client import SampClient


def info(client):
    print("""Server Info:
Password: {info.password}
Players: {info.players}/{info.max_players}
Hostname: {info.hostname}
Gamemode: {info.gamemode}
Language: {info.language}
    """.format(
        info=client.get_server_info(),
    ))


def rules(client):
    print("Server Rules:")
    for rule in client.get_server_rules():
        print("{rule.name}: {rule.value}".format(
            rule=rule,
        ))


def clients(client):
    print("Connected Clients")
    print("Name                       | Score".format(client=client))
    print("==================================")
    for client in client.get_server_clients():
        print("{client.name:26} | {client.score}".format(client=client))


def details(client):
    print("Detailed Clients")
    print(" ID |Name                        | Score | Ping".format(client=client))
    print("===============================================")
    for client in client.get_server_clients_detailed():
        print("{client.id:3} | {client.name:26} | {client.score:5} | {client.ping:4}".format(client=client))


def rcon(client):
    if client.rcon_password is None:
        client.rcon_password = input('RCON password:')
    print('Enter rcon commands or leave blank to exit. Example: cmdlist')
    while True:
        command = input('RCON: ')
        if not command:
            return
        for line in client.send_rcon_command(command):
            print(line)


def main(args):
    with SampClient(*args) as client:
        if not client.is_online():
            print('Server {}:{} is offline'.format(*args))
            exit(1)
        server_info = client.get_server_info()
        print("""Connected to {info.hostname}. 
Currently {info.players}/{info.max_players} players online.

Select one of the options:

i. Server Info
r. Server Rules
c. Connected clients
d. Detailed clients
x. RCON
""".format(
            info=server_info,
        ))

        options = {
            'i': info,
            'r': rules,
            'c': clients,
            'd': details,
            'x': rcon,
        }
        option = input('Select option: ')
        if option in options: options[option](client)
        else: print('Unknown option, bye!')


if len(sys.argv) < 3:
    print('Usage: py example.py [server_address] [port]')
    exit(1)
main(sys.argv[1:])
```
