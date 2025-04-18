from machine import Pin


def init_connector():
    # set zero to address
    set_address(0)

    # init read pins
    read_pins = []
    for pin in range(0, 8):
        read_pins.append(Pin(pin, Pin.IN))

    # set /RD pin to low
    Pin(19, Pin.OUT, value=0)
    # set /RESET pin to high
    Pin(20, Pin.OUT, value=1)

    return read_pins


def set_address(addr, old_addr=None):
    addr_pins = []
    for pin in range(8, 16):
        addr_pins.append(Pin(pin, Pin.OUT, value=0))

    buffer_pins = []
    for pin in range(16, 19):
        buffer_pins.append(Pin(pin, Pin.OUT, value=0))

    for buffer_pin in buffer_pins:
        if old_addr is not None:
            if (addr & 0xff) == (old_addr & 0xff):
                addr >>= 8
                old_addr >>= 8
                continue
            else:
                old_addr >>= 8

        for addr_pin in addr_pins:
            addr_pin.value(addr & 0x01)
            addr >>= 1
        buffer_pin.value(1)
        buffer_pin.value(0)


def read_byte(read_pins):
    byte = 0
    for read_pin in reversed(read_pins):
        byte <<= 1
        byte |= read_pin.value()
    return byte
