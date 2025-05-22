import Adafruit_DHT
import serial
import requests
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import csv
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from statistics import mode

# Constants
DESKTOP_PATH = os.path.expanduser("~/Desktop")
GOOGLE_SHEETS_URL_DHT = "YOUR_GOOGLE_SCRIPT_URL_DHT"
GOOGLE_SHEETS_URL_SD = "YOUR_GOOGLE_SCRIPT_URL_SD"
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PINS = [5, 6, 12, 13, 19, 16, 26, 20]
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200
CPU_TEMP_PATH = "/sys/class/thermal/thermal_zone0/temp"

# Control flags and counters
running = False
pause_event = threading.Event()
pause_event.set()
veri_sayisi_dht = 0
veri_sayisi_sd = 0

# Threads
dht_thread = None
sd_thread = None

# Font sizes for 3.5" screen
SMALL_FONT = ('Arial', 9)
MEDIUM_FONT = ('Arial', 11)
LARGE_FONT = ('Arial', 14)
SENSOR_FONT = ('Arial', 12)

# Labels dictionary
labels = {}

# ---------------------------- FUNCTIONS ----------------------------
def write_dht_to_csv(data):
    global veri_sayisi_dht
    fname = os.path.join(DESKTOP_PATH, "dht_data.csv")
    exists = os.path.isfile(fname)
    with open(fname, 'a', newline='') as f:
        writer = csv.writer(f)
        if not exists:
            header = ["time"] + [f"{x}{i}" for i in range(1,9) for x in ['T', 'H']]
            writer.writerow(header)
        row = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        for i in range(1, 9):
            row.extend([data.get(f'T{i}'), data.get(f'H{i}')])
        writer.writerow(row)
        veri_sayisi_dht += 1
        data_counter_dht.config(text=f"DHT Veri: {veri_sayisi_dht}")
        
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        values = [ts]
        for i in range(1, 9):
            values.extend([data.get(f'T{i}'), data.get(f'H{i}')])
        payload = {"sheet":"veriler","values":values}
        requests.post(GOOGLE_SHEETS_URL_DHT, json=payload)
        update_dht_status('Kaydedildi')
    except Exception as e:
        update_dht_status('GSheet Hatası')

def write_sd_to_csv(value):
    global veri_sayisi_sd
    fname = os.path.join(DESKTOP_PATH, "flow_data.csv")
    exists = os.path.isfile(fname)
    with open(fname, 'a', newline='') as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(["time", "flow"])
        writer.writerow([datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), value])
        veri_sayisi_sd += 1
        data_counter_sd.config(text=f"Debi Veri: {veri_sayisi_sd}")
    
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {"sheet":"debimetre","values":[ts, value]}
        requests.post(GOOGLE_SHEETS_URL_SD, json=payload)
        update_sd_status('Kaydedildi')
    except Exception as e:
        update_sd_status('GSheet Hatası')

def read_dht_loop():
    global running
    while running:
        pause_event.wait()
        data = {}
        update_dht_status('Kaydediliyor...')
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
        except Exception as e:
            update_dht_status('DHT Hatası')
        time.sleep(5)

def read_sd_loop():
    global running
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        while running:
            pause_event.wait()
            update_sd_status('Kaydediliyor...')
            line = ser.readline().decode().strip()
            if line:
                try:
                    flow = float(line)
                    labels['SD1'].config(text=f"SD1: {flow:.2f} L/dk")
                    write_sd_to_csv(flow)
                except Exception as e:
                    update_sd_status('Debi Hatası')
            time.sleep(1)
    except Exception as e:
        update_sd_status('Seri Port Hatası')

def update_cpu_temp():
    try:
        with open(CPU_TEMP_PATH) as f:
            temp_milli = int(f.read().strip())
            temp_c = temp_milli / 1000.0
            status_cpu.config(text=f"{temp_c:.1f} °C")
    except Exception:
        status_cpu.config(text="Hata!")
    root.after(1000, update_cpu_temp)

