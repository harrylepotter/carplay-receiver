
# "Autobox" dongle driver for HTML 'streaming'
# Created by Colin Munro, December 2019
# See README.md for more information

"""Dongle USB connection code."""

import usb.core
import usb.util
import threading
import protocol

class Connection:
    idVendor = 0x1314
    idProduct = 0x1520
    
    def __init__(self):
        self._device = usb.core.find(idVendor = self.idVendor, idProduct = self.idProduct)
        if self._device is None:
            raise RuntimeError("Couldn't find USB device")
        self._device.reset()
        self._device.set_configuration()
        self._interface = self._device.get_active_configuration()[(0,0)]
        self._ep_in = usb.util.find_descriptor(self._interface, custom_match = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)
        if self._ep_in is None:
            raise RuntimeError("Couldn't find input endpoint")
        self._ep_in.clear_halt()
        self._ep_out = usb.util.find_descriptor(self._interface, custom_match = lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
        if self._ep_out is None:
            raise RuntimeError("Couldn't find output endpoint")
        self._ep_out.clear_halt()
        self._out_locker = threading.Lock()
        self._run = True
        self._thread = threading.Thread(target=self._read_thread)
        self._thread.start()

    def send_message(self, message):
        data = message.serialise()
        while not self._out_locker.acquire():
            pass
        try:
            self._ep_out.write(data[:message.headersize])
            self._ep_out.write(data[message.headersize:])
        finally:
            self._out_locker.release()

    def send_multiple(self, messages):
        for x in messages:
            self.send_message(x)

    def stop(self):
        self._run = False
        self._thread.join()

    def on_message(self, message):
        """Handle message from dongle [called from another thread]"""
        pass

    def on_error(self, error):
        """Handle exception on dongle read thread [called from another thread]"""
        self._run = False

    def _threaderror(self, error):
        print(f"Error with thread: {error}")
        self.on_error(error)
        
    def _read_thread(self):
        while self._run:
            try:
                data = self._ep_in.read(protocol.Message.headersize)
            except usb.core.USBError as e:
                if e.errno != 110: # Timeout
                    self.on_error(e)
                continue
            if len(data) == protocol.Message.headersize:
                header = protocol.Message()
                header.deserialise(data)
                needlen = len(header._data())
                if needlen:
                    try:
                        msg = header.upgrade(self._ep_in.read(needlen))
                    except usb.core.USBError as e:
                        self._threaderror(e)
                        continue
                else:
                    msg = header
                try:
                    self.on_message(msg)
                except Exception as e:
                    self.on_error(e)
                    continue
            else:
                print(f"R> Bad data: {data}")

Error = usb.core.USBError
