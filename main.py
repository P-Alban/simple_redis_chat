import os
import threading
from cmd import Cmd

import redis

lock = threading.RLock()
connect = redis.from_url(os.getenv("REDIS_URL"))
subscriber = connect.pubsub()


class ChannelListener(threading.Thread):

    def __init__(self, username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username = username

    def run(self):
        for message in subscriber.listen():
            self.notify(message)

    def notify(self, message):
        if message["type"] != "message":
            return
        text = message["data"].decode()
        with lock:
            print("\n(MESSAGE) [{}]: {}\n".format(self.username, text))


class ChatPrompt(Cmd):
    prompt = "(CHAT) > "
    intro = "Simple chat client"
    current_channel = None

    def __init__(self, username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username = username

    def do_exit(self, *args):
        subscriber.unsubscribe(self.current_channel)
        return True

    def do_leave(self, *args):
        subscriber.unsubscribe(self.current_channel)
        print("Leave from {}".format(self.current_channel))

    def do_send(self, message):
        if not self.current_channel:
            print("Subscribe to some channel.")
        if not message:
            print("Specify the message text.")
        else:
            connect.publish(self.current_channel, message)

    def do_subscribe(self, channel):
        if not channel:
            print("Error: you should enter a channel.")
        if self.current_channel:
            print("First unsubscribe from {}".format(self.current_channel))
        else:
            print("Subscribed to {}".format(channel))
            self.current_channel = channel
            subscriber.subscribe(channel)
            ChannelListener(self.username).start()


if __name__ == '__main__':
    name = input("Enter username: ")
    ChatPrompt(name).cmdloop()
