import serial
import base64
from tqdm import tqdm


def main(i = 0):
    print('connecting to serial port...')
    ser = serial.Serial('COM5')
    print('connected')
    print('read rom header')
    raw_header = dump_header(ser)
    header = Header(raw_header)
    print(header)
    print('ROM header received')
    print('dump rom data')
    rom_data = dump_rom(ser, header)
    print('ROM data received')
    print('calc checksum')
    checksum = calc_checksum(rom_data, header.rom_type == 'ExHiROM')
    print(f'checksum: {checksum:04x}')
    print(f'header checksum: {header.checksum:04x}')
    if checksum != header.checksum and header.rom_type != 'ExHiROM':
        print('checksum mismatch')
        try:
            print('verify rom data')
            diff_chunks = verify_rom(ser, header, rom_data)
            print('fix rom data')
            rom_data = fix_rom(ser, header, rom_data, diff_chunks)
        except IOError as e:
            print(e)
    ser.close()
    print('writing rom data to file...')
    checksum = calc_checksum(rom_data, header.rom_type == 'ExHiROM')
    rom_name = header.title.strip().replace(" ", "_") + (f'_checksum_mismatch_{i}' if checksum != header.checksum else '')
    with open(f'{rom_name}.sfc', 'wb') as f:
        f.write(rom_data)
    print('done')
    if checksum != header.checksum:
        main(i + 1)

def dump_header(ser: serial):
    header_addr = 0x00FFC0
    size = 0x32
    ser.write(f'dump 0x{header_addr:06x} {size}\n'.encode('ascii'))
    header_data = receive(ser, size)
    return header_data

class Header:
    def __init__(self, data):
        try:
            self.title = data[0:21].decode('ascii').strip()
        except UnicodeDecodeError:
            self.title = bytes([(i if i < 0x80 else 0x3f) for i in data[0:20]]).decode('ascii').strip()
        self.rom_speed = 'Fast' if data[21] >> 4 & 1 else 'Slow'
        if data[21] & 0b100:
            self.rom_type = 'ExHiROM'
        elif data[21] & 0b001:
            self.rom_type = 'HiROM'
        else:
            self.rom_type = 'LoROM'
        if self.rom_type == 'ExHiROM':
            self.rom_size = 1024 * (6 if self.title == 'TALES OF PHANTASIA' else 5)
        else:
            self.rom_size = 1 << data[23]
        self.checksum = (data[29] << 8) + data[28]

    def __str__(self):
        return f'title: {self.title}\n' \
               f'rom speed: {self.rom_speed}\n' \
               f'rom type: {self.rom_type}\n' \
               f'rom size: {self.rom_size}KB\n' \
               f'checksum: {self.checksum:04x}'


def dump_rom(ser: serial, header: Header):
    rom_data = bytearray()
    whole_size = 0
    next_addr = None
    while True:
        if whole_size >= header.rom_size * 1024:
            break
        next_addr, size = get_next_addr_and_size(header, next_addr)
        print(f'dump ${next_addr:06x} ({whole_size // 1024}KB / {header.rom_size}KB)')
        ser.write(f'dump 0x{next_addr:06x} {size}\n'.encode('ascii'))
        rom_data += receive(ser, size, header.rom_type != 'LoROM')
        next_addr += size
        whole_size += size
    return rom_data


def verify_rom(ser: serial, header: Header, rom_data: bytes):
    diff_chunks = []
    cart_addr = get_init_addr(header)
    file_addr = 0
    while True:
        print(f'verify ${cart_addr:06x} ({file_addr // 1024}KB / {header.rom_size}KB)')
        cart_addr, limit_size = get_next_addr_and_size(header, cart_addr)
        if limit_size == 0:
            break
        chunk_size = min(limit_size, 1024)
        ser.write(f'dump 0x{cart_addr:06x} {chunk_size}\n'.encode('ascii'))
        verify_chunk = receive(ser, chunk_size)
        if rom_data[file_addr:file_addr + chunk_size] != verify_chunk:
            error_length = 0
            for i in range(chunk_size):
                if rom_data[file_addr + i] != verify_chunk[i]:
                    error_length += 1
                    continue
                if error_length > 0:
                    diff_chunks.append((cart_addr + i - error_length, error_length))
                    error_length = 0
            if error_length > 0:
                diff_chunks.append((cart_addr + chunk_size - error_length, error_length))
        cart_addr += chunk_size
        file_addr += chunk_size

    if len(diff_chunks) == 0:
        raise IOError('verify failed')
    return diff_chunks

