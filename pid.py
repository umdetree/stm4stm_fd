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

ser = serial.Serial()

def send_pid_click():
    print("send_pid_click")
    pid_frame = make_pid_frame()
    send_buf_str.set(pid_frame.hex())
    try:
        ser.write(pid_frame)
    except SerialException:
        messagebox.showerror("Serial Error","serial port is closed!")


'''
 TODO 
 read data received from STM
 etc
'''

def up_process():
    while is_serial_open == True:
        # read(17) for test
        recv = ser.read(17)
        if len(recv) > 0:
            print("data received: ", recv)
        recv_buf_str.set(recv.hex())
        sleep(0.5)
        print("not blocked")

Rx = threading.Thread(target=up_process, args=())
is_serial_open = False


'''
reference:
https://stackoverflow.com/questions/14487151/pyserial-full-duplex-communication
https://robotics.stackexchange.com/questions/11897/how-to-read-and-write-data-with-pyserial-at-same-time
'''

def open_serial_click():
    ser.port = serial_port.get()
    ser.baudrate = int(baud_rate.get(), 10)
    ser.timeout = 0
    if ser.isOpen():
        ser.close()
    try:
        ser.open()
    except SerialException:
        messagebox.showerror("Serial Error", "could not open port {}".format(ser.port))
        return
    global is_serial_open
    is_serial_open = True
    Rx.start()
    send_pid_btn.configure(state=ACTIVE)
    close_serial_btn.configure(state=ACTIVE)
    open_serial_btn.configure(state=DISABLED)
    
def close_serial_click():
    global is_serial_open
    is_serial_open = False
    sleep(0.1)
    ser.close()
    send_pid_btn.configure(state=DISABLED)
    close_serial_btn.configure(state=DISABLED)
    open_serial_btn.configure(state=ACTIVE)
    

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# +     4    +     1     +    4    +    1   +  4 +  4 +  4 +    1    +
# +包头4bytes 通道地址1byte 包长度0x17 指令0x03 P(4) I(4) D(4) 校验和1byte
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def make_pid_frame():
    ret_s = "59485A53" + "01" + "00000017" + "03"
    ret = bytearray.fromhex(ret_s)
    ret.append(int(p_spin.get(), 16))
    ret.append(int(i_spin.get(), 16))
    ret.append(int(d_spin.get(), 16))
    ret.append(checksum(ret))
    print("the pid_frame is {}".format(ret.hex()))
    return ret

def checksum(frame):
    cs = 0
    for b in frame:
        print("b is {:x}".format(b))
        cs += b
    cs = cs & 0xff
    print("checksum of {} is {:x}".format(frame, cs))
    return cs


window = Tk()
window.title("气压反馈")
window.geometry("800x500")

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

# GUI part 2: buffer view 
Label(window, text="发送的数据包:").grid(column=2, row=0)
send_buf_str = StringVar()
Entry(window, textvariable=send_buf_str, width=30, background="white", state='readonly').grid(column=3, row=0)

Label(window, text="接收的数据包:").grid(column=2, row=1)
recv_buf_str = StringVar()
Entry(window, textvariable=recv_buf_str, width=30, background="white", state='readonly').grid(column=3, row=1)

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
