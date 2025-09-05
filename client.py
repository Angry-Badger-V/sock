# Client
import base64
import msvcrt
import os
import socket
import sys
import threading

# Delimiter marks end of messages
delimiter = '<END>'
# Encoding Standard
es = 'UTF-8'
# Prompt for asking for user requests
prompt = 'REQUEST: '
# Stores incompleted request for terminal formatting
requests = ['']
username_ = []

def encoder(data):
    '''
    Encodes a message into base 64 with a delimiter
    Parameters:
    - data: smessage to encode
    '''
    data = base64.b64encode(data.encode(es))
    return data + delimiter.encode(es)

def handle_file(prefix, data):
    '''
    Handles the downloading of a file
    Ensures that the file is saved to a user-specific directory without overwritting files of the same name
    Parameters:
    - prefix: will always be 'DOWNLOAD'
    - data: contains file metadata (name, size) and the file contents
    '''
    filename, filesize, contents = data.split(':', 2)
    fileprefix, filesuffix = filename.split('.')
    contents = base64.b64decode(contents)
    ticker = 1
    # Creates directory based off of username if it doesn't already exist
    if not os.path.exists(f'{username_[0]}Files'):
        os.makedirs(f'{username_[0]}Files')
    while True:
        # Formats file name, prevents files from being overwritten
        if os.path.exists(f'{username_[0]}Files/{filename}'):
            filename = f'{fileprefix}({str(ticker)}).{filesuffix}'
            ticker += 1
        else:
            # Writes to the file
            with open(f'{username_[0]}Files/{filename}', 'xb') as file:
                file.write(contents)
            break
    # Writes about download to the terminal
    sys.stdout.write('\033[F\033[K')
    print(f'{prefix}: {fileprefix}.{filesuffix} {filesize}')
    sys.stdout.write(f'{prompt}{requests[0]}\n')
    sys.stdout.flush()

def handle_data(data):
    '''
    Handles data sent by the server, if it is a file download calls the correct function
    If it is an exit request, informs the user and returns True - sets of exit sequence
    Otherwise just writes to the terminal
    Parameters:
    - data: the data received from the server
    '''
    prefix, data = data.split(':', 1)
    if prefix == 'DOWNLOAD':
        handle_file(prefix, data)
    elif prefix == 'EXIT':
        sys.stdout.write('\033[F\033[K')
        data = base64.b64decode(data).decode(es)
        print(prefix + ': ' + data)
        return True
    else:
        # Moves terminal cursor up a line and clears it
        sys.stdout.write('\033[F\033[K')
        # Decode data
        data = base64.b64decode(data).decode(es)
        # Writes message to terminal
        print(prefix + ': ' + data)
        # Rewrites the current user prompt and input
        sys.stdout.write(f'{prompt}{requests[0]}\n')
        sys.stdout.flush()
    return False
        
def receiver(sock):
    '''
    Listens for incoming messages from the server
    Accumulates partial messages in buffer for next read
    Parameters:
    - sock: the socket connected to the server
    '''
    try:
        data = ''
        while True:
            buffer = ''
            while True:
                data += sock.recv(1024).decode(es)
                if delimiter in data:
                    data, buffer = data.split(delimiter, 1)
                    break
            exit = handle_data(data)
            data = buffer
            if exit:
                break
    except ConnectionResetError:
        # In case of server crash
        print('SERVER: server has crashed')
        sock.close()
        sys.exit(1)

def handle_request(sock, request):
    '''
    Encodes and sends messages to the server
    Parameters:
    - sock: the socket connected to the server
    - request: the user request to be sent
    '''
    msg = encoder(request)
    sock.send(msg)

def launch_client(username, hostname, port):
    '''
    Establishes connection with the server and facilitates user interaction
    Spawns thread where server is listened to
    Parameters:
    - username: the client's username
    - hostname: server hostname / IP address
    - port: the server port number
    '''
    address = (hostname, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Attempts connection with server
    try:
        sock.connect(address)
    except socket.error:
        print('USAGE: [hostname] and [port] must give a valid address')
        sock.close()
        sys.exit(1)
    
    thread = threading.Thread(target=receiver, args=(sock, ), daemon=True)
    thread.start()

    handle_request(sock, f'USERNAME::{username}')
    username_.append(username)
    print(prompt)

    while True:
        # Done in order to keep client input tidy and at bottom of the terminal
        # Stores currently written request in real time
        requests[0] = ''
        while True:
            # Gets character when keyboard pressed
            char = msvcrt.getwch()
            if not thread.is_alive():
                sock.close()
                sys.exit(0)
                break
            if char == '\r':
                # Enter breaks loop
                sys.stdout.write(f'{prompt}\n')
                sys.stdout.flush()
                break
            elif char == '\b':
                # Backspace, deletes most recent character
                requests[0] = requests[0][:-1]
                # Moves cursor to start of line and overwrites it
                sys.stdout.write('\033[F\033[K')
                sys.stdout.write(f'{prompt}{requests[0]}\n')
                sys.stdout.flush()
            else:
                requests[0] += char
                sys.stdout.write('\033[F\033[K')
                sys.stdout.write(f'{prompt}{requests[0]}\n')
                sys.stdout.flush()
        handle_request(sock, requests[0])

if __name__ == '__main__':
    '''
    Entry point for client script
    Validates command-line arguments
    Launches client with specified username, server hostname and server port
    '''
    if len(sys.argv) != 4:
        print('USAGE: python client.py [username] [hostname] [port]')
        sys.exit(1)
    try:
        username = sys.argv[1]
        hostname = sys.argv[2]
        port = int(sys.argv[3])
        launch_client(username, hostname, port)
    except ValueError:
        print('USAGE: [port] must be an integer')
        sys.exit(1)