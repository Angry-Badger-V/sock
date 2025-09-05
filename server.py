# Server
import base64
import os
import select
import socket
import sys

# Stores partial data from incomplete reads
buffers = {}
# Stores client usernames and connections
clients = {}
# Delimiter marks end of messages
delimiter = '<END>'
# Encoding Standard
es = 'UTF-8'
hostname = '0.0.0.0'
# Seperator used in parsing client requests
seperator = '::'
# shared folder environment variable
sharedfolder = os.getenv('SERVER_SHARED_FILES', './SharedFiles')

def encoder(prefix, content):
    '''
    Encodes a message into base 64 and gives it a prefix and a delimiter
    Parameters:
    - prefix: usually the name of the sender, but can specify other things
    - content: content of the message
    '''
    prefix += ': '
    content = base64.b64encode(content.encode(es))
    return prefix.encode(es) + content + delimiter.encode(es)

def handle_failed_request(conn, reason):
    '''
    Sends failure message with explanation to the client
    Parameters:
    - conn: the client connection
    - reason: reason for failure
    '''
    msg = encoder('USAGE', reason)
    conn.send(msg)

def handle_unicast(sender, content):
    '''
    Handles unicast messaging between two users, by sending a message from the sender to a specified client
    Validates the recepient of the message
    Parameters:
    - sender: username of the sender
    - content: contains the username of the recipient, and the message itself
    '''
    try:
        client, content = content.split(':', 1)
        if client == sender:
            handle_failed_request(clients[sender], '[recipient] cannot be you')
        elif client in clients:
            conn = clients[client]
            msg = encoder(sender, content)
            conn.send(msg)
        else:
            handle_failed_request(clients[sender], '[recipient] does not exist')
    except ValueError:
        handle_failed_request(clients[sender], '[request] invalid')

def handle_broadcast(sender, content, exclude=[]):
    '''
    Broadcasts a message from the sender to all other clients
    Parameters:
    - sender: username of the sender
    - content: message to be sent
    - exclude: list of users other than the sender to not send the message
               used in usecase of the server broadcasting
    '''
    msg = encoder(sender, content)
    for client in clients:
        if (client != sender) and (client not in exclude):
            clients[client].send(msg)

def handle_download(conn, directory):
    '''
    Handles file download requests by reading the folder at the directory relative to the shared folder
    Encodes contents of file to base 64
    Includes metadata about the file in the prefix
    Parameters:
    - conn: the client connection
    - directory: the directory of the file to be downloaded
    '''
    path = sharedfolder + '/' + directory
    try:
        if os.path.isfile(path):
            with open(path, 'rb') as file:
                prefix = f'DOWNLOAD:{os.path.basename(path)}:({os.path.getsize(path)} bytes):'
                contents = base64.b64encode(file.read())
                msg = prefix.encode(es) + contents + delimiter.encode(es)
                conn.send(msg)
        else:
            handle_failed_request(conn, f'{directory} is not a file')
    except FileNotFoundError:
        handle_failed_request(conn, f'{directory} does not exist')

def handle_access(conn, directory):
    '''
    Provides list of the content of a directory
    Sends number of files, names and sizes of files, and names of folders
    Parameters:
    - conn: the client connection
    - directory: the directory to be accessed, relative to the shared folder
    '''
    path = sharedfolder + '/' + directory
    result = f'{directory}: '
    ticker = 0
    result2 = ''
    try:
        with os.scandir(path) as entries:
            # Iterate over entries in the directory
            for entry in entries:
                ticker += 1
                # Differentiating between files and folders
                if entry.is_file():
                    filename = entry.name
                    filesize = os.path.getsize(entry.path)
                    result2 += f'\nFILE: {filename} ({filesize} bytes)'
                else:
                    result2 += f'\nFOLDER: {entry.name}'
        msg = encoder('SERVER', result+str(ticker)+' files'+result2)
        conn.send(msg)
    except Exception:
        handle_failed_request(conn, f'failed to access {directory}')

def handle_exit(conn, username):
    '''
    Handles client disconnection requests
    Notifies other clients of the disconnection
    Parameters:
    - conn: the connection of the disconnecting client
    - username: the username of the client exiting
    '''
    msg = encoder('EXIT', 'you have disconnected from the server')
    clients.pop(username)
    buffers.pop(conn)
    handle_broadcast('SERVER', f'{username} has left the server')
    conn.send(msg)
    conn.close()

