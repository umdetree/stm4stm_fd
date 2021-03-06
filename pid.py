from tkinter import *
from tkinter import messagebox
from tkinter.ttk import *
import matplotlib
import serial
import threading
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from serial.serialutil import SerialException
from time import sleep


BUFFER_SIZE = 1024
TARGET_CMD = "01"
FACT_CMD = "02"
PID_CMD = "03"
PERIOD_CMD = "06"


# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# +     4    +     1     +    4    +    1   +  4 +  4 +  4 +    1    +
# +包头4bytes 通道地址1byte 包长度0x17 指令0x10 P(4) I(4) D(4) 校验和1byte
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def make_pid_packet():
    ret_s = "535a4859" + "01" + "17000000" + "10"
    ret = bytearray.fromhex(ret_s)

    ret += int(p_spin.get(), 10).to_bytes(4, 'little')
    ret += int(i_spin.get(), 10).to_bytes(4, 'little')
    ret += int(d_spin.get(), 10).to_bytes(4, 'little')

    ret.append(checksum(ret))

    print("the pid_packet is {}".format(ret.hex()))
    return ret

def make_target_packet():
    ret_s = "535a4859" + "01" + "0f000000" + "11"
    ret = bytearray.fromhex(ret_s)

    ret += int(target_spin.get(), 10).to_bytes(4, 'little')
    ret.append(checksum(ret))

    print("the target_packet is ", ret.hex())
    return ret

def checksum(packet: bytearray):
    cs = 0
    for b in packet:
        cs += b

    cs = cs & 0xff
    print("checksum of {} is {:x}".format(packet.hex(), cs))
    return cs


ser = serial.Serial()

'''
Closed by default.
Open after calling open_serial_click()
'''
def send_pid_click():
    print("send_pid_click")
    pid_packet = make_pid_packet()
    send_buf_str.set(pid_packet.hex())
    try:
        ser.write(pid_packet)
    except SerialException:
        messagebox.showerror("Serial Error","serial port may be closed!")

def send_target_click():
    print("send_target_click")
    target_packet = make_target_packet()
    try:
        ser.write(target_packet)
    except SerialException:
        messagebox.showerror("Serial Error","serial port may be closed!")


Rx: threading.Thread
'''
reference:
https://stackoverflow.com/questions/14487151/pyserial-full-duplex-communication
https://robotics.stackexchange.com/questions/11897/how-to-read-and-write-data-with-pyserial-at-same-time
'''
def open_serial_click():
    ser.port = serial_port.get()
    ser.baudrate = int(baud_rate.get(), 10)

    if ser.isOpen():
        ser.close()

    try:
        ser.open()
        ser.setDTR(False)
        ser.setRTS(False) 
    except SerialException:
        messagebox.showerror("Serial Error", "Could not open port {}".format(ser.port))
        return

    global Rx
    Rx = threading.Thread(target=up_process, args={})
    Rx.start()

    send_pid_btn.configure(state=ACTIVE)
    send_target_btn.configure(state=ACTIVE)
    close_serial_btn.configure(state=ACTIVE)
    open_serial_btn.configure(state=DISABLED)
    
ser_lock = threading.Lock()

def up_process():
    ser.timeout = 0.5
    while True:
        try:
            ser_lock.acquire()

            if ser.is_open == False:
                ser_lock.release()
                break
            recv_b = ser.read(BUFFER_SIZE)

            ser_lock.release()

        except SerialException:
            print("Error: up_process thread failed to read from serial port")
        # ser.flushInput()
        parse_read_buf(recv_b)

