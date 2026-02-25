import asyncio
import websockets

async def websocket_client():
    # Demande de l'adresse au démarrage
    host = input("Entrez l'adresse IP ou le hostname du serveur WebSocket (ex: 192.168.1.10:8765): ").strip()

    # Construction de l'URL WS
    if not host.startswith("ws://") and not host.startswith("wss://"):
        uri = f"ws://{host}"
    else:
        uri = host

    print(f"Tentative de connexion à {uri} ...")

    try:
        async with websockets.connect(uri) as websocket:
            print("Connecté au serveur WebSocket.")
            print("En attente de messages...\n")

            while True:
                try:
                    message = await websocket.recv()
                    print("Message reçu :", message)

                except websockets.exceptions.ConnectionClosed:
                    print("Connexion fermée par le serveur.")
                    break

    except Exception as e:
        print("Erreur de connexion :", e)


if __name__ == "__main__":
    asyncio.run(websocket_client())