import asyncio
from unittest import IsolatedAsyncioTestCase

from src.client import SampClient
from src.exceptions import ConnectionError
from src.models import ServerInfo, Rule, Client, ClientDetail
from mock import MockSocket


class ClientTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = SampClient(address='server.convoytrucking.net')
        self.client.protocol_cls = MockSocket
        await self.client.connect()

    async def asyncTearDown(self):
        self.client.disconnect()

    async def test_server_ip(self):
        self.assertNotEqual('server.convoytrucking.net', self.client.address)
        self.assertEqual('51.254.130.14', self.client.address)

    async def test_server_info(self):
        info = await self.client.get_server_info()
        self.assertIsNotNone(info)
        self.assertIsInstance(info, ServerInfo)
        self.assertIsInstance(info.password, bool)
        self.assertIsInstance(info.players, int)
        self.assertIsInstance(info.max_players, int)
        self.assertIsInstance(info.hostname, str)
        self.assertIsInstance(info.gamemode, str)
        self.assertIsInstance(info.language, str)

        self.assertTrue(info.max_players)
        self.assertTrue(info.hostname)
        self.assertTrue(info.gamemode)
        self.assertTrue(info.language)

    async def test_server_rules(self):
        rules = list(await self.client.get_server_rules())
        self.assertEqual(6, len(rules))
        self.assertIsNotNone(rules)
        self.assertIsInstance(rules[0], Rule)

    async def test_server_rules_dict(self):
        rules = await self.client.get_server_rules_dict()
        self.assertIsNotNone(rules)
        self.assertIsInstance(rules, dict)
        self.assertIn('worldtime', rules)
        self.assertIn('mapname', rules)
        self.assertIn('version', rules)
        self.assertIn('weather', rules)

    async def test_server_clients(self):
        for client in await self.client.get_server_clients():
            self.assertIsInstance(client, Client)
            self.assertIsInstance(client.name, str)
            self.assertIsInstance(client.score, int)
            return

    async def test_server_clients_detailed(self):
        for client in await self.client.get_server_clients_detailed():
            self.assertIsInstance(client, ClientDetail)
            self.assertIsInstance(client.name, str)
            self.assertIsInstance(client.score, int)
            self.assertIsInstance(client.ping, int)
            self.assertIsInstance(client.id, int)
            return

    async def test_probe_server_unicode(self):
        self.assertEqual(b'test', await self.client.probe_server(u'test'))

    async def test_probe_server_bytestring(self):
        self.assertEqual(b'test', await self.client.probe_server(b'test'))

    async def test_is_online(self):
        self.assertTrue(await self.client.is_online())

    async def test_is_offline(self):
        async with SampClient(address='localhost', port=6666) as client:
            self.assertFalse(await client.is_online())

    async def test_is_invalid_domain(self):
        client = SampClient(address='localhostinvalid', port=6666)
        with self.assertRaises(ConnectionError):
            await client.connect()


if __name__ == "__main__":
    import unittest
    unittest.main()