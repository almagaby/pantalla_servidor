import socket
import cv2
import numpy as np
import struct
import threading
import tkinter as tk
import os

# Variable global para el zoom de cada conexión
zoom_levels = [1.0] * 4
connections = []
ips = []
ips_lock = threading.Lock()

# Carpeta para guardar las capturas de pantalla
screenshot_folder = "screenshots"
if not os.path.exists(screenshot_folder):
    os.makedirs(screenshot_folder)

def receive_screen_data(conn, window_name, zoom_level_index):
    global zoom_levels, connections, ips
    data = b""
    payload_size = struct.calcsize(">L")
    
    while True:
        while len(data) < payload_size:
            data_chunk = conn.recv(4096)
            if not data_chunk:
                return
            data += data_chunk
        packed_msg_size = data[:payload_size]
        data = data[payload_size:]
        msg_size = struct.unpack(">L", packed_msg_size)[0]
        while len(data) < msg_size:
            data_chunk = conn.recv(4096)
            if not data_chunk:
                return
            data += data_chunk
        frame_data = data[:msg_size]
        data = data[msg_size:]
        frame = np.frombuffer(frame_data, dtype=np.uint8)
        frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)

        # Aplicar zoom
        height, width = frame.shape[:2]
        new_height, new_width = int(height * zoom_levels[zoom_level_index]), int(width * zoom_levels[zoom_level_index])
        frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        
        cv2.imshow(window_name, frame)

        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            break

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('+'):
            zoom_levels[zoom_level_index] += 0.1
        elif key == ord('-'):
            zoom_levels[zoom_level_index] = max(0.1, zoom_levels[zoom_level_index] - 0.1)  # Evitar zoom negativo o cero
        elif key == ord('c'):
            screenshot_path = os.path.join(screenshot_folder, f'screenshot_{window_name}.png')
            cv2.imwrite(screenshot_path, frame)
            print(f"Screenshot taken for {window_name}. Saved as {screenshot_path}")

    cv2.destroyWindow(window_name)
    with ips_lock:
        conn.close()
        if conn.getpeername()[0] in ips:
            ips.remove(conn.getpeername()[0])
            update_ip_buttons()

def handle_connection(conn, address):
    global connections, ips, ips_lock
    with ips_lock:
        ips.append(address[0])
        update_ip_buttons()
    connections.append((conn, address[0]))

def update_ip_buttons():
    global ips
    # Eliminar todos los botones actuales
    for widget in ip_frame.winfo_children():
        widget.destroy()
        
    # Crear botones para cada IP
    for ip in ips:
        btn = tk.Button(ip_frame, text=ip, command=lambda ip=ip: connect_to_ip(ip))
        btn.pack(pady=5)

def connect_to_ip(ip):
    for conn, conn_ip in connections:
        if conn_ip == ip:
            window_name = f'Received Screen {ips.index(ip) + 1}'
            threading.Thread(target=receive_screen_data, args=(conn, window_name, ips.index(ip))).start()
            break

# Configuración de la interfaz gráfica
root = tk.Tk()
root.title("Screen Viewer")

ip_frame = tk.Frame(root)
ip_frame.pack(pady=20)

# Iniciar el servidor en un hilo separado
def start_server():
    host = '0.0.0.0'
    port = 5001  # Usa un puerto diferente que esté libre
    server_socket = socket.socket()
    server_socket.bind((host, port))
    server_socket.listen(4)  # Escuchar hasta 4 conexiones
    print("Server listening on port", port)

    while True:
        conn, address = server_socket.accept()
        print("Connection from: " + str(address))
        threading.Thread(target=handle_connection, args=(conn, address)).start()

server_thread = threading.Thread(target=start_server)
server_thread.daemon = True
server_thread.start()

# Función para cerrar la ventana de Tkinter
def on_closing():
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing) 
root.mainloop()