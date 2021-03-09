import socket
import threading
import traceback

close = False
clients = list()
clients_lock = threading.Lock()

HOST = 'localhost'
PORT = 50007

addClient = "a"
removeClient = "rm"
message = "m"
nameTaken = "nt"
nameAvailable = "na"
connectionGone = "cg"
nameSet = "n"
connectionUpholder = "co"


def encode(command, msg=""):
    return bytes(command + " " + str(len(msg)) + " " + msg, 'utf-8')


def decode(b):
    if len(b) == 0:
        return None
    try:
        temp = str(b, 'utf-8')
        tab = temp.split()
        t0 = len(tab[0])
        t1 = len(tab[1])
        it1 = int(tab[1])
    except:
        return None
    if len(temp) < t0+t1+2+it1:
        return None
    return tab[0], temp[t0+t1+2:t0+t1+2+it1:], len(bytes(temp[:t0+t1+2+it1:], 'utf-8'))


def sendMessage(fro, to, command, msg):
    with clients_lock:
        for i in clients:
            if to == "ALL" or i[2] == fro or i[2] == to:
                i[0].sendall(encode(command, fro + " " + to + " " + msg))


def addOrRemClients(addOrRem, sock, name):
    if addOrRem == addClient:
        with clients_lock:
            for i in clients:
                if i[0] != sock:
                    i[0].sendall(encode(addClient, name))
                    sock.sendall(encode(addClient, i[2]))
    else:
        with clients_lock:
            if name != "":
                for i in clients:
                    if i[0] != sock:
                        i[0].sendall(encode(removeClient, name))
                for i in clients:
                    if i[0] == sock:
                        clients.remove(i)


def manageName(name, sock, addr):
    try:
        with clients_lock:
            for i in clients:
                if i[2] == name:
                    sock.sendall(encode(nameTaken, ""))
                    return False
        sock.sendall(encode(nameAvailable, ""))
        with clients_lock:
            clients.append((sock, addr, name))
        addOrRemClients(addClient, sock, name)
        return True
    except ConnectionError and socket.timeout:
        return None


def manageClient(sock, addr):
    sock.settimeout(3)
    name = ""
    try:
        b = bytes()
        while True:
            data = sock.recv(1024)
            if data == bytes():
                addOrRemClients(removeClient, sock, name)
                return
            b = b''.join([b, data])
            while (trio := decode(b)) is not None:
                if trio[0] == message:
                    receiver = trio[1].split()[0]
                    sendMessage(name, receiver, message, trio[1][len(receiver) + 1::])
                elif trio[0] == nameSet:
                    if (temp := manageName(trio[1], sock, addr)) is None:
                        return
                    elif temp:
                        name = trio[1]
                elif trio[0] == connectionUpholder:
                    sock.sendall(encode(connectionUpholder))
                b = b[trio[2]::]
    except ConnectionError and socket.timeout and socket.error:
        addOrRemClients(removeClient, sock, name)


def runServer(host, port):
    global close
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind((host, port))
            server_sock.listen(1)
            while True:
                client_sock, client_addr = server_sock.accept()
                threading.Thread(target=manageClient, args=(client_sock, client_addr), daemon=True).start()
    except:
        traceback.print_exc()
        close = True


runServer(HOST, PORT)
