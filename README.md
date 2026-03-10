# SAMP.py
[![Downloads](https://static.pepy.tech/badge/samp-python)](https://pepy.tech/project/samp-python/)

SAMP.py is a GTA SA:MP RCON and query client for Python with full **async/await** support.

> **Note:** As of the latest version, all client methods are asynchronous. Use `async with` and `await` throughout your code.

---

# Installation

```bash
pip install samp-python
```

# Requirements

- Python 3.8+

---

# Usage

All interactions with `SampClient` are now completely asynchronous. Use `async with` to manage the connection and `await` every method call.

### Basic query

```python
import asyncio
from samp_py.client import SampClient

async def main():
    async with SampClient(address='localhost', port=7777) as client:
        info = await client.get_server_info()
        print(info)

asyncio.run(main())
```

### Running RCON commands

```python
import asyncio
from samp_py.client import SampClient

async def main():
    async with SampClient(address='localhost', port=7777, rcon_password='password') as client:
        await client.rcon_cmdlist()

asyncio.run(main())
```

### Accessing query and RCON responses

```python
import asyncio
from samp_py.client import SampClient

async def main():
    async with SampClient(address='localhost', port=7777, rcon_password='password') as client:
        info = await client.get_server_info()
        print(info)
        print(info.gamemode)
        print(await client.rcon_get_hostname())
        players = await client.rcon_players()
        print(players[0].ping)

asyncio.run(main())
```

---

# Exceptions

| Exception              | Description                                      |
|------------------------|--------------------------------------------------|
| `SampError`            | General SA:MP error                             |
| `RconError`            | RCON is unavailable or password not provided    |
| `InvalidRconPassword`  | The RCON password is incorrect                  |
| `ConnectionError`      | Could not connect to the server                 |

---

# Full Example

Below is a complete interactive SAMP.py script updated for async:

```python
import sys
import asyncio
from builtins import input
from samp_py.client import SampClient


async def info(client):
    server_info = await client.get_server_info()
    print("""Server Info:
Password: {info.password}
Players: {info.players}/{info.max_players}
Hostname: {info.hostname}
Gamemode: {info.gamemode}
Language: {info.language}
    """.format(info=server_info))


async def rules(client):
    print("Server Rules:")
    for rule in await client.get_server_rules():
        print("{rule.name}: {rule.value}".format(rule=rule))


async def clients(client):
    print("Connected Clients")
    print("Name                       | Score")
    print("==================================")
    for c in await client.get_server_clients():
        print("{client.name:26} | {client.score}".format(client=c))


async def details(client):
    print("Detailed Clients")
    print(" ID | Name                       | Score | Ping")
    print("================================================")
    for c in await client.get_server_clients_detailed():
        print("{client.id:3} | {client.name:26} | {client.score:5} | {client.ping:4}".format(client=c))


async def rcon(client):
    if client.rcon_password is None:
        client.rcon_password = input('RCON password: ')
    print('Enter rcon commands or leave blank to exit. Example: cmdlist')
    while True:
        command = input('RCON: ')
        if not command:
            return
        for line in await client.send_rcon_command(command):
            print(line)


async def main(args):
    async with SampClient(*args) as client:
        if not await client.is_online():
            print('Server {}:{} is offline'.format(*args))
            exit(1)

        server_info = await client.get_server_info()
        print("""Connected to {info.hostname}.
Currently {info.players}/{info.max_players} players online.
Select one of the options:
i. Server Info
r. Server Rules
c. Connected clients
d. Detailed clients
x. RCON
""".format(info=server_info))

        options = {
            'i': info,
            'r': rules,
            'c': clients,
            'd': details,
            'x': rcon,
        }

        option = input('Select option: ')
        if option in options:
            await options[option](client)
        else:
            print('Unknown option, bye!')


if len(sys.argv) < 3:
    print('Usage: py example.py [server_address] [port]')
    exit(1)

asyncio.run(main(sys.argv[1:]))
```

---

# API Reference

### `SampClient(address, port, rcon_password)`

| Parameter       | Type    | Default       | Description                        |
|-----------------|---------|---------------|------------------------------------|
| `address`       | `str`   | `'127.0.0.1'` | Server hostname or IP address      |
| `port`          | `int`   | `7777`        | Server port                        |
| `rcon_password` | `str`   | `None`        | RCON password (required for RCON)  |

### Connection

| Method                         | Description                                      |
|--------------------------------|--------------------------------------------------|
| `await client.connect()`       | Connect to the server (called by `async with`)  |
| `client.disconnect()`          | Close the connection                             |

### Query Methods

| Method                                   | Returns         |
|------------------------------------------|-----------------|
| `await client.get_server_info()`         | `ServerInfo`    |
| `await client.get_server_rules()`        | `list[Rule]`    |
| `await client.get_server_rules_dict()`   | `dict`          |
| `await client.get_server_clients()`      | `list[Client]`  |
| `await client.get_server_clients_detailed()` | `list[ClientDetail]` |
| `await client.is_online()`               | `bool`          |
| `await client.probe_server(value)`       | `bytes`         |

### RCON Methods

| Method                                        | Description                        |
|-----------------------------------------------|------------------------------------|
| `await client.rcon_cmdlist()`                 | List available RCON commands       |
| `await client.rcon_varlist()`                 | List server variables              |
| `await client.rcon_varlist_dict()`            | Server variables as a dict         |
| `await client.rcon_players()`                 | List connected players             |
| `await client.rcon_kick(player_id)`           | Kick a player by ID                |
| `await client.rcon_ban(player_id)`            | Ban a player by ID                 |
| `await client.rcon_banip(ip_address)`         | Ban an IP address                  |
| `await client.rcon_unbanip(ip_address)`       | Unban an IP address                |
| `await client.rcon_say(message)`              | Broadcast a message                |
| `await client.rcon_echo(text)`                | Echo text to the server console    |
| `await client.rcon_exec(filename)`            | Execute a server config file       |
| `await client.rcon_changemode(mode)`          | Change the game mode               |
| `await client.rcon_gmx()`                     | Restart the game mode              |
| `await client.rcon_gravity(gravity)`          | Set server gravity                 |
| `await client.rcon_weather(weather)`          | Set server weather                 |
| `await client.rcon_loadfs(name)`              | Load a filterscript                |
| `await client.rcon_unloadfs(name)`            | Unload a filterscript              |
| `await client.rcon_reloadfs(name)`            | Reload a filterscript              |
| `await client.rcon_get_hostname()`            | Get the server hostname            |
| `await client.rcon_set_hostname(name)`        | Set the server hostname            |
| `await client.rcon_get_language()`            | Get the server language            |
| `await client.rcon_set_language(language)`    | Set the server language            |
| `await client.rcon_get_password()`            | Get the server password            |
| `await client.rcon_set_password(password)`    | Set the server password            |
| `await client.rcon_get_rcon_password()`       | Get the RCON password              |
| `await client.rcon_set_rcon_password(password)` | Set the RCON password            |
| `await client.rcon_exit()`                    | Shut down the server               |
| `await client.send_rcon_command(command)`     | Send a raw RCON command            |