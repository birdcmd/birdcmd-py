import websocket
import time
import argparse
import os
import pdb
import json
# websocket.enableTrace(True)

class CommandChannel(object):
    def __init__(self, token, uuid):
        self.token = token
        self.uuid = uuid

        self.connect_msg = {
            "command": "subscribe",
            "identifier": json.dumps({
                "channel": "CommandChannel",
                "tunnel": self.uuid
            })
        }

    def start(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        self.wsapp = websocket.WebSocketApp("wss://eckoproject.com/cable",
                                    header=headers,
                                    on_message=self.on_message,
                                    on_open=self.on_open,
                                    on_close=self.on_close,
                                    on_reconnect=self.on_reconnect,
                                    on_error=self.on_error)
        self.wsapp.run_forever(reconnect=5)


    def on_message(self, wsapp, message):
        msg = json.loads(message)
        if msg.get("type") == "ping":
            # print("ping type")
            return
        print(msg)
        if msg.get("type") == "reject_subscription":
            print("Connection is refused, please make sure your token/uuid is correct and your account is valid. Exiting.")
            wsapp.close()
        if msg.get("type") == "confirm_subscription":
            print("You're connected to tunnel.")
        if msg.get("type") == "disconnect":
            if (msg.get("reason") == "server_restart" and msg.get("reconnect") == True):
                print("Reconnecting in 5")
                wsapp.close()
                time.sleep(5)
                self.start()
        if msg.get("identifier"):
            ids = json.loads(msg.get("identifier"))
            if ids.get("channel") == "CommandChannel":
                cmd = msg.get("message", {}).get("command")
                if cmd:
                    os.system(cmd)

    def on_error(self, wsapp, error):
        print("Error: " + str(error))

    def on_reconnect(self, wsapp):
        print("Reconnected to server.")
        wsapp.send(json.dumps(self.connect_msg))

    def on_open(self, wsapp):
        print("Connected to server.")
        wsapp.send(json.dumps(self.connect_msg))

    def on_close(self, wsapp, close_status_code, close_msg):
        print("On_close args:")
        if close_status_code or close_msg:
            print("close status code: " + str(close_status_code))
            print("close message: " + str(close_msg))

def main():
    parser = argparse.ArgumentParser(description='Input your uuid and token')
    parser.add_argument('-c', type=str, metavar="Config", required=True, help="Format is TOKEN:UUID")
    args = parser.parse_args()
    token, uuid = args.c.split(":")
    app = CommandChannel(token=token, uuid=uuid)
    app.start()

if __name__ == "__main__":
    main()
