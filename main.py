import os
import threading
from cmd import Cmd

import redis

lock = threading.RLock()
connect = redis.from_url(os.getenv("REDIS_URL", ""))
subscriber = connect.pubsub()


class ChannelListener(threading.Thread):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self):
        for message in subscriber.listen():
            self.notify(message)

    @staticmethod
    def notify(message):
        if message["type"] != "message":
            return
        username, text = message["data"].decode().split(maxsplit=1)
        channel = message["channel"].decode()
        with lock:
            print("\n(MESSAGE FROM {}) {} {}\n".format(channel, username, text))


class ChatPrompt(Cmd):
    prompt = "(CHAT) > "
    intro = "Simple chat client"
    channels = []

    def __init__(self, username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username = username

    @staticmethod
    def do_exit(*args):
        subscriber.unsubscribe()
        return True

    def do_leave(self, channel="all"):
        if channel == "all":
            subscriber.unsubscribe(self.channels)
            self.channels.clear()
        else:
            subscriber.unsubscribe(*channel.split())

    def do_send(self, data):
        data = data.split(maxsplit=1)
        if not self.channels and len(data) != 2:
            print("Specify message and channel.")
        channel = data[0] if len(data) == 2 else self.channels[-1]
        message = data[-1]
        if not message:
            print("Specify the message text.")
        else:
            connect.publish(channel, "[{}]: {}".format(self.username, message))

    def do_subscribe(self, channel):
        if not channel:
            print("Error: you should enter a channel.")
        else:
            print("Subscribed to {}".format(channel))
            self.channels.append(channel)
            subscriber.subscribe(channel)
            ChannelListener().start()


if __name__ == '__main__':
    name = input("Enter username: ")
    ChatPrompt(name).cmdloop()
