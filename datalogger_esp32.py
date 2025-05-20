import serial
import time

SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2) 
    print("Seri bağlantı kuruldu.")
except serial.SerialException as e:
    print(f"Seri port hatası: {e}")
    exit()

try:
    while True:
        line = ser.readline().decode('utf-8').strip()
        if line:
            try:
                flow_rate = float(line)
                print(f"Anlık Su Debisi: {flow_rate:.2f} L/dk")
            except ValueError:
                print(f"Geçersiz veri: {line}")
except KeyboardInterrupt:
    print("Kapatılıyor...")
finally:
    ser.close()


