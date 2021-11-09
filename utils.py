
BUFFER_SIZE = 1024

stm_target = 0
stm_fact = 0
stm_period = 0

def parse_read_buf(data: bytearray):
    length = len(data)
    if length >= BUFFER_SIZE:
        print("Warning: receive buffer overflow!")
    
    pos = 0
    seg_head = bytearray.fromhex("535a4859")

    while pos < length:
        packet = str()

        # head segment
        pos += data[pos:].find(seg_head)
        if pos < 0:
            return
        packet += data[pos:(pos + 4)][::-1].hex()
        pos += 4

        # channel and length segments
        packet += data[pos:(pos + 1)][::-1].hex()
        pos += 1
        seg_len = data[pos:(pos + 4)][::-1].hex()
        packet += seg_len
        packet_len = int(seg_len, base=16)
        pos += 4

        # cmd, parameters and checksum segments
        seg_etc = parse_data_after_len(data[pos:(pos - 9 + packet_len)])
        packet += seg_etc
        pos += (packet_len - 9)

        process_packet(packet)


'''
Parse a packet received from stm32
after having received the length 
segments. Return remaining segments
'''
def parse_data_after_len(bytes_left: bytearray) -> str:
    ret = str()
    pos = 0
    length = len(bytes_left)
    # cmd segment: 1 byte
    ret += bytes_left[pos:(pos + 1)].hex()
    pos += 1
    # parameter segments: (length - 2) bytes
    if (length - pos - 1) % 4 != 0:
        print("Warning: could not parse parameter segments")
        return str()
    while pos < length - 1:
        ret += bytes_left[pos:(pos + 4)][::-1].hex()
        pos += 4
    # checksum secgment: 1 byte
    ret += bytes_left[pos:(pos + 1)].hex()

    return ret


def process_packet(packet: str):
    cmd = packet[18:20]
    if cmd == "01":
        target = int(packet[20:28], base=16)
        global stm_target
        if stm_target != target:
            stm_target = target
            print("target updated: target=", target)

    if cmd == "02":
        fact = int(packet[20:28], base=16)
        global stm_fact
        if stm_fact != fact:
            stm_fact = fact
            print("fact updated: fact=", fact)
        
    if cmd == "06":
        period = int(packet[20:28], base=16)
        global stm_period
        if stm_period != period:
            stm_period = period
            print("period updated: period=", period)