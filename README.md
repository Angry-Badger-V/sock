# Python Client-Server Chat Application

## Requirements

- **Python Version:** 3.13.0
- **Libraries:**
  - `base64`
  - `msvcrt`
  - `os`
  - `select`
  - `socket`
  - `sys`

---

## Usage

### Starting the Server

1. Clone the repository onto your local machine.
2. Run the server script:

   ```bash
   python server.py [port]
   ```

   Replace `[port]` with the port number on which the server should listen.

3. The server will now be awaiting connections.

### Starting the Client

1. Clone the repository onto your local machine.
2. Run the client script:

   ```bash
   python client.py [username] [hostname] [port]
   ```

   - Replace `[username]` with the desired client username.
   - Replace `[hostname]` with the server's hostname or IP address.
   - Replace `[port]` with the server's listening port.

3. The client will attempt to connect with the server.

---

## Server Functionality

- Prints a message when a new client connects, showing their IP address and port.
- Sends a welcome message to new clients.
- Informs all existing clients when a new client joins.
- Supports multiple simultaneous client connections.
- Clients can leave using the `EXIT::` command.
- Handles unexpected client disconnections gracefully.
- Continues running after client disconnects.

---

## Client Functionality

- Can send multiple messages.
- Supports unicast and broadcast messaging.
- Can access shared files:
  - Displays the number of files and their sizes when accessing a folder.
- Can download files:
  - Displays file size before downloading.
  - Saves files to a folder named `<username>Files`.
- Can leave the server via command or unexpected disconnection without crashing.
- Receives notifications if the server crashes.
- Informed when other clients join or leave.

---

## Commands

### 1. Unicast

Send a private message to a specific user:

```text
UNICAST::<username>:<message>
```

**Example:**

```text
UNICAST::William:hello, world!
```

---

### 2. Broadcast

Send a message to all connected clients:

```text
BROADCAST::<message>
```

**Example:**

```text
BROADCAST::hi all
```

---

### 3. Access Shared Files

View contents of the `SharedFiles` folder or subfolders:

```text
ACCESS::<directory>
```

**Examples:**

- View `SharedFiles` folder:

  ```text
  ACCESS::
  ```

- View subfolder `DeepFiles`:

  ```text
  ACCESS::DeepFiles
  ```

- Nested subfolders:

  ```text
  ACCESS::<sub-directory-1>/<sub-directory-2>
  ```

---

### 4. Download Files

Download a file from the server:

```text
DOWNLOAD::<filename>
```

**Example:**

```text
DOWNLOAD::video1.mp4
```

> Note: File types must be specified. Downloaded files are saved in `<username>Files`.

---

### 5. Exit Server

Disconnect from the server:

```text
EXIT::
```

---

## Client-Server Communication

- **Message Format:**
  - Messages encoded in `base64`.
  - Each message ends with a delimiter `<END>` (encoded as bytes).
  - Server messages include a prefix identifying the sender or message type.

---

## Server Architecture

- **Encoding:** UTF-8 with base64 for user messages/files.
- **Delimiter:** `<END>` marks the end of a client message.
- **Client Management:** Maintains a dictionary mapping usernames to socket connections.
- **Protocols:**
  - Unicast: send message to a specific client.
  - Broadcast: send message to all clients.
  - Access: view shared files.
  - Download: retrieve shared files.
  - Exit: disconnect client.

---

## Environment Variables

- `SERVER_SHARED_FILES`  
  - Directory for shared files.  
  - Default: `./SharedFiles`

---

## Error Handling

- Sends detailed `USAGE` messages for invalid requests.
- Handles both expected and unexpected disconnections.
- Informs other clients when someone disconnects.
- Validates usernames to prevent conflicts.
- Notifies clients if the server crashes.
- Notifies clients attempting to join a non-existing server.

---

