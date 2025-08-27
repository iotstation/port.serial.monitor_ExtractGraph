import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import serial
import serial.tools.list_ports
import threading
import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import re
import os

class SerialMonitor:
    def __init__(self, master):
        self.master = master
        self.master.title("Serial Monitor")
        self.master.geometry("1400x800")

        # Serial variables
        self.ser = None
        self.connection_active = False
        self.logging_active = False
        self.graph_active = False
        self.log_file = None
        self.temp_data = []  # Store temperature values
        self.hum_data = []   # Store humidity values
        self.timestamps = []
        self.y_min = 20.0    # Initial minimum y-axis value
        self.y_max = 50.0    # Initial maximum y-axis value
        self.y_range = 30.0  # Initial y-axis range

        # Top frame
        self.top_frame = tk.Frame(master, bg="#f0f0f0")
        self.top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        # Port selection
        self.port_label = tk.Label(self.top_frame, text="Port:", font=("Arial", 12))
        self.port_label.pack(side=tk.LEFT, padx=5)

        self.port_combobox = ttk.Combobox(self.top_frame, font=("Arial", 12), width=15)
        self.port_combobox.pack(side=tk.LEFT, padx=5)
        self.refresh_ports()

        self.baud_label = tk.Label(self.top_frame, text="Baud Rate:", font=("Arial", 12))
        self.baud_label.pack(side=tk.LEFT, padx=5)

        self.baud_combobox = ttk.Combobox(
            self.top_frame,
            values=["9600", "19200", "38400", "57600", "115200"],
            font=("Arial", 12),
            width=10,
        )
        self.baud_combobox.current(4)  # Default to 115200 to match ESP32
        self.baud_combobox.pack(side=tk.LEFT, padx=5)

        self.connect_button = tk.Button(
            self.top_frame, text="Connect", command=self.connect, font=("Arial", 12)
        )
        self.connect_button.pack(side=tk.LEFT, padx=10)

        self.disconnect_button = tk.Button(
            self.top_frame, text="Disconnect", command=self.disconnect, font=("Arial", 12)
        )
        self.disconnect_button.pack(side=tk.LEFT, padx=10)

        self.start_logging_button = tk.Button(
            self.top_frame, text="Start Logging", command=self.start_logging, font=("Arial", 12)
        )
        self.start_logging_button.pack(side=tk.LEFT, padx=10)

        self.stop_logging_button = tk.Button(
            self.top_frame, text="Stop Logging", command=self.stop_logging, font=("Arial", 12)
        )
        self.stop_logging_button.pack(side=tk.LEFT, padx=10)

        self.start_graph_button = tk.Button(
            self.top_frame, text="Start Graph", command=self.start_graph, font=("Arial", 12)
        )
        self.start_graph_button.pack(side=tk.LEFT, padx=10)

        self.stop_graph_button = tk.Button(
            self.top_frame, text="Stop Graph", command=self.stop_graph, font=("Arial", 12)
        )
        self.stop_graph_button.pack(side=tk.LEFT, padx=10)

        self.zoom_in_button = tk.Button(
            self.top_frame, text="Zoom In", command=self.zoom_in, font=("Arial", 12)
        )
        self.zoom_in_button.pack(side=tk.LEFT, padx=10)

        self.zoom_out_button = tk.Button(
            self.top_frame, text="Zoom Out", command=self.zoom_out, font=("Arial", 12)
        )
        self.zoom_out_button.pack(side=tk.LEFT, padx=10)

        # Log display
        self.log_text = scrolledtext.ScrolledText(
            master, width=160, height=15, font=("Consolas", 14)
        )
        self.log_text.pack(padx=10, pady=5)

        # Graph area
        self.figure = Figure(figsize=(10, 5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Temperature and Humidity", fontsize=18)
        self.ax.set_xlabel("Time", fontsize=16)
        self.ax.set_ylabel("Value", fontsize=16)
        self.temp_line, = self.ax.plot([], [], "b-", label="Temperature (°C)", linewidth=2)
        self.hum_line, = self.ax.plot([], [], "r-", label="Humidity (%)", linewidth=2)
        self.ax.legend()

        self.canvas = FigureCanvasTkAgg(self.figure, master)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=(0, 10))

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combobox["values"] = ports
        if ports:
            self.port_combobox.current(0)

    def connect(self):
        port = self.port_combobox.get()
        baud = self.baud_combobox.get()
        try:
            self.ser = serial.Serial(port, baudrate=int(baud), timeout=1)
            self.connection_active = True
            threading.Thread(target=self.read_from_port, daemon=True).start()
            self.log_text.insert(tk.END, f"[INFO] Connected to {port} at {baud} baud\n")
        except Exception as e:
            self.log_text.insert(tk.END, f"[ERROR] {e}\n")

    def disconnect(self):
        self.connection_active = False
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.log_text.insert(tk.END, "[INFO] Disconnected\n")

    def start_logging(self):
        self.log_file = filedialog.asksaveasfile(
            mode="w", defaultextension=".txt", filetypes=[("Text Files", "*.txt")]
        )
        if self.log_file:
            self.logging_active = True
            self.log_text.insert(tk.END, "[INFO] Logging started\n")

    def stop_logging(self):
        self.logging_active = False
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        self.log_text.insert(tk.END, "[INFO] Logging stopped\n")

    def start_graph(self):
        self.graph_active = True
        self.temp_data.clear()
        self.hum_data.clear()
        self.timestamps.clear()
        self.ax.cla()
        self.ax.set_title("Temperature and Humidity", fontsize=18)
        self.ax.set_xlabel("Time", fontsize=16)
        self.ax.set_ylabel("Value", fontsize=16)
        self.temp_line, = self.ax.plot([], [], "b-", label="Temperature (°C)", linewidth=2)
        self.hum_line, = self.ax.plot([], [], "r-", label="Humidity (%)", linewidth=2)
        self.ax.legend()
        self.ax.set_ylim(self.y_min, self.y_max)
        self.log_text.insert(tk.END, "[INFO] Graph started (waiting for data...)\n")
        self.update_graph()

    def stop_graph(self):
        self.graph_active = False
        self.log_text.insert(tk.END, "[INFO] Graph stopped\n")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.figure.savefig(f"graph_stop_{timestamp}.png", dpi=300, bbox_inches="tight")

    def zoom_in(self):
        self.y_range /= 2.0
        self.y_min = max(min(self.temp_data + self.hum_data) - self.y_range / 2, 0)
        self.y_max = self.y_min + self.y_range
        self.ax.set_ylim(self.y_min, self.y_max)
        self.canvas.draw()

    def zoom_out(self):
        self.y_range *= 2.0
        self.y_min = max(min(self.temp_data + self.hum_data) - self.y_range / 2, 0)
        self.y_max = self.y_min + self.y_range
        self.ax.set_ylim(self.y_min, self.y_max)
        self.canvas.draw()

    def update_graph(self):
        if self.graph_active:
            if self.temp_data and self.hum_data:
                self.temp_line.set_xdata(range(len(self.timestamps)))
                self.temp_line.set_ydata(self.temp_data)
                self.hum_line.set_xdata(range(len(self.timestamps)))
                self.hum_line.set_ydata(self.hum_data)
                self.ax.set_xticks(range(len(self.timestamps)))
                self.ax.set_xticklabels(self.timestamps, rotation=45, ha="right")
                data_min = min(self.temp_data + self.hum_data)
                data_max = max(self.temp_data + self.hum_data)
                if data_max > self.y_max or data_min < self.y_min:
                    self.y_min = max(data_min - self.y_range / 2, 0)
                    self.y_max = self.y_min + self.y_range
                    self.ax.set_ylim(self.y_min, self.y_max)
                self.ax.relim()
                self.ax.autoscale_view()
            else:
                self.temp_line.set_xdata([0])
                self.temp_line.set_ydata([0])
                self.hum_line.set_xdata([0])
                self.hum_line.set_ydata([0])
            self.canvas.draw_idle()
            self.master.after(200, self.update_graph)

    def read_from_port(self):
        while self.connection_active:
            try:
                line = self.ser.readline().decode("utf-8").strip()
                if line:
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    self.log_text.insert(tk.END, f"[{timestamp}] {line}\n")
                    self.log_text.see(tk.END)

                    if self.logging_active and self.log_file:
                        self.log_file.write(f"[{timestamp}] {line}\n")
                        self.log_file.flush()

                    if self.graph_active:
                        # List of regex patterns to match different formats
                        patterns = [
                            # Format: Temperature: X.XX C, Humidity: Y.YY %
                            r"Temperature: (\d+\.\d{1,2}) C, Humidity: (\d+\.\d{1,2}) %",
                            # Format: Sent: X.X,Y.Y
                            r"Sent: (\d+\.\d),(\d+\.\d)",
                            # Format: X.X,Y.Y (Bluetooth numeric data)
                            r"(\d+\.\d),(\d+\.\d)",
                            # Format: Temperature: X.XX, Humidity: Y.YY (without units)
                            r"Temperature: (\d+\.\d{1,2}), Humidity: (\d+\.\d{1,2})",
                        ]
                        temp, hum = None, None
                        for pattern in patterns:
                            match = re.search(pattern, line)
                            if match:
                                temp, hum = float(match.group(1)), float(match.group(2))
                                break
                        if temp is not None and hum is not None:
                            self.temp_data.append(temp)
                            self.hum_data.append(hum)
                            self.timestamps.append(timestamp)
                        else:
                            self.log_text.insert(tk.END, f"[WARN] Invalid format: {line}\n")
            except Exception:
                break

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialMonitor(root)
    root.mainloop()