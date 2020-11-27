#!/usr/bin/python3

# "Autobox" dongle driver for HTML 'streaming' - test application
# Created by Colin Munro, December 2019
# See README.md for more information

"""Implementation to stream PNGs over a webpage that rsponds with touches that are relayed back to the dongle for Tesla experimental purposes."""
import decoder
import server
import link
import protocol
from threading import Thread
import time
import queue
import os

class Teslabox:
    class _Server(server.Server):
        def __init__(self, owner):
            self._owner = owner
            super().__init__()
        def on_touch(self, type, x, y):
            if self._owner.connection is None:
                return
            if True:
                msg = protocol.Touch()
                types = {"down": protocol.Touch.Action.Down, "up": protocol.Touch.Action.Up, "move": protocol.Touch.Action.Move}
                msg.action = types[type]
                msg.x = int(x*10000/800)
                msg.y = int(y*10000/600)
            else:
                types = {"down": protocol.MultiTouch.Touch.Action.Down, "up": protocol.MultiTouch.Touch.Action.Up, "move": protocol.MultiTouch.Touch.Action.Move}
                msg = protocol.MultiTouch()
                tch = protocol.MultiTouch.Touch()
                tch.x = int(x)
                tch.y = int(y)
                tch.action = types[type]
                msg.touches.append(tch)
            self._owner.connection.send_message(msg)
        def on_get_snapshot(self):
            return self._owner._frame
    class _Decoder(decoder.Decoder):
        def __init__(self, owner):
            super().__init__()
            self._owner = owner
        def on_frame(self, png):
            self._owner._frame = png
    class _Connection(link.Connection):
        def __init__(self, owner):
            super().__init__()
            self._owner = owner
            self._owner.av_queue = queue.Queue()
            self.fifo_path = "mypipe2"
            # os.mkfifo(self.fifo_path, 0o600)
            self._owner.audio_fd = os.open(self.fifo_path, os.O_RDWR | os.O_NONBLOCK)
            self.put_thread = Thread(target=self._put_thread, args=[self._owner])
            self.put_thread.start()
        def _put_thread(self, owner):
            self._owner = owner
            while True:
                while self._owner.av_queue.qsize():
                    message = self._owner.av_queue.get()                
                    if isinstance(message, protocol.VideoData):
                        self._owner.decoder.send(message.data)
                    elif isinstance(message, protocol.AudioData):
                        try:
                            os.write(self._owner.audio_fd, message.data)
                        except Exception as e:
                            print(f"exception: {e}")
        def on_message(self, message):
            if isinstance(message, protocol.Open):
                if not self._owner.started:
                    self._owner._connected()
                    self.send_multiple(protocol.opened_info)
            else:
                self._owner.av_queue.put(message);
                
        def on_error(self, error):
            self._owner._disconnect()
    def __init__(self):
        self._disconnect()
        self.server = self._Server(self)
        self.decoder = self._Decoder(self)
        self.heartbeat = Thread(target=self._heartbeat_thread)
        self.heartbeat.start()
    def _connected(self):
        print("Connected!")
        self.started = True
        self.decoder.stop()
        self.decoder = self._Decoder(self)
    def _disconnect(self):
        if hasattr(self, "connection"):
            if self.connection is None:
                return
            print("Lost USB device")
        self._frame = b''
        self.connection = None
        self.started = False
    def _heartbeat_thread(self):
        while True:
            try:
                self.connection.send_message(protocol.Heartbeat())
            except link.Error:
                self._disconnect()
            except:
                pass
            time.sleep(protocol.Heartbeat.lifecycle)
    def run(self):
        while True:
            # First task: look for USB device
            while self.connection is None:
                try:
                    self.connection = self._Connection(self)
                except Exception as e:
                    pass
            print("Found USB device...")
            # Second task: transmit startup info
            try:
                while not self.started:
                    self.connection.send_multiple(protocol.startup_info)
                    time.sleep(1)
            except:
                self._disconnect()
            print("Connection started!")
            # Third task: idle while connected
            while self.started:
                time.sleep(1)

if __name__ == "__main__":
    Teslabox().run()
