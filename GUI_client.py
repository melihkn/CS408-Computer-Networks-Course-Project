import socket
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

class ClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("File Client")
        self.client_socket = None
        self.username = ""
        self.connected = False
        self.filepath = ""

        self.create_widgets()

    def create_widgets(self):
        frame = tk.Frame(self.root)
        frame.pack(pady=10)

        tk.Label(frame, text="Server IP:").grid(row=0, column=0, sticky="e")
        self.server_ip_entry = tk.Entry(frame)
        self.server_ip_entry.grid(row=0, column=1)

        tk.Label(frame, text="Port:").grid(row=1, column=0, sticky="e")
        self.port_entry = tk.Entry(frame)
        self.port_entry.grid(row=1, column=1)

        tk.Label(frame, text="Username:").grid(row=2, column=0, sticky="e")
        self.username_entry = tk.Entry(frame)
        self.username_entry.grid(row=2, column=1)

        tk.Button(frame, text="Connect", command=self.connect_to_server).grid(row=3, column=0, columnspan=2, pady=10)

        self.log = ScrolledText(self.root, width=80, height=20, state='disabled')
        self.log.pack(pady=10)

        button_frame = tk.Frame(self.root)
        button_frame.pack()

        tk.Button(button_frame, text="Upload File", command=self.upload_file).grid(row=0, column=0, padx=5)
        tk.Button(button_frame, text="Download File", command=self.download_file).grid(row=0, column=1, padx=5)
        tk.Button(button_frame, text="List Files", command=self.list_files).grid(row=0, column=2, padx=5)
        tk.Button(button_frame, text="Delete File", command=self.delete_file).grid(row=0, column=3, padx=5)
        tk.Button(button_frame, text="Disconnect", command=self.disconnect).grid(row=0, column=4, padx=5)

    def log_message(self, message):
        self.log.config(state='normal')
        self.log.insert(tk.END, f"{message}\n")
        self.log.see(tk.END)
        self.log.config(state='disabled')

    def connect_to_server(self):
        server_ip = self.server_ip_entry.get()
        port = self.port_entry.get()
        self.username = self.username_entry.get()

        if not server_ip or not port or not self.username:
            messagebox.showerror("Error", "Please enter server IP, port, and username.")
            return

        try:
            port = int(port)
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid port number.")
            return

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((server_ip, port))
            self.log_message(f"[CONNECTED] Connected to server at {server_ip}:{port}")
            self.authenticate()
        except Exception as e:
            self.log_message(f"[ERROR] Unable to connect to server: {e}")
            return

    def authenticate(self):
        self.send_message(self.username, self.client_socket)
        response = self.receive_message(self.client_socket)
        if response and response.startswith("[AUTHENTICATED]"):
            self.connected = True
            self.log_message(f"[AUTHENTICATED] Welcome, {self.username}!")
            threading.Thread(target=self.listener, daemon=True).start()
        else:
            self.log_message(response)
            self.client_socket.close()
            self.client_socket = None

    def send_message(self, message, connection_socket : socket.socket):
        try:
            connection_socket.send(len(message).to_bytes(4, byteorder="big"))
            connection_socket.send(message.encode())
        except Exception as e:
            self.log_message(f"[ERROR] Failed to send message: {e}")

    def receive_message(self, connection_socket):
        try:
            message_length_bytes = connection_socket.recv(4)
            if not message_length_bytes:
                return None
            message_length = int.from_bytes(message_length_bytes, byteorder="big")
            message = connection_socket.recv(message_length).decode()
            return message
        except Exception as e:
            self.log_message(f"[ERROR] Failed to receive message: {e}")
            return None

    def upload_file(self):
        if not self.connected:
            messagebox.showerror("Error", "Not connected to server.")
            return

        self.filepath = filedialog.askopenfilename()
        if not self.filepath:
            return

        if not os.path.exists(self.filepath):
            self.log_message("[ERROR] File does not exist.")
            return

        filesize = os.path.getsize(self.filepath)
        filename = os.path.basename(self.filepath)
        packet = f"[UPLOAD]|[{filename}]|[{filesize}]"
        self.send_message(packet, self.client_socket)
        #self.send_file(filepath, filename)
        #threading.Thread(target=self.send_file, args=(filepath, filename), daemon=True).start()

    def send_file(self, port, filename):


        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as data_socket:
            data_socket.connect((self.server_ip_entry.get(), port))

            try:
                with open(self.filepath, "rb") as file:
                    self.log_message(f"[UPLOADING] Sending {filename}...")
                    while chunk:= file.read(1024):
                        data_socket.send(chunk)
                self.log_message(f"[UPLOAD COMPLETE] {filename} uploaded.")
            except Exception as e:
                self.log_message(f"[ERROR] Failed to upload file: {e}")
        """try:
            with open(self.filepath, "rb") as file:
                self.log_message(f"[UPLOADING] Sending {filename}...")
                while True:
                    chunk = file.read(1024)
                    if not chunk:
                        break
                    stateless_conn.send(chunk)
            self.log_message(f"[UPLOAD COMPLETE] {filename} uploaded.")
        except Exception as e:
            self.log_message(f"[ERROR] Failed to upload file: {e}")"""

    def download_file(self):
        if not self.connected:
            messagebox.showerror("Error", "Not connected to server.")
            return

        filename = simple_input_dialog("Enter the name of the file to download:")
        if not filename:
            return

        uploader_name = simple_input_dialog("Enter the uploader's username:")
        if not uploader_name:
            return

        message = f"[DOWNLOAD]|[{filename}]|[{uploader_name}]"
        self.send_message(message, self.client_socket)

    def list_files(self):
        if not self.connected:
            messagebox.showerror("Error", "Not connected to server.")
            return

        self.send_message("[LIST_FILES]", self.client_socket)

    def delete_file(self):
        if not self.connected:
            messagebox.showerror("Error", "Not connected to server.")
            return

        filename = simple_input_dialog("Enter the name of the file to delete:")
        if not filename:
            return

        message = f"[DELETE]|[{filename}]"
        self.send_message(message, self.client_socket)

    def disconnect(self):
        if self.connected:
            self.send_message("[DISCONNECT]", self.client_socket)
            self.client_socket.close()
            self.connected = False
            self.log_message("[DISCONNECTED] Connection closed.")
        self.root.quit()

    def listener(self):
        while self.connected:
            response = self.receive_message(self.client_socket)
            if not response:
                self.log_message("[DISCONNECTED] Connection closed by server.")
                self.connected = False
                break

            if response.startswith("[ERROR]"):
                self.log_message(f"[SERVER ERROR]: {response}")

            elif response.startswith("[NOTIFICATION]"):
                self.log_message(f"[SERVER NOTIFICATION]: {response}")

            elif response.startswith("[UPLOAD]"):
                if response.startswith("[UPLOAD][SERVER RESPONSE]"):
                    self.log_message(f"{response}")
                else:
                    _, port, filename = response.split("|")
                    port = int(port.strip("[]"))
                    filename = filename.strip("[]")

                    threading.Thread(target=self.send_file, args=(port, filename), daemon=True).start()

            elif response.startswith("[DOWNLOAD]"):

                if response.startswith("[ERROR]"):
                    self.log_message(f"[SERVER RESPONSE]: {response}")
                elif response.startswith("[DOWNLOAD][SERVER RESPONSE]"):
                    self.log_message(f"{response}")
                else:
                    _, temp_port, temp_filename = response.split("|")
                    temp_port = int(temp_port.strip("[]"))
                    temp_filename = temp_filename.strip("[]")
                    threading.Thread(target=self.receive_file, args=(temp_port, temp_filename), daemon=True).start()
                    #self.receive_file(filename, filesize)

            elif response.startswith("[DELETE]"):
                self.log_message(f"{response}")

            elif response.startswith("[LIST_FILES]"):
                self.log_message(f"[AVAILABLE FILES]: {response[12:]}")

    def receive_file(self, port, filename):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as data_socket:
            data_socket.connect((self.server_ip_entry.get(), port))
            download_dir = filedialog.askdirectory(title="Select Download Directory")
            filepath = os.path.join(download_dir, filename)

            filesize = self.receive_message(data_socket)
            filesize = int(filesize.strip("[] "))

            try:
                with open(filepath, "wb") as file:
                    bytes_received = 0
                    while bytes_received < filesize:
                        data = data_socket.recv(min(1024, filesize - bytes_received))
                        if not data:
                            break
                        file.write(data)
                        bytes_received += len(data)
                self.log_message(f"[DOWNLOAD COMPLETE] File saved as '{filepath}'.")
            except Exception as e:
                self.log_message(f"[ERROR] Failed to download file: {e}")
                self.log_message(f"[DOWNLOAD COMPLETE] File saved as '{filepath}'.")

def simple_input_dialog(prompt):
    input_window = tk.Toplevel()
    input_window.title("Input")
    tk.Label(input_window, text=prompt).pack(pady=5)
    input_var = tk.StringVar()
    tk.Entry(input_window, textvariable=input_var).pack(pady=5)
    result = []

    def on_ok():
        result.append(input_var.get())
        input_window.destroy()

    tk.Button(input_window, text="OK", command=on_ok).pack(pady=5)
    input_window.wait_window()
    return result[0] if result else None

if __name__ == "__main__":
    root = tk.Tk()
    app = ClientGUI(root)
    root.mainloop()
