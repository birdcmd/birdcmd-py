import websocket
import time
import argparse
import os
import pdb
import json
import threading
import random
import string
# websocket.enableTrace(True)

class CommandChannel(object):
    def __init__(self, token, uuid, dev_mode):
        self.token = token
        self.uuid = uuid
        self.dev_mode = dev_mode

        self.connect_msg = json.dumps({
            "command": "subscribe",
            "identifier": json.dumps({
                "channel": "CommandChannel",
                "tunnel": self.uuid
            })
        })

        self.heartbeat_msg = json.dumps({
            "command": "message",
            "identifier": json.dumps({
                "channel": "CommandChannel",
                "tunnel": self.uuid
            }),
            "data": json.dumps({
                "action": "heartbeat_ping"
            })
        })

        if self.dev_mode:
            self.ws_URI = "ws://localhost:3000/cable"
            self.HEARTBEAT_INTERVAL = 5
            self.SLEEP_MIN = 1
            self.SLEEP_MAX = 1
        else:
            self.ws_URI = "wss://www.birdcmd.com/cable"
            self.HEARTBEAT_INTERVAL = 45
            self.SLEEP_MIN = 1
            self.SLEEP_MAX = 10


    def start(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        self.wsapp = websocket.WebSocketApp(self.ws_URI,
                                    header=headers,
                                    on_message=self.on_message,
                                    on_open=self.on_open,
                                    on_close=self.on_close,
                                    on_reconnect=self.on_reconnect,
                                    on_error=self.on_error)
        self.wsapp.run_forever(reconnect=5)


    def send_heartbeat(self, *args):
        """
        Sends a ping to the heartbeat_ping method every 30+X seconds.
        Failing to send a heartbeat won't stop you from receiving commands from the server,
        it's just that you won't see a green dot indicating your tunnel is online.

        args:
          running_hb_thread_id: every time on_open/on_reconnect, a heartbeat thread is spawn.
          to prevent multiple heartbeat thread are run, self keeps a most recent running_hb_thread_id.
          Stale threads will be stopped by comparing their own id with self.running_hb_thread_id.
        """
        this_thread_id = args[0]
        time.sleep(self.HEARTBEAT_INTERVAL + random.randint(self.SLEEP_MIN, self.SLEEP_MAX))
        while this_thread_id == self.running_hb_thread_id:
            if self.wsapp:
                try:
                    self.wsapp.send(self.heartbeat_msg)
                    print(f"Heartbeat thread {this_thread_id}: Heartbeat sent.")
                except websocket._exceptions.WebSocketConnectionClosedException as e:
                    print(f"Heartbeat thread {this_thread_id}: Connection is closed, stopped heartbeat.")
                    break
                except Exception as e:
                    print(f"Heartbeat thread {this_thread_id}: Error sending heartbeat: {e}.")
                    break
            time.sleep(self.HEARTBEAT_INTERVAL + random.randint(self.SLEEP_MIN, self.SLEEP_MAX))
        print(f"Heartbeat thread {this_thread_id}: Closed.")

    def on_message(self, wsapp, message):
        def run(*args):
            msg = json.loads(message)
            if msg.get("type") == "ping":
                return
            # print(msg)
            if msg.get("type") == "reject_subscription":
                print("Client: Connection is refused, please make sure your token/uuid is correct and your account is valid. Exiting.")
                wsapp.close()
            elif msg.get("type") == "confirm_subscription":
                print(f"Client: You're connected to tunnel: {json.loads(msg.get("identifier")).get("tunnel")}.")
            elif msg.get("type") == "disconnect":
                if (msg.get("reason") == "server_restart" and msg.get("reconnect") == True):
                    print("Client: Reconnecting in a few seconds")
                    wsapp.close()
                    time.sleep(random.randint(self.SLEEP_MIN, self.SLEEP_MAX))
                    self.start()
                elif (msg.get("reason") == "remote" and msg.get("reconnect") == True):
                    print("Client: Reconnecting in a few seconds")
                    wsapp.close()
                    time.sleep(random.randint(self.SLEEP_MIN, self.SLEEP_MAX))
                    self.start()
                elif (msg.get("reason") == "unauthorized" and msg.get("reconnect") == False):
                    print("Client: Unauthorized User.")
                    wsapp.close()
            if msg.get("identifier"):
                ids = json.loads(msg.get("identifier"))
                if ids.get("channel") == "CommandChannel":
                    cmd = msg.get("message", {}).get("command")
                    if cmd:
                        os.system(cmd)
        threading.Thread(target=run).start()


    def on_error(self, wsapp, error):
        print(f"Client: Error: {error}")

    def on_reconnect(self, wsapp):
        print("Client: Reconnecting.")
        wsapp.send(self.connect_msg)
        self.running_hb_thread_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        threading.Thread(target=self.send_heartbeat, args=[self.running_hb_thread_id], daemon=True).start()

    def on_open(self, wsapp):
        print("Client: Connecting.")
        wsapp.send(self.connect_msg)
        self.running_hb_thread_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        threading.Thread(target=self.send_heartbeat, args=[self.running_hb_thread_id], daemon=True).start()

    def on_close(self, wsapp, close_status_code, close_msg):
        print("Client: Closing.")
        if close_status_code or close_msg:
            print("close status code: " + str(close_status_code))
            print("close message: " + str(close_msg))

def main():
    parser = argparse.ArgumentParser(description='Input your uuid and token')
    parser.add_argument('-c', type=str, metavar="Config", required=True, help="Format is TOKEN:UUID")
    parser.add_argument('-d', '--dev_mode', action='store_true', help="Enable development mode")
    args = parser.parse_args()
    token, uuid = args.c.split(":")
    app = CommandChannel(token=token, uuid=uuid, dev_mode=args.dev_mode)
    app.start()

if __name__ == "__main__":
    main()
