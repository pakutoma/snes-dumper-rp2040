import sys
import ubinascii

import rp2
from machine import Pin

class Dumper:
    BUFFER_SIZE = 1024 * 16

    def __init__(self):
        # set /RD pin to low
        Pin(19, Pin.OUT, value=0)
        # set /RESET pin to high
        Pin(20, Pin.OUT, value=1)

        self.data_pins = []
        for pin in range(0, 8):
            self.data_pins.append(Pin(pin, Pin.IN))
        self.addr_pins = []
        for pin in range(8, 16):
            self.addr_pins.append(Pin(pin, Pin.OUT, value=0))
        self.select_pins = []
        for pin in range(16, 19):
            self.select_pins.append(Pin(pin, Pin.OUT, value=0))

        # init PIO state machine and DMA
        self.sm = rp2.StateMachine(
            0,
            self._pio_read_data,
            freq=10_000_000,
            in_base=self.data_pins[0],  # 8 bit
            out_base=self.addr_pins[0],  # 8 bit * 3 = 24 bit
            set_base=self.select_pins[0],  # 3 pins
        )
        self.dma = rp2.DMA()
        self.dma_ctrl = self.dma.pack_ctrl(
            size=0,  # 8 bit
            inc_read=False,
            treq_sel=4  # PIO(SM0) RX FIFO
        )

    def dump(self, addr_hex: str, size_str: str):
        addr = int(addr_hex, 16)
        size = int(size_str)
        print('send')
        self._read_and_send_data(addr, size)
        print('done')

    def _read_and_send_data(self, start_addr: int, rom_size: int):
        end_addr = start_addr + max(rom_size, self.BUFFER_SIZE)  # [start, end) range

        self.sm.put(start_addr)
        self.sm.put(end_addr)

        buffers = [bytearray(self.BUFFER_SIZE), bytearray(self.BUFFER_SIZE)]
        writing_buffer = 0
        sent_size = 0
        buffered_size = 0

        self.sm.active(1)
        while sent_size < rom_size:
            if buffered_size < rom_size:
                # read rom data from SFC cart in PIO and copy to buffer with DMA asynchronously
                self.dma.config(read=self.sm,
                                write=buffers[writing_buffer],
                                count=self.BUFFER_SIZE,
                                ctrl=self.dma_ctrl)
                self.dma.active(1)
            if sent_size < buffered_size:
                # send written data to host synchronously
                send_limit = min(rom_size - sent_size, self.BUFFER_SIZE)
                self._send_data(buffers[1 - writing_buffer][:send_limit])
                sent_size += send_limit
            if buffered_size < rom_size:
                while self.dma.active():
                    pass
                buffered_size += self.BUFFER_SIZE
            # flip buffers
            writing_buffer = 1 - writing_buffer
        self.sm.active(0)

    def _send_data(self, data: bytearray):
        b64_data = ubinascii.b2a_base64(data)
        print(len(b64_data))
        sys.stdout.write(b64_data)

    # noinspection PyStatementEffect,PyArgumentList,PyUnresolvedReferences
    @staticmethod
    @rp2.asm_pio(out_init=([rp2.PIO.OUT_LOW] * 8),
                 set_init=([rp2.PIO.OUT_LOW] * 3),
                 out_shiftdir=rp2.PIO.SHIFT_RIGHT)
    def _pio_read_data():
        pull()
        mov(x, invert(osr))  # copy start addr (inverted)
        pull()
        mov(y, invert(osr))  # copy end addr (inverted)
        label('loop')
        mov(osr, invert(x))  # move start addr to OSR
        out(pins, 8).delay(4)  # send 8 bit to buffer 0
        set(pins, 0b001).delay(4)
        set(pins, 0b000).delay(4)
        out(pins, 8).delay(4)  # send 8 bit to buffer 1
        set(pins, 0b010).delay(4)
        set(pins, 0b000).delay(4)
        out(pins, 8).delay(4)  # send 8 bit to buffer 2
        set(pins, 0b100).delay(4)
        set(pins, 0b000).delay(4)
        in_(pins, 8)  # read data from cart
        push()  # push 1 byte to FIFO
        jmp(x_dec, 'post_dec')  # decrement inverted start addr (= increment start addr)
        label('post_dec')
        jmp(x_not_y, 'loop')
