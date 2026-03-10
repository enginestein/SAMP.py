import asyncio
import socket
from .constants import *
from .exceptions import SampError, RconError, InvalidRconPassword, ConnectionError
from .models import ServerInfo, Rule, Client, ClientDetail, RConPlayer
from .utils import encode_bytes, decode_int, decode_string, build_rcon_command, parse_server_var


class AsyncUDPProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None
        self._recv_queue = asyncio.Queue()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        self._recv_queue.put_nowait(data)

    def error_received(self, exc):
        pass

    def sendto(self, data, addr):
        self.transport.sendto(data, addr)

    async def recvfrom(self, timeout=1.0):
        try:
            return await asyncio.wait_for(self._recv_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None


class SampClient(object):
    timeout = 1.0
    protocol_cls = AsyncUDPProtocol

    def __init__(self, address='127.0.0.1', port=7777, rcon_password=None):
        super(SampClient, self).__init__()
        assert isinstance(address, str)
        self.address = address
        self.port = int(port)
        self.rcon_password = rcon_password
        self._protocol = None
        self._transport = None

    async def connect(self):
        try:
            loop = asyncio.get_event_loop()
            self.address = await loop.run_in_executor(None, socket.gethostbyname, self.address)
            self.header = (
                MSG_PREFIX
                + encode_bytes(*map(int, self.address.split('.')))
                + encode_bytes(self.port & 0xFF, self.port >> 8 & 0xFF)
            )
            self._protocol = self.protocol_cls()
            self._protocol._recv_queue = asyncio.Queue()

            if self.protocol_cls is AsyncUDPProtocol:
                self._transport, _ = await loop.create_datagram_endpoint(
                    lambda: self._protocol,
                    remote_addr=(self.address, self.port),
                    family=socket.AF_INET,
                )
            return self
        except socket.error as e:
            raise ConnectionError(e)
        except OSError as e:
            raise ConnectionError(e)

    def disconnect(self):
        if self._transport:
            self._transport.close()
            self._transport = None
        self._protocol = None

    async def __aenter__(self):
        return await self.connect()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    async def send_request(self, opcode, extras=b'', return_response=True):
        body = self.header + opcode + extras
        self._protocol.sendto(body, (self.address, self.port))
        if return_response:
            return await self.receive()

    async def receive(self, strip_header=True):
        try:
            response = await self._protocol.recvfrom(timeout=self.timeout)
            if response is None:
                return None
            return response[11:] if strip_header else response
        except OSError as e:
            raise ConnectionError(e)

    async def get_server_info(self):
        response = await self.send_request(OPCODE_INFO)

        offset = 0
        hostname = decode_string(response, 5, 4)
        offset += len(hostname)
        gamemode = decode_string(response, offset + 9, 4)
        offset += len(gamemode)
        language = decode_string(response, offset + 13, 4)

        return ServerInfo(
            password=bool(response[0]),
            players=decode_int(response[1:3]),
            max_players=decode_int(response[3:5]),
            hostname=hostname,
            gamemode=gamemode,
            language=language,
        )

    async def get_server_rules(self):
        response = await self.send_request(OPCODE_RULES)
        num_rules = decode_int(response[:2])
        offset = 2
        result = []
        for n in range(num_rules):
            name = decode_string(response, offset, len_bytes=1)
            offset += 1 + len(name)
            value = decode_string(response, offset, len_bytes=1)
            offset += 1 + len(value)
            result.append(Rule(name=str(name), value=value))
        return result

    async def get_server_rules_dict(self):
        return {rule.name: rule.value for rule in await self.get_server_rules()}

    async def get_server_clients(self):
        response = await self.send_request(OPCODE_CLIENTS)
        result = []
        if response is None:
            return result
        num_clients = decode_int(response[:2])
        offset = 2
        for n in range(num_clients):
            name = decode_string(response, offset, len_bytes=1)
            offset += 1 + len(name)
            score = decode_int(response[offset:offset + 4])
            offset += 4
            result.append(Client(name=name, score=score))
        return result

    async def get_server_clients_detailed(self):
        response = await self.send_request(OPCODE_CLIENTS_DETAILED)
        result = []
        if response is None:
            return result
        num_clients = decode_int(response[:2])
        offset = 2
        for n in range(num_clients):
            player_id = decode_int(response[offset:offset])
            offset += 1
            name = decode_string(response, offset, len_bytes=1)
            offset += 1 + len(name)
            score = decode_int(response[offset:offset + 4])
            offset += 4
            ping = decode_int(response[offset:offset + 4])
            offset += 4
            result.append(ClientDetail(id=player_id, name=name, score=score, ping=ping))
        return result

    async def probe_server(self, value='ping'):
        if isinstance(value, str):
            value = bytes(value, ENCODING)
        assert len(value) == 4, 'Value must be exactly 4 characters'
        return await self.send_request(OPCODE_PSEUDORANDOM, extras=value)

    async def validate_server(self, value='ping'):
        response = await self.probe_server(value)
        if response != value:
            raise SampError('Server returned {} instead of {}'.format(response, value))

    async def is_online(self):
        value = b'test'
        try:
            return await self.probe_server(value=value) == value
        except ConnectionError:
            return False

    @property
    def rcon_password_bytes(self):
        if not self.rcon_password:
            raise RconError('Rcon password was not provided')
        pass_len = len(self.rcon_password)
        return encode_bytes(pass_len & 0xFF, pass_len >> 8 & 0xFF) + bytes(self.rcon_password, ENCODING)

    async def send_rcon_command(self, command, args=tuple(), fetch_response=True):
        command = build_rcon_command(command, args)
        command_length = encode_bytes(len(command) & 0xFF, len(command) >> 8 & 0xFF)
        payload = self.rcon_password_bytes + command_length + command
        await self.send_request(OPCODE_RCON, extras=payload, return_response=False)
        if fetch_response:
            result = []
            while True:
                response = await self.receive()
                if response is None:
                    break
                line = decode_string(response, 0, 2)
                if line:
                    result.append(line.lstrip())
                else:
                    break
            if len(result) == 1 and result[0] == 'Invalid RCON password.':
                raise InvalidRconPassword
            return result

    async def rcon_cmdlist(self):
        return (await self.send_rcon_command(RCON_CMDLIST))[1:]

    async def rcon_varlist(self):
        vars = (await self.send_rcon_command(RCON_VARLIST))[1:]
        return [parse_server_var(var) for var in vars]

    async def rcon_varlist_dict(self):
        return {var.name: var.value for var in await self.rcon_varlist()}

    async def rcon_exit(self):
        return await self.send_rcon_command(RCON_EXIT, fetch_response=False)

    async def rcon_echo(self, text):
        return (await self.send_rcon_command(RCON_ECHO, args=(text,)))[0]

    async def rcon_set_hostname(self, name):
        return await self.send_rcon_command(RCON_HOSTNAME, args=(name,), fetch_response=False)

    async def rcon_get_hostname(self):
        response = (await self.send_rcon_command(RCON_HOSTNAME))[0]
        return parse_server_var(response)

    async def rcon_set_gamemodetext(self, name):
        return await self.send_rcon_command(RCON_GAMEMODETEXT, args=(name,), fetch_response=False)

    async def rcon_get_gamemodetext(self):
        response = (await self.send_rcon_command(RCON_GAMEMODETEXT))[0]
        return parse_server_var(response)

    async def rcon_set_mapname(self, name):
        return await self.send_rcon_command(RCON_MAPNAME, args=(name,), fetch_response=False)

    async def rcon_get_mapname(self):
        response = (await self.send_rcon_command(RCON_MAPNAME))[0]
        return parse_server_var(response)

    async def rcon_exec(self, filename):
        response = await self.send_rcon_command(RCON_EXEC, args=(filename,))
        if len(response) == 1:
            raise SampError(response[0])
        return response

    async def rcon_kick(self, player_id):
        return await self.send_rcon_command(RCON_KICK, args=(player_id,))

    async def rcon_ban(self, player_id):
        return await self.send_rcon_command(RCON_BAN, args=(player_id,))

    async def rcon_banip(self, ip_address):
        return await self.send_rcon_command(RCON_BANIP, args=(ip_address,))

    async def rcon_unbanip(self, ip_address):
        return await self.send_rcon_command(RCON_UNBANIP, args=(ip_address,))

    async def rcon_changemode(self, mode):
        return await self.send_rcon_command(RCON_CHANGEMODE, args=(mode,))

    async def rcon_gmx(self):
        return await self.send_rcon_command(RCON_GMX)

    async def rcon_reloadbans(self):
        return await self.send_rcon_command(RCON_RELOADBANS)

    async def rcon_reloadlog(self):
        return await self.send_rcon_command(RCON_RELOADBANS)

    async def rcon_say(self, message):
        return await self.send_rcon_command(RCON_SAY, args=(message,))

    async def rcon_players(self):
        result = []
        for line in (await self.send_rcon_command(RCON_PLAYERS))[1:]:
            player_id, name, ping, ip = line.split('\t')
            result.append(RConPlayer(id=int(player_id), name=str(name), ping=int(ping), ip=str(ip)))
        return result

    async def rcon_gravity(self, gravity=0.008):
        return await self.send_rcon_command(RCON_GRAVITY, args=(gravity,))

    async def rcon_weather(self, weather):
        return await self.send_rcon_command(RCON_WEATHER, args=(weather,))

    async def rcon_loadfs(self, name):
        response = (await self.send_rcon_command(RCON_LOADFS, args=(name,)))[0]
        if 'load failed' in response:
            raise SampError(response)
        return response

    async def rcon_unloadfs(self, name):
        response = (await self.send_rcon_command(RCON_UNLOADFS, args=(name,)))[0]
        if 'unload failed' in response:
            raise SampError(response)
        return response

    async def rcon_reloadfs(self, name):
        response = await self.send_rcon_command(RCON_RELOADFS, args=(name,))
        if 'load failed' in response[-1]:
            raise SampError(response[-1])
        return response

    async def rcon_get_weburl(self):
        response = (await self.send_rcon_command(RCON_WEBURL))[0]
        return parse_server_var(response)

    async def rcon_set_weburl(self, url):
        return await self.send_rcon_command(RCON_WEBURL, args=(url,))

    async def rcon_set_rcon_password(self, password):
        await self.send_rcon_command(RCON_RCON_PASSWORD, args=(password,))
        self.rcon_password = password

    async def rcon_get_rcon_password(self):
        response = (await self.send_rcon_command(RCON_RCON_PASSWORD))[0]
        return parse_server_var(response)

    async def rcon_get_password(self):
        response = (await self.send_rcon_command(RCON_PASSWORD))[0]
        return parse_server_var(response)

    async def rcon_set_password(self, password):
        return (await self.send_rcon_command(RCON_PASSWORD, args=(password,)))[0]

    async def rcon_get_messageslimit(self):
        response = (await self.send_rcon_command(RCON_MESSAGESLIMIT))[0]
        return parse_server_var(response)

    async def rcon_set_messageslimit(self, limit):
        return await self.send_rcon_command(RCON_MESSAGESLIMIT, args=(limit,), fetch_response=False)

    async def rcon_get_ackslimit(self):
        response = (await self.send_rcon_command(RCON_ACKSLIMIT))[0]
        return parse_server_var(response)

    async def rcon_set_ackslimit(self, limit):
        return await self.send_rcon_command(RCON_ACKSLIMIT, args=(limit,), fetch_response=False)

    async def rcon_get_messageholelimit(self):
        response = (await self.send_rcon_command(RCON_MESSAGEHOLELIMIT))[0]
        return parse_server_var(response)

    async def rcon_set_messageholelimit(self, limit):
        return await self.send_rcon_command(RCON_MESSAGEHOLELIMIT, args=(limit,), fetch_response=False)

    async def rcon_get_playertimeout(self):
        response = (await self.send_rcon_command(RCON_PLAYERTIMEOUT))[0]
        return parse_server_var(response)

    async def rcon_set_playertimeout(self, limit):
        return await self.send_rcon_command(RCON_PLAYERTIMEOUT, args=(limit,), fetch_response=False)

    async def rcon_get_language(self):
        response = (await self.send_rcon_command(RCON_LANGUAGE))[0]
        return parse_server_var(response)

    async def rcon_set_language(self, limit):
        return await self.send_rcon_command(RCON_LANGUAGE, args=(limit,), fetch_response=False)