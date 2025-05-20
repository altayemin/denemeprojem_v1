import Adafruit_DHT
import serial
import requests
import datetime
import tkinter as tk
from tkinter import ttk
import threading
import time
import csv
import os

# Constants
DESKTOP_PATH = os.path.expanduser("~/Desktop")
GOOGLE_SHEETS_URL_DHT = "https://script.google.com/macros/s/AKfycbzbljWuNrXPW7UHn9ON7tTLZQH2auZNuC8Q4Is-FafSTP7Jzn7C_xwZZE8Zj5bSWhtWxA/exec"
GOOGLE_SHEETS_URL_SD = "https://script.google.com/macros/s/AKfycby95FK2-4Mzn8c0BtRx352R3EHm_rZ0FpHl4U0KES6HZOYbEBOFbgf5xIz0TfWFkCrK/exec"
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PINS = [17, 27, 23, 25, 26, 16, 12, 6]
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200
CPU_TEMP_PATH = "/sys/class/thermal/thermal_zone0/temp"

# Control flags
running = False
pause_event = threading.Event()
pause_event.set()

# Threads
dht_thread = None
sd_thread = None

# CSV and Sheets functions
def write_dht_to_csv(data):
    fname = os.path.join(DESKTOP_PATH, "dht_data.csv")
    exists = os.path.isfile(fname)
    with open(fname, 'a', newline='') as f:
        writer = csv.writer(f)
        if not exists:
            header = ["time"] + [f"T{i}" for i in range(1,9)] + [f"H{i}" for i in range(1,9)]
            writer.writerow(header)
        row = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")] + [data.get(f'T{i}') for i in range(1,9)] + [data.get(f'H{i}') for i in range(1,9)]
        writer.writerow(row)

def write_dht_to_csv(data):
    fname = os.path.join(DESKTOP_PATH, "dht_data.csv")
    exists = os.path.isfile(fname)
    with open(fname, 'a', newline='') as f:
        writer = csv.writer(f)
        if not exists:
            # Başlıkları da yeni sıraya göre düzenle
            header = ["time"] + [f"{x}{i}" for i in range(1,9) for x in ['T', 'H']]
            writer.writerow(header)
        # Verileri T1,H1,T2,H2,... şeklinde sırala
        row = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        for i in range(1, 9):
            row.extend([data.get(f'T{i}'), data.get(f'H{i}')])
        writer.writerow(row)

def send_dht_to_sheets(data):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # T1,H1,T2,H2,... şeklinde sırala
    values = [ts]
    for i in range(1, 9):
        values.extend([data.get(f'T{i}'), data.get(f'H{i}')])
    payload = {"sheet":"veriler","values":values}
    requests.post(GOOGLE_SHEETS_URL_DHT, json=payload)

def send_sd_to_sheets(value):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = {"sheet":"debimetre","values":[ts, value]}
    requests.post(GOOGLE_SHEETS_URL_SD, json=payload)

# GUI setup
root = tk.Tk()
root.title("SUBÜ - DATALOGGER")
root.attributes('-fullscreen', True)
root.configure(bg="#e6f2ff")

style = ttk.Style(root)
style.theme_use('default')
style.configure('TLabel', background='#e6f2ff', foreground='#003366', font=('Arial', 10, 'bold'))
style.configure('Header.TLabel', background='#e6f2ff', foreground='#003366', font=('Arial', 14, 'bold'))
# Unified status style
style.configure('Status.TLabel', background='#0066CC', foreground='white', font=('Arial', 10, 'bold'))
style.configure('TButton', font=('Arial', 10, 'bold'))

# Header
header1 = ttk.Label(root, text="SUBÜ - DATALOGGER", style='Header.TLabel')
header1.place(relx=0.5, rely=0.03, anchor='n')
header2 = ttk.Label(root, text="DATALOGGER PROJESİ", style='Header.TLabel')
header2.place(relx=0.5, rely=0.08, anchor='n')

# Sensor Labels
labels = {}
base_y = 60
spacing = 30
for i in range(8):
    y = base_y + spacing * i
    labels[f"T{i+1}"] = ttk.Label(root, text=f"T{i+1}: -- °C")
    labels[f"T{i+1}"].place(x=10, y=y)
    labels[f"H{i+1}"] = ttk.Label(root, text=f"H{i+1}: -- %")
    labels[f"H{i+1}"].place(x=160, y=y)
labels['SD1'] = ttk.Label(root, text="SD1: -- L/dk")
labels['SD1'].place(x=310, y=base_y)

