Cloud File Storage and Publishing System
This project implements a Cloud File Storage and Publishing System as part of the CS408 Computer Networks course. It is a client-server application that uses TCP sockets for communication. The system supports file uploads, downloads, and management through a graphical user interface (GUI).

Features
Server
Accepts connections from multiple clients simultaneously.
Stores uploaded text files in a predefined directory.
Ensures unique filenames for each client by appending client-specific identifiers.
Allows file list retrieval, upload, download, and deletion requests from clients.
Logs all server-side activities, errors, and notifications in the server GUI.
Handles large files and ensures graceful shutdown even if the server is abruptly closed.
Client
Connects to the server with a unique username.
Uploads and downloads files to/from the server.
Requests and displays the list of available files and their respective owners.
Deletes files uploaded by the client.
Notifies the uploader if their file is downloaded (if the uploader is online).
Provides a user-friendly GUI for all operations and logs client-side activities.
Project Structure
GUI_server.py
Implements the server application, including file management, client connections, and a GUI for server-side operations.

GUI_client.py
Implements the client application, including file upload, download, and management features with a user-friendly GUI.

CS408_Project_Fall24.pdf
The project description document detailing the requirements and grading criteria.

Setup and Usage
Prerequisites
Python 3.x
Tkinter (pre-installed with Python)
Basic networking setup (server and client must be on the same network or accessible via public IP)
Instructions
Server
Run GUI_server.py on the server machine:
bash
Copy
Edit
python GUI_server.py
Specify a port number and choose a directory to store uploaded files using the GUI.
Click Start Server to begin listening for client connections.
Client
Run GUI_client.py on the client machine:
bash
Copy
Edit
python GUI_client.py
Enter the server's IP address, port number, and a unique username in the GUI.
Use the buttons to upload, download, list, or delete files on the server.
Key Design Points
Concurrency: The server uses threading to handle multiple client connections simultaneously.
GUI: Both client and server applications include intuitive GUIs built using Tkinter.
Data Integrity: Server ensures file uniqueness and handles large files reliably.
Notifications: The uploader is notified whenever their file is downloaded by another client.
Limitations
Only supports text files with ASCII characters.
Server and client must be on the same network or accessible over the internet.
No encryption; all communication is in plain text.
Contributors
[Your Name]
[Your Partner's Name] (if applicable)
License
This project is for educational purposes under the CS408 Computer Networks course at [Your University Name].