def parse_read_buf(data: bytearray):
    length = len(data)
    if length >= BUFFER_SIZE:
        print("Warning: read buffer overflow!")
    
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

    if cmd == TARGET_CMD:
        target = int(packet[20:28], base=16)
        global stm_target
        if stm_target.get() != target:
            stm_target.set(target)
            print("target updated: target=", target)
            print("target_packet: ", packet)

    if cmd == FACT_CMD:
        fact = int(packet[20:28], base=16)
        global stm_fact
        if stm_fact.get() != fact:
            stm_fact.set(fact)
            print("fact updated: fact=", fact)
        
    if cmd == PERIOD_CMD:
        period = int(packet[20:28], base=16)
        global stm_period
        if stm_period.get() != period:
            stm_period.set(period)
            print("period updated: period=", period)


def close_serial_click():
    ser_lock.acquire()
    print("Debug: ser.close()")
    ser.close()
    ser_lock.release()

    send_pid_btn.configure(state=DISABLED)
    send_target_btn.configure(state=DISABLED)
    close_serial_btn.configure(state=DISABLED)
    open_serial_btn.configure(state=ACTIVE)
    


window = Tk()
window.title("气压反馈")
window.geometry("900x500")

# GUI part 1: pid sending
Label(window, text="P").grid(column=0, row=0)
Label(window, text="I").grid(column=0, row=1)
Label(window, text="D").grid(column=0, row=2)
p_spin = Spinbox(window, from_=0, to=100, width = 3)
i_spin = Spinbox(window, from_=0, to=100, width = 3)
d_spin = Spinbox(window, from_=0, to=100, width = 3)
p_spin.grid(column=1, row=0)
i_spin.grid(column=1, row=1)
d_spin.grid(column=1, row=2)

send_pid_btn = Button(window, text="发送pid", command=send_pid_click, state=DISABLED)
send_pid_btn.grid(column=1, row=3)

Label(window, text="target").grid(column=0, row=4)
target_spin = Spinbox(window, from_=25, to=120, width=3)
target_spin.grid(column=1, row=4)

send_target_btn = Button(window, text="发送target", command=send_target_click, state=DISABLED)
send_target_btn.grid(column=1, row=5)

# GUI part 2: buffer view 
Label(window, text="发送的数据包:").grid(column=2, row=0)
send_buf_str = StringVar()
Entry(window, textvariable=send_buf_str, width=50, background="white", state='readonly').grid(column=3, row=0)

Label(window, text="接收的数据包:").grid(column=2, row=1)
recv_buf_str = StringVar()
Entry(window, textvariable=recv_buf_str, width=50, background="white", state='readonly').grid(column=3, row=1)

Label(window, text="target:").grid(column=2, row=2)
stm_target = IntVar()
stm_target.set(0)
Entry(window, textvariable=stm_target, width=10, background='white', state='readonly').grid(column=3, row=2, sticky='w')

Label(window, text="fact:").grid(column=2, row=3)
stm_fact = IntVar()
stm_fact.set(0)
Entry(window, textvariable=stm_fact, width=10, background='white', state='readonly').grid(column=3, row=3, sticky='w')

Label(window, text="period:").grid(column=2, row=4)
stm_period = IntVar()
stm_period.set(0)
Entry(window, textvariable=stm_period, width=10, background='white', state='readonly').grid(column=3, row=4, sticky='w')

# GUI part 3: serial port 
Label(window, text="选择串口:").grid(column=4, row=0)
serial_port = Combobox(window)
serial_port['value'] = ("COM1", "COM2", "COM3", "COM4", "COM5", "COM6","COM7","COM8","COM9")
serial_port.grid(column=5, row=0)

Label(window, text="波特率:").grid(column=4, row=1)
baud_rate = Combobox(window)
baud_rate['value'] = (300, 1200, 2400, 9600, 19200, 38400, 115200)
baud_rate.grid(column=5, row=1)

open_serial_btn = Button(window, text="打开串口", command=open_serial_click, state=ACTIVE)
open_serial_btn.grid(column=4, row=2)

close_serial_btn = Button(window, text="关闭串口", command=close_serial_click, state=DISABLED)
close_serial_btn.grid(column=5, row=2)

window.mainloop()


ser_lock.acquire()
ser.close()
ser_lock.release()