def fix_rom(ser: serial, header: Header, rom_data: bytes, diff_chunks: list[tuple[int, int]]):
    fix_rom_data = bytearray(rom_data)
    print(diff_chunks)
    for cart_addr, error_size in diff_chunks:
        file_addr = convert_addr_cart_to_file(cart_addr, header)
        reread_chunks = {}
        for i in range(5):
            ser.write(f'dump 0x{cart_addr:06x} {error_size}\n'.encode('ascii'))
            reread_chunk = receive(ser, error_size)
            reread_chunks[reread_chunk] = reread_chunks.get(reread_chunk, 0) + 1
        most_read_chunk = max(reread_chunks, key=reread_chunks.get)
        fix_rom_data[file_addr:file_addr + error_size] = most_read_chunk
    checksum = calc_checksum(fix_rom_data, header.rom_type == 'ExHiROM')
    if checksum != header.checksum:
        raise IOError('fix failed')
    print('fix success')
    return fix_rom_data


def convert_addr_cart_to_file(cart_addr, header):
    if header.rom_type == 'HiROM':
        return cart_addr & 0x3fffff
    else:
        # LoROM
        return ((cart_addr & 0xff0000) >> 1) + (cart_addr & 0x7fff)


def calc_checksum(data: bytes, is_exhirom: bool = False):
    checksum = 0
    for i in range(0, len(data)):
        checksum += data[i]
    if is_exhirom:
        rom_limit = 4 * 1024 * 1024
        size = len(data) - rom_limit
        num = rom_limit // size
        print(f'num: {num}, size: {size}')
        for _ in range(num):
            for i in range(size):
                checksum += data[rom_limit + i]
    return ~checksum & 0xffff


def receive(ser: serial, size: int, show_progress: bool = False) -> bytes:
    data = bytearray()
    bar = tqdm(total=size, unit='B', unit_scale=True, disable=not show_progress)

    while True:
        line = ser.readline()
        if line == b'done\r\n':
            break
        elif line.strip().isdigit():
            chunk = read_data(ser, line)
            bar.update(len(chunk))
            data += chunk
        elif line == b'wait\r\n':
            print('wait')
        else:
            pass
    return data

def read_data(ser, size):
    size = int(size)
    b64_data = ser.read(size + 1)  # converted \n -> \r\n in serial port
    return base64.b64decode(b64_data)


def get_next_addr_and_size(header, next_addr = None):
    rom_size = header.rom_size * 1024
    if header.rom_type == 'LoROM':
        if next_addr is None:
            return 0x808000, 0x8000
        if next_addr & 0xffff < 0x8000:
            next_addr += 0x8000
        size = 0x10000 - (next_addr & 0xffff)
    elif header.rom_type == 'HiROM':
        if next_addr is None:
            return 0xc00000, rom_size
        size = rom_size - (next_addr - 0xc00000)
    else: # ExHiROM
        if next_addr is None:
            return 0xc00000, 4 * 1024 * 1024
        if next_addr >= 0xc00000 and next_addr < 0xffffff:
            size = 0xffffff - next_addr
        elif next_addr < 0x7f0000:
            size = rom_size - (4 * 1024 * 1024) - (next_addr - 0x400000)
        else: # next_addr >= 0xffffff
            next_addr = 0x400000
            size = rom_size - (4 * 1024 * 1024)
    return next_addr, size

def get_init_addr(header):
    if header.rom_type == 'LoROM':
        return 0x008000
    else:
        return 0xc00000


if __name__ == '__main__':
    main()