def handle_username(conn, username):
    '''
    Validates and registers usernames for connecting clients
    Notifies other clients of a new connection
    Parameters:
    - conn: the client connection
    - username: the client username
    '''
    if username in clients:
        print('SERVER: connection failed')
        msg = encoder('SERVER', 'username already in use')
        conn.send(msg)
        conn.close()
    elif (username == 'SERVER') or (username == 'USAGE'):
        print('SERVER: connection failed')
        msg = encoder('SERVER', 'username invalid')
        conn.send(msg)
        conn.close()
    else:
        print(f'SERVER: connection success')
        clients[username] = conn
        msg = encoder('SERVER', 'welcome to the server')
        conn.send(msg)
        handle_broadcast('SERVER', f'{username} has joined the server', [username])

def handle_data(conn, data):
    '''
    Processes data, decodes the request, and calls the appropriate function
    Ensures that the formatting for a request is broadly correct
    Parameters:
    - conn: the client connection
    - data: the data received from the client
    '''
    data = base64.b64decode(data).decode(es)
    if seperator not in data:
        handle_failed_request(conn, 'request invalid')
    else:
        request, content = data.split(seperator, 1)
        match request:
            case 'USERNAME':
                if conn in list(clients.values()):
                    handle_failed_request(conn, 'you already have a username')
                else:
                    handle_username(conn, content)
            case 'UNICAST':
                handle_unicast(list(clients.keys())[list(clients.values()).index(conn)], content)
            case 'BROADCAST':
                handle_broadcast(list(clients.keys())[list(clients.values()).index(conn)], content)
            case 'ACCESS':
                handle_access(conn, content)
            case 'DOWNLOAD':
                handle_download(conn, content)
            case 'EXIT':
                handle_exit(conn, list(clients.keys())[list(clients.values()).index(conn)])
            case _:
                handle_failed_request(conn, 'request invalid')

def receiver(conn):
    '''
    Receives data from clients and converts it into a string
    Handles fragmented data by using buffers
    Parameters:
    - conn: the client connection
    '''
    if conn not in buffers:
        buffers[conn] = ''

    # Uses buffer from last read
    data = buffers[conn]
    while True:
        try:
            data += conn.recv(1024).decode(es)
        except BlockingIOError:
            # No data at moment
            pass
        if delimiter in data:
            # Split data at delimiter
            data, buffer = data.split(delimiter, 1)
            break
    # Process each complete message
    handle_data(conn, data)
    # Remaining partial data is retained in the buffer for future reads
    buffers[conn] = buffer

def launch_server(port):
    '''
    Launches server on specified port and listens for connections
    Uses non-blocking sockets for client handling
    Parameters:
    - port: port number on which server will be connected
    '''
    address = (hostname, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.bind(address)
    sock.listen()

    sock.setblocking(False)

    print(f'SERVER: server started on {hostname}:{port}')
    
    while True:
        # Use select to monitor sockets
        r, w, e = select.select([sock] + list(clients.values()), [], [])
        for s in r:
            if s is sock:
                # Accept new connections on server socket
                conn, addr = sock.accept()
                print(f'SERVER: connection attempt from {addr[0]}:{addr[1]}')
                conn.setblocking(False)
                # Verify username
                receiver(conn)
            else:
                try:
                    try:
                        # Receive client messages on client sockets
                        receiver(s)
                    except BlockingIOError:
                        pass
                except ConnectionResetError:
                    # Unexpected disconnect
                    username = list(clients.keys())[list(clients.values()).index(s)]
                    clients.pop(username)
                    buffers.pop(s)
                    handle_broadcast('SERVER', f'{username} has left the server')
                    s.close()

if __name__ == '__main__':
    '''
    Entry point for server script
    Validates command-line arguments
    Initilises SharedFiles folder if needed
    Launches server with specified port
    '''
    if len(sys.argv) != 2:
        print('USAGE: python server.py [port]')
        sys.exit(1)
    try:
        port = int(sys.argv[1])
        if not os.path.exists(sharedfolder):
            os.makedirs(sharedfolder)
        launch_server(port)
    except ValueError:
        print('USAGE: [port] must be an integer')

        sys.exit(1)
