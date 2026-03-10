import asyncio
from src.client import SampClient


async def test_server():
    print("Connecting to SA:MP server...\n")

    async with SampClient("127.0.0.1", 7777, rcon_password="password") as client:

        online = await client.is_online()
        print("Server online:", online)

        if not online:
            print("Server is offline")
            return

        print("\n--- SERVER INFO ---")
        info = await client.get_server_info()

        print("Hostname:", info.hostname)
        print("Players:", f"{info.players}/{info.max_players}")
        print("Gamemode:", info.gamemode)
        print("Language:", info.language)
        print("Password protected:", info.password)

        print("\n--- SERVER RULES ---")
        rules = await client.get_server_rules()
        for rule in rules:
            print(f"{rule.name}: {rule.value}")

        print("\n--- PLAYERS ---")
        players = await client.get_server_clients()

        if not players:
            print("No players online")
        else:
            for p in players:
                print(f"{p.name} | score: {p.score}")

        print("\n--- DETAILED PLAYERS ---")
        detailed = await client.get_server_clients_detailed()

        if not detailed:
            print("No players online")
        else:
            for p in detailed:
                print(f"ID:{p.id} {p.name} score:{p.score} ping:{p.ping}")

        print("\n--- PROBE TEST ---")
        probe = await client.probe_server(b"test")
        print("Probe response:", probe)

        print("\n--- RCON TEST ---")

        try:
            cmds = await client.rcon_cmdlist()
            print("Available RCON commands:", len(cmds))
            print(cmds[:10])  # show first few
        except Exception as e:
            print("RCON error:", e)


if __name__ == "__main__":
    asyncio.run(test_server())