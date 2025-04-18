import rom_interface
import sys
import ubinascii


class Dumper:
    def __init__(self):
        self.read_pins = rom_interface.init_connector()

    def dump(self, addr, size):
        print('dump')
        data = self._load_data(int(addr, 16), int(size))
        print('send')
        self._send_data(data)
        print('done')

    def read_header(self):
        print('read rom header')
        rom_header = self._read_rom_header()
        print('send rom header')
        self._send_data(rom_header)
        print('done')

    def _read_rom_header(self):
        return self._load_data(0x00ffc0, 32)

    def _load_data(self, addr, size):
        data = bytearray(size)
        cache_addr = None
        for i in range(size):
            rom_interface.set_address(addr + i, cache_addr)
            cache_addr = addr + i
            data[i] = rom_interface.read_byte(self.read_pins)
        return data

    @staticmethod
    def _send_data(data):
        b64_data = ubinascii.b2a_base64(data)
        print(len(b64_data))
        sys.stdout.write(b64_data)