# Status frames (smaller) and labels
status_frame_dht = ttk.LabelFrame(root, text="Sıcaklık ve Nem", width=120, height=50)
status_frame_dht.place(x=360, y=100)
status_dht = ttk.Label(status_frame_dht, text="Kaydediliyor", style='Status.TLabel')
status_dht.place(relx=0.5, rely=0.5, anchor='center')

status_frame_sd = ttk.LabelFrame(root, text="Su Debisi", width=120, height=50)
status_frame_sd.place(x=360, y=160)
status_sd = ttk.Label(status_frame_sd, text="Kaydediliyor", style='Status.TLabel')
status_sd.place(relx=0.5, rely=0.5, anchor='center')

status_frame_cpu = ttk.LabelFrame(root, text="Pi CPU Sıcaklığı", width=120, height=50)
status_frame_cpu.place(x=360, y=220)
status_cpu = ttk.Label(status_frame_cpu, text="-- °C", style='Status.TLabel')
status_cpu.place(relx=0.5, rely=0.5, anchor='center')

# Function to update Pi CPU temp
def update_cpu_temp():
    try:
        with open(CPU_TEMP_PATH) as f:
            temp_milli = int(f.read().strip())
            temp_c = temp_milli / 1000.0
            status_cpu.config(text=f"{temp_c:.1f} °C")
    except Exception:
        status_cpu.config(text="Hata")
    root.after(1000, update_cpu_temp)

# Update status helper functions
def update_dht_status(state):
    status_dht.config(text=state)

def update_sd_status(state):
    status_sd.config(text=state)

# Sensor loops
def read_dht_loop():
    global running
    while running:
        pause_event.wait()
        data = {}
        update_dht_status('Kaydediliyor')
        try:
            for idx, pin in enumerate(DHT_PINS, start=1):
                hum, temp = Adafruit_DHT.read_retry(DHT_SENSOR, pin)
                data[f'T{idx}'] = round(temp,2) if temp else None
                data[f'H{idx}'] = round(hum,2) if hum else None
                if temp is not None:
                    labels[f"T{idx}"].config(text=f"T{idx}: {temp:.1f} °C")
                if hum is not None:
                    labels[f"H{idx}"].config(text=f"H{idx}: {hum:.1f} %")
            write_dht_to_csv(data)
            send_dht_to_sheets(data)
            update_dht_status('Kaydedildi')
        except Exception:
            update_dht_status('Kaydedilemedi')
        time.sleep(5)

# Su debisi loop
def read_sd_loop():
    global running
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        while running:
            pause_event.wait()
            update_sd_status('Kaydediliyor')
            line = ser.readline().decode().strip()
            if line:
                try:
                    flow = float(line)
                    labels['SD1'].config(text=f"SD1: {flow:.2f} L/dk")
                    write_sd_to_csv(flow)
                    send_sd_to_sheets(flow)
                    update_sd_status('Kaydedildi')
                except Exception:
                    update_sd_status('Kaydedilemedi')
            time.sleep(1)
    except Exception:
        update_sd_status('Kaydedilemedi')

# Control callbacks
def start_experiment():
    global running, dht_thread, sd_thread
    if not running:
        running = True
        pause_event.set()
        dht_thread = threading.Thread(target=read_dht_loop, daemon=True)
        sd_thread = threading.Thread(target=read_sd_loop, daemon=True)
        dht_thread.start()
        sd_thread.start()

def stop_experiment():
    pause_event.clear()

def resume_experiment():
    pause_event.set()

def stop_and_exit():
    global running
    running = False
    pause_event.set()
    root.destroy()

# Buttons
btn_start = ttk.Button(root, text="Deneyi Başlat", command=start_experiment)
btn_start.place(relx=0.2, rely=0.95, anchor='center')
btn_stop = ttk.Button(root, text="Deneyi Durdur", command=stop_experiment, state='disabled')
btn_stop.place(relx=0.4, rely=0.95, anchor='center')
btn_resume = ttk.Button(root, text="Devam Et", command=resume_experiment, state='disabled')
btn_resume.place(relx=0.6, rely=0.95, anchor='center')
btn_exit = ttk.Button(root, text="Durdur ve Kapat", command=stop_and_exit)
btn_exit.place(relx=0.8, rely=0.95, anchor='center')

# Button state updater
def update_buttons():
    if running and pause_event.is_set():
        btn_start.config(state='disabled')
        btn_stop.config(state='normal')
        btn_resume.config(state='disabled')
    elif running and not pause_event.is_set():
        btn_start.config(state='disabled')
        btn_stop.config(state='disabled')
        btn_resume.config(state='normal')
    else:
        btn_start.config(state='normal')
        btn_stop.config(state='disabled')
        btn_resume.config(state='disabled')
    root.after(200, update_buttons)

# Start CPU temp updater and button updater
update_buttons()
update_cpu_temp()
root.mainloop()