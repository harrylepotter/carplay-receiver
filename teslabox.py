#!/usr/bin/python3

# "Autobox" dongle driver for HTML 'streaming' - test application
# Created by Colin Munro, December 2019
# See README.md for more information

"""Implementation to stream PNGs over a webpage that rsponds with touches that are relayed back to the dongle for Tesla experimental purposes."""
import decoder
import audiodecoder
import link
import protocol
from threading import Thread
import time
import queue
import os
import struct

class Teslabox:
    class _Decoder(decoder.Decoder):
        def __init__(self, owner):
            super().__init__()
            self._owner = owner
        def on_frame(self, png):
            self._owner._frame = png
    class _AudioDecoder(audiodecoder.AudioDecoder):
        def __init__(self, owner):
            super().__init__()
            self._owner = owner
    class _Connection(link.Connection):
        def __init__(self, owner):
            super().__init__()
            self._owner = owner
            self._owner.av_queue = queue.Queue()
            self.put_thread = Thread(target=self._put_thread, args=[self._owner])
            self.put_thread.start()
        def _put_thread(self, owner):
            self._owner = owner
            while True:
                while self._owner.av_queue.qsize():
                    message = self._owner.av_queue.get()                
                    if isinstance(message, protocol.Open):
                        if not self._owner.started:
                            self._owner._connected()
                            self.send_multiple(protocol.opened_info)
                    elif isinstance(message, protocol.VideoData):
                        self._owner.decoder.send(message.data)
                    elif isinstance(message, protocol.AudioData):
                        try:
                            self._owner.audio_decoder.send(message.data)
                        except Exception as e:
                            print(f"exception: {e}")
        def on_message(self, message):

                self._owner.av_queue.put(message);
                
        def on_error(self, error):
            self._owner._disconnect()
    def __init__(self):
        self._disconnect()
        # self.server = self._Server(self)
        self.decoder = self._Decoder(self)
        self.audio_decoder = self._AudioDecoder(self)
        self.heartbeat = Thread(target=self._heartbeat_thread)
        self.heartbeat.start()
    def _connected(self):
        print("Connected!")
        self.started = True
        self.decoder.stop()
        self.audio_decoder.stop()
        self.decoder = self._Decoder(self)
        self.audio_decoder = self._AudioDecoder(self)
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
    def _keylistener_thread(self, caller):
        while True:
            input1 = int(input())
            print(f'you entered {input1}')
            keys = protocol.CarPlay()
            mcVal = struct.pack("<L",input1)
            keys._setdata(mcVal)            
            caller.connection.send_message(keys)
    def run(self):
        self.keylistener = Thread(target=self._keylistener_thread, args=(self,))
        self.keylistener.start()
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
