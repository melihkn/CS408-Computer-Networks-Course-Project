import os
import threading
import socket
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

HOST = "0.0.0.0"
data_port_base = 5000  # Base port for data connections
clients = {}  # Active clients
uploads = {}  # Track uploaded files by clients
write_lock = threading.Lock()  # Exclusive access for uploads
read_lock = threading.RLock()  # Allows concurrent reads
lock = threading.Lock()  # Lock for notifications
read_count = 0  # Tracks active readers

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("File Server")
        self.port = tk.IntVar()
        self.storage_dir = ""
        self.server_socket = None
        self.is_running = False

        self.create_widgets()

    def create_widgets(self):
        frame = tk.Frame(self.root)
        frame.pack(pady=10)

        tk.Label(frame, text="Port:").grid(row=0, column=0, sticky="e")
        tk.Entry(frame, textvariable=self.port).grid(row=0, column=1)

        tk.Button(frame, text="Select Storage Directory", command=self.select_directory).grid(row=1, column=0, columnspan=2)

        tk.Button(frame, text="Start Server", command=self.start_server).grid(row=2, column=0, columnspan=2, pady=10)

        self.log = ScrolledText(self.root, width=80, height=20, state='disabled')
        self.log.pack(pady=10)

    def select_directory(self):
        self.storage_dir = filedialog.askdirectory()
        self.log_message(f"Storage directory set to: {self.storage_dir}")

    def start_server(self):
        if not self.storage_dir:
            messagebox.showerror("Error", "Please select a storage directory.")
            return

        port = self.port.get()
        if not port:
            messagebox.showerror("Error", "Please enter a valid port number.")
            return

        threading.Thread(target=self.run_server, args=(port,), daemon=True).start()

    def run_server(self, port):
        global HOST

        self.is_running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((HOST, port))
        self.server_socket.listen(5)
        self.log_message(f"[STARTING] Server is starting on {HOST}:{port}")
        self.log_message("[LISTENING] Server is listening for connections...")

        while self.is_running:
            try:
                client_socket, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, address), daemon=True).start()
                self.log_message(f"[NEW CONNECTION] {address} connected.")
                self.log_message(f"[ACTIVE CONNECTIONS] {len(clients)}")
            except Exception as e:
                self.log_message(f"[ERROR] {e}")
                break

    def log_message(self, message):
        self.log.config(state='normal')
        self.log.insert(tk.END, f"{message}\n")
        self.log.see(tk.END)
        self.log.config(state='disabled')

    def send_message(self, client_socket, message):
        try:
            client_socket.send((len(message)).to_bytes(4, byteorder="big"))
            client_socket.send(message.encode())
        except Exception as e:
            self.log_message(f"[ERROR] Failed to send message: {e}")

    def receive_message(self, client_socket):
        try:
            message_length_bytes = client_socket.recv(4)
            if not message_length_bytes:
                return None
            message_length = int.from_bytes(message_length_bytes, byteorder="big")
            message = client_socket.recv(message_length).decode()
            return message
        except Exception as e:
            self.log_message(f"[ERROR] Failed to receive message: {e}")
            return None

    def notify_uploader(self, uploader_name, filename, downloader):
        with lock:
            if uploader_name != downloader and uploader_name in clients:
                uploader_socket = clients[uploader_name]
                try:
                    self.send_message(uploader_socket, f"[NOTIFICATION]: Your file '{filename}' was downloaded by {downloader}.")
                    self.log_message(f"[NOTIFICATION SENT] To: {uploader_name} - File '{filename}' downloaded by {downloader}.")
                except Exception as e:
                    self.log_message(f"[ERROR] Failed to notify {uploader_name}: {e}")
                    if uploader_name in clients:
                        del clients[uploader_name]

    def handle_upload(self, data_socket, client_socket, username, filename, filesize):
        unique_filename = f"{username}_{filename}"
        filepath = os.path.join(self.storage_dir, unique_filename)
        filesize = int(filesize)
        with write_lock:
            with open(filepath, "wb") as file:
                bytes_received = 0
                self.log_message(f"[UPLOADING] Receiving {filename} from {username}...")
                while bytes_received < filesize:
                    data = data_socket.recv(min(1024, filesize - bytes_received))
                    if not data:
                        break
                    file.write(data)
                    bytes_received += len(data)
            uploads[filename] = username

        self.send_message(client_socket, f"[UPLOAD][SERVER RESPONSE] File '{filename}' uploaded successfully.")
        self.log_message(f"[UPLOAD SUCCESS] {filename} uploaded by {username}.")

    def handle_download(self, data_socket, client_socket, filename, uploader, downloader):
        global read_count

        stored_filename = f"{downloader}_{filename}"
        print(stored_filename)
        filepath = os.path.join(self.storage_dir, stored_filename)

        with read_lock:
            read_count += 1
            if read_count == 1:
                write_lock.acquire()

        try:
            if os.path.exists(filepath):
                filesize = os.path.getsize(filepath)
                self.send_message(data_socket, f"{filesize}")

                with open(filepath, "rb") as file:
                    while chunk := file.read(1024):
                        data_socket.send(chunk)
                self.log_message(f"[DOWNLOAD SUCCESS] {filename} sent to {downloader}.")
                self.notify_uploader(downloader, filename, uploader)
                self.send_message(client_socket, "[DOWNLOADS][SERVER RESPONSE] File downloaded")
            else:
                self.send_message(client_socket, "[ERROR]: File not found.")
        finally:
            with read_lock:
                read_count -= 1
                if read_count == 0:
                    write_lock.release()

    def handle_client(self, client_socket: socket.socket, address):
        username = None

        try:
            # Authenticate the user
            while True:
                username = self.receive_message(client_socket)
                if not username:
                    break
                with lock:
                    if username in clients:
                        self.send_message(client_socket, "[ERROR]: Username already in use.")
                    else:
                        clients[username] = client_socket
                        self.send_message(client_socket, f"[AUTHENTICATED] Welcome, {username}!")
                        self.log_message(f"[AUTHENTICATED] {username} connected.")
                        break

            # Handle client commands
            while True:
                command = self.receive_message(client_socket)
                if not command:
                    break

                if command.startswith("[UPLOAD]"):
                    _, filename, filesize = command.split("|")
                    filename = filename.strip("[] ")
                    filesize = int(filesize.strip("[] "))
                    #threading.Thread(target=self.handle_upload, args=(client_socket, username, filename, filesize), daemon=True).start()
                    #self.handle_upload(client_socket, username, filename, filesize)
                    port = self.start_data_socket_upload(filename, filesize, username, client_socket)
                    self.send_message(client_socket, f"[UPLOAD]|[{port}]|[{filename}]")
                elif command.startswith("[DOWNLOAD]"):
                    _, filename, uploader = command.split("|")
                    filename = filename.strip("[] ")
                    uploader = uploader.strip("[] ")
                    port = self.start_data_socket(filename, client_socket, username, uploader)
                    self.send_message(client_socket, f"[DOWNLOAD]|[{port}]|[{filename}]")
                elif command == "[LIST_FILES]":
                    try:
                        # Generate the list of files from the directory
                        file_list = []
                        for file in os.listdir(self.storage_dir):
                            if "_" in file:  # Ensure the file format includes an underscore
                                uploader, actual_filename = file.split("_", 1)
                                file_list.append(f"{actual_filename} (Uploaded by {uploader})")

                        # Send the file list to the client
                        if file_list:
                            self.send_message(client_socket, f"[LIST_FILES]\n" + "\n".join(file_list))
                        else:
                            self.send_message(client_socket, "[LIST_FILES]\nNo files available.")
                    except Exception as e:
                        self.log_message(f"[ERROR] Failed to list files: {e}")
                        self.send_message(client_socket, "[ERROR] Could not list files.")

                elif command.startswith("[DELETE]"):
                    try:
                        # Extract the filename from the command
                        _, filename = command.split("|")
                        filename = filename.strip("[]")

                        found_file = None
                        permission_denied = False
                        with read_lock:
                            # Search for the file in the directory
                            for file in os.listdir(self.storage_dir):
                                if file.endswith(f"_{filename}"):  # Match the file by its suffix
                                    uploader, actual_filename = file.split("_", 1)
                                    if actual_filename == filename:
                                        if uploader == username:  # User has permission to delete
                                            found_file = file
                                            permission_denied = False
                                            break  # Correct file found
                                        else:
                                            permission_denied = True

                            # Handle the delete operation based on the search results
                            if found_file:  # Correct file found, proceed with deletion
                                filepath = os.path.join(self.storage_dir, found_file)
                                with write_lock:
                                    os.remove(filepath)
                                self.send_message(client_socket, f"[DELETE] File '{filename}' deleted successfully.")
                                self.log_message(f"[DELETE SUCCESS] {filename} deleted by {username}.")
                            elif permission_denied:  # File exists but belongs to another user
                                self.send_message(client_socket, "[ERROR] You do not have permission to delete this file.")
                                self.log_message(f"[DELETE ERROR] {username} attempted to delete {filename}, owned by another user.")
                            else:  # File not found
                                self.send_message(client_socket, "[ERROR] File not found.")
                    except Exception as e:
                        self.log_message(f"[ERROR] Failed to delete file: {e}")
                        self.send_message(client_socket, "[ERROR] Could not delete file.")
                elif command == "[DISCONNECT]":
                    self.log_message(f"[DISCONNECTED] {username} disconnected.")
                    break

        except Exception as e:
            self.log_message(f"[ERROR] {e}")
        finally:
            with lock:
                if username in clients:
                    del clients[username]
            client_socket.close()
    def start_data_socket(self, filename, client_socket, username, uploader):
        """Create a stateless data socket for uploading or downloading files."""
        global data_port_base
        port = data_port_base
        data_port_base += 1  # Increment port for next connection

        threading.Thread(
            target=self.handle_data_connection,
            args=(port, filename, client_socket, username, uploader),
            daemon=True
        ).start()
        return port
    
    def start_data_socket_upload(self, filename, filesize, user, client_socket):
        """Create a stateless data socket for uploading or downloading files."""
        global data_port_base
        port = data_port_base
        data_port_base += 1  # Increment port for next connection

        threading.Thread(
            target=self.handle_data_connection_upload,
            args=(port, filename, filesize, user, client_socket),
            daemon=True
        ).start()
        return port
    
    def handle_data_connection_upload(self, port, filename, filesize, user, client_socket):
        """Handle a temporary stateless connection for uploading or downloading files."""
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_socket.bind((HOST, port))
        data_socket.listen(1)

        self.log_message(f"[DATA SOCKET] Listening on port {port} for upload of {filename}.")
        conn, addr = data_socket.accept()

        try:
            self.handle_upload(conn, client_socket, user, filename, filesize)
        finally:
            conn.close()
            data_socket.close()

    def handle_data_connection(self, port, filename, client_socket, username, uploader):
        """Handle a temporary stateless connection for uploading or downloading files."""
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_socket.bind((HOST, port))
        data_socket.listen(1)

        self.log_message(f"[DATA SOCKET] Listening on port {port} for download of {filename}.")
        conn, addr = data_socket.accept()
        self.log_message(f"[DATA SOCKET] Connection established with {addr}.")

        try:
            self.handle_download(conn, client_socket, filename, username, uploader)
        finally:
            conn.close()
            data_socket.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = ServerGUI(root)
    root.mainloop()