def show_graph_page():
    graph_page = tk.Toplevel(root)
    graph_page.title("Grafikler")
    graph_page.attributes('-fullscreen', True)
    graph_page.configure(bg="#e6f2ff")
    
    btn_back = ttk.Button(graph_page, text="Ana Sayfa", command=graph_page.destroy)
    btn_back.pack(pady=5)
    
    # Temperature buttons
    temp_frame = tk.Frame(graph_page, bg="#e6f2ff")
    temp_frame.pack(fill='x', pady=2)
    for i in range(1, 9):
        ttk.Button(temp_frame, text=f"T{i}", 
                 command=lambda i=i: plot_data(f'T{i}'), 
                 width=3).pack(side='left', padx=2)
    
    # Flow button
    ttk.Button(temp_frame, text="SD1", 
              command=lambda: plot_data('SD1'), 
              width=3).pack(side='left', padx=2)
    
    # Humidity buttons
    hum_frame = tk.Frame(graph_page, bg="#e6f2ff")
    hum_frame.pack(fill='x', pady=2)
    for i in range(1, 9):
        ttk.Button(hum_frame, text=f"H{i}", 
                 command=lambda i=i: plot_data(f'H{i}'), 
                 width=3).pack(side='left', padx=2)
    
    # Figure for plotting
    fig = plt.Figure(figsize=(4.5, 3.5), dpi=80)
    ax = fig.add_subplot(111)
    fig.subplots_adjust(left=0.15, bottom=0.2, right=0.95, top=0.9)
    canvas = FigureCanvasTkAgg(fig, master=graph_page)
    canvas.get_tk_widget().pack(fill='both', expand=True, padx=5, pady=5)
    
    def plot_data(sensor):
        ax.clear()
        if sensor.startswith('T') or sensor.startswith('H'):
            filename = os.path.join(DESKTOP_PATH, "dht_data.csv")
            try:
                with open(filename, 'r') as f:
                    reader = csv.reader(f)
                    headers = next(reader)
                    
                    sensor_num = int(sensor[1:])
                    if sensor.startswith('T'):
                        col_index = 1 + (sensor_num-1)*2
                    else:
                        col_index = 2 + (sensor_num-1)*2
                    
                    times = []
                    values = []
                    rows = list(reader)
                    start_idx = max(0, len(rows) - veri_sayisi_dht)
                    
                    for row in rows[start_idx:]:
                        try:
                            times.append(datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S"))
                            values.append(float(row[col_index]))
                        except:
                            continue
                
                line_color = 'b' if sensor.startswith('T') else 'g'
                ax.plot(times, values, line_color+'-', linewidth=1.5)
                ax.set_title(f"{sensor} (Son {len(values)} veri)", fontsize=10)
                ax.set_ylabel("°C" if sensor.startswith('T') else "%", fontsize=9)
                ax.tick_params(axis='both', which='major', labelsize=7)
                ax.grid(True, linestyle=':', linewidth=0.5)
            
            except Exception as e:
                ax.set_title(f"Hata: {str(e)}", fontsize=10)
        
        elif sensor == 'SD1':
            filename = os.path.join(DESKTOP_PATH, "flow_data.csv")
            try:
                times = []
                values = []
                with open(filename, 'r') as f:
                    reader = csv.reader(f)
                    next(reader)
                    rows = list(reader)
                    start_idx = max(0, len(rows) - veri_sayisi_sd)
                    
                    for row in rows[start_idx:]:
                        try:
                            times.append(datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S"))
                            values.append(float(row[1]))
                        except:
                            continue
                
                ax.plot(times, values, 'r-', linewidth=1.5)
                ax.set_title(f"Debimetre (Son {len(values)} veri)", fontsize=10)
                ax.set_ylabel("L/dk", fontsize=9)
                ax.tick_params(axis='both', which='major', labelsize=7)
                ax.grid(True, linestyle=':', linewidth=0.5)
            
            except Exception as e:
                ax.set_title(f"Hata: {str(e)}", fontsize=10)
        
        canvas.draw()

def show_calculations_page():
    calc_page = tk.Toplevel(root)
    calc_page.title("Hesaplamalar")
    calc_page.attributes('-fullscreen', True)
    calc_page.configure(bg="#e6f2ff")

    btn_back = ttk.Button(calc_page, text="Ana Sayfa", command=calc_page.destroy)
    btn_back.pack(pady=5)

    # Sensor buttons
    temp_frame = tk.Frame(calc_page, bg="#e6f2ff")
    temp_frame.pack(fill='x', pady=2)
    for i in range(1, 9):
        ttk.Button(temp_frame, text=f"T{i}", command=lambda i=i: calculate_stats(f'T{i}'), width=3).pack(side='left', padx=2)
    ttk.Button(temp_frame, text="SD1", command=lambda: calculate_stats('SD1'), width=3).pack(side='left', padx=2)

    hum_frame = tk.Frame(calc_page, bg="#e6f2ff")
    hum_frame.pack(fill='x', pady=2)
    for i in range(1, 9):
        ttk.Button(hum_frame, text=f"H{i}", command=lambda i=i: calculate_stats(f'H{i}'), width=3).pack(side='left', padx=2)

    # Stats display
    stats_frame = tk.Frame(calc_page, bg="#e6f2ff", padx=10, pady=10)
    stats_frame.pack(fill='both', expand=True)

    global stats_labels
    stats_labels = {
        'mean': ttk.Label(stats_frame, text="Ortalama: --", font=MEDIUM_FONT),
        'median': ttk.Label(stats_frame, text="Medyan: --", font=MEDIUM_FONT),
        'std': ttk.Label(stats_frame, text="Standart Sapma: --", font=MEDIUM_FONT),
        'min': ttk.Label(stats_frame, text="Minimum: --", font=MEDIUM_FONT),
        'max': ttk.Label(stats_frame, text="Maksimum: --", font=MEDIUM_FONT),
        'mode': ttk.Label(stats_frame, text="Mod: --", font=MEDIUM_FONT)
    }

    for label in stats_labels.values():
        label.pack(anchor='w', pady=2)

def calculate_stats(sensor):
    values = []
    
    try:
        if sensor.startswith('T') or sensor.startswith('H'):
            filename = os.path.join(DESKTOP_PATH, "dht_data.csv")
            with open(filename, 'r') as f:
                reader = csv.reader(f)
                next(reader)
                
                sensor_num = int(sensor[1:])
                col_index = 1 + (sensor_num-1)*2 if sensor.startswith('T') else 2 + (sensor_num-1)*2
                
                rows = list(reader)
                start_idx = max(0, len(rows) - veri_sayisi_dht)
                
                for row in rows[start_idx:]:
                    try:
                        values.append(float(row[col_index]))
                    except:
                        continue
        elif sensor == 'SD1':
            filename = os.path.join(DESKTOP_PATH, "flow_data.csv")
            with open(filename, 'r') as f:
                reader = csv.reader(f)
                next(reader)
                
                rows = list(reader)
                start_idx = max(0, len(rows) - veri_sayisi_sd)
                
                for row in rows[start_idx:]:
                    try:
                        values.append(float(row[1]))
                    except:
                        continue

        if len(values) > 0:
            rounded_values = [round(v, 1) for v in values]
            
            stats_labels['mean'].config(text=f"Ortalama: {np.mean(values):.2f}")
            stats_labels['median'].config(text=f"Medyan: {np.median(values):.2f}")
            stats_labels['std'].config(text=f"Standart Sapma: {np.std(values):.2f}")
            stats_labels['min'].config(text=f"Minimum: {min(values):.2f}")
            stats_labels['max'].config(text=f"Maksimum: {max(values):.2f}")
            
            try:
                mod_value = mode(rounded_values)
                stats_labels['mode'].config(text=f"Mod: {mod_value:.1f}")
            except:
                stats_labels['mode'].config(text="Mod: Belirsiz")
        else:
            for label in stats_labels.values():
                label.config(text="Veri yok!")

    except Exception as e:
        for label in stats_labels.values():
            label.config(text=f"Hata: {str(e)}")

def start_experiment():
    global running, dht_thread, sd_thread, veri_sayisi_dht, veri_sayisi_sd
    if not running:
        veri_sayisi_dht = 0
        veri_sayisi_sd = 0
        data_counter_dht.config(text=f"DHT Veri: 0")
        data_counter_sd.config(text=f"Debi Veri: 0")
        running = True
        pause_event.set()
        dht_thread = threading.Thread(target=read_dht_loop, daemon=True)
        sd_thread = threading.Thread(target=read_sd_loop, daemon=True)
        dht_thread.start()
        sd_thread.start()
        btn_show_graph.config(state='disabled')
        btn_calculations.config(state='disabled')

def stop_experiment():
    pause_event.clear()
    btn_show_graph.config(state='normal')
    btn_calculations.config(state='normal')

def resume_experiment():
    pause_event.set()
    btn_show_graph.config(state='disabled')
    btn_calculations.config(state='disabled')

def stop_and_exit():
    global running
    running = False
    pause_event.set()
    root.destroy()

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

def update_dht_status(state):
    status_dht.config(text=state)

def update_sd_status(state):
    status_sd.config(text=state)

# ---------------------------- GUI SETUP ----------------------------
root = tk.Tk()
root.title("SUBÜ - DATALOGGER")
root.attributes('-fullscreen', True)
root.configure(bg="#e6f2ff")

style = ttk.Style(root)
style.theme_use('default')
style.configure('TLabel', background='#e6f2ff', foreground='#003366', font=SMALL_FONT)
style.configure('Header.TLabel', background='#e6f2ff', foreground='#003366', font=LARGE_FONT)
style.configure('Status.TLabel', background='#0066CC', foreground='white', font=SMALL_FONT)
style.configure('TButton', font=MEDIUM_FONT, padding=4)
style.configure('Status.TFrame', background='#e6f2ff', relief='sunken', borderwidth=2)

# Header
header = ttk.Label(root, text="SUBÜ - DATALOGGER", style='Header.TLabel')
header.place(relx=0.5, rely=0.02, anchor='n')

# Main content area
main_frame = tk.Frame(root, bg="#e6f2ff")
main_frame.place(x=0, y=40, width=480, height=220)

# Left column - Sensor values
sensor_frame = tk.Frame(main_frame, bg="#e6f2ff")
sensor_frame.place(x=10, y=0, width=250, height=220)

for i in range(1, 9):
    labels[f"T{i}"] = ttk.Label(sensor_frame, text=f"T{i}: -- °C", font=SENSOR_FONT)
    labels[f"T{i}"].place(x=10, y=(i-1)*25)

for i in range(1, 9):
    labels[f"H{i}"] = ttk.Label(sensor_frame, text=f"H{i}: -- %", font=SENSOR_FONT)
    labels[f"H{i}"].place(x=120, y=(i-1)*25)

labels['SD1'] = ttk.Label(sensor_frame, text="SD1: -- L/dk", font=SENSOR_FONT)
labels['SD1'].place(x=10, y=200)

# Right column - Status boxes
status_frame = tk.Frame(main_frame, bg="#e6f2ff")
status_frame.place(x=270, y=0, width=200, height=220)

dht_status_frame = ttk.LabelFrame(status_frame, text="Sıcaklık/Nem", width=180, height=50)
dht_status_frame.pack(pady=5)
status_dht = ttk.Label(dht_status_frame, text="Bekliyor", style='Status.TLabel')
status_dht.place(relx=0.5, rely=0.5, anchor='center')

sd_status_frame = ttk.LabelFrame(status_frame, text="Su Debisi", width=180, height=50)
sd_status_frame.pack(pady=5)
status_sd = ttk.Label(sd_status_frame, text="Bekliyor", style='Status.TLabel')
status_sd.place(relx=0.5, rely=0.5, anchor='center')

cpu_frame = ttk.LabelFrame(status_frame, text="CPU Sıcaklık", width=180, height=50)
cpu_frame.pack(pady=5)
status_cpu = ttk.Label(cpu_frame, text="-- °C", style='Status.TLabel')
status_cpu.place(relx=0.5, rely=0.5, anchor='center')

data_frame = ttk.LabelFrame(status_frame, text="Veri Sayacı", width=180, height=50)
data_frame.pack(pady=5)
data_counter_dht = ttk.Label(data_frame, text="DHT: 0", style='Status.TLabel')
data_counter_dht.place(relx=0.3, rely=0.5, anchor='center')
data_counter_sd = ttk.Label(data_frame, text="Debi: 0", style='Status.TLabel')
data_counter_sd.place(relx=0.7, rely=0.5, anchor='center')

# Control buttons - Left side
btn_left_frame = tk.Frame(root, bg="#e6f2ff")
btn_left_frame.place(x=10, y=270, width=240, height=50)

btn_start = ttk.Button(btn_left_frame, text="Başlat", command=start_experiment, width=10)
btn_start.pack(side='left', padx=5)
btn_stop = ttk.Button(btn_left_frame, text="Durdur", command=stop_experiment, state='disabled', width=10)
btn_stop.pack(side='left', padx=5)
btn_resume = ttk.Button(btn_left_frame, text="Devam", command=resume_experiment, state='disabled', width=10)
btn_resume.pack(side='left', padx=5)

# Control buttons - Right side
btn_right_frame = tk.Frame(root, bg="#e6f2ff")
btn_right_frame.place(x=260, y=270, width=210, height=50)

btn_calculations = ttk.Button(btn_right_frame, text="Hesaplamalar", command=show_calculations_page, width=10)
btn_calculations.pack(side='top', padx=5)
btn_show_graph = ttk.Button(btn_right_frame, text="Grafikler", command=show_graph_page, width=10, state='disabled')
btn_show_graph.pack(side='top', padx=5)
btn_exit = ttk.Button(btn_right_frame, text="Çıkış", command=stop_and_exit, width=10)
btn_exit.pack(side='top', padx=5)

# Start the application
update_buttons()
update_cpu_temp()
root.mainloop()