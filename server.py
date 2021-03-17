import socket
import sys
import threading
import traceback
from signal import signal, SIGINT


HOST = 'localhost'
PORT = 50007
clients = dict()
messages = list()
clients_lock = threading.Lock()
messages_lock = threading.Lock()

def handler(signal_received, frame):
    print("SIGINT")
    for client in clients:
        try:
            clients[client][0].close()
        except:
            pass
    try:
        server_sock.close()
    except:
        pass

    exit(0)

def addClient(name, client_sock):
    for client in clients:
        try:
            clients[client][0].sendall(bytes('1', 'utf-8'))
            clients[client][0].sendall(bytes(str(len(name))+" ", 'utf-8'))
            clients[client][0].sendall(bytes(name, 'utf-8'))

            client_sock.sendall(bytes('1', 'utf-8'))
            client_sock.sendall(bytes(str(len(client))+" ", 'utf-8'))
            client_sock.sendall(bytes(client, 'utf-8'))
        except:
            print("cannot send m8s add")


def removeClient(name):
    for client in clients:
        if not client == name:
            try:
                clients[client][0].sendall(bytes("2", 'utf-8'))
                clients[client][0].sendall(bytes(str(len(name))+" ", 'utf-8'))
                clients[client][0].sendall(bytes(name, 'utf-8'))
            except:
                print("cannot send m8s remove")


def quickRemove(name):
    with clients_lock:
        clients[name][0].close()
        removeClient(name)
        clients.pop(name)


def readClient(name):
    clients[name][0].settimeout(3.0)
    while True:
        try:
            size = ""
            temp = ""
            while not temp == " ":
                size += temp
                try:
                    temp = clients[name][0].recv(1)
                except socket.timeout:
                    print("client didnt reply, remove "+name)
                    quickRemove(name)
                    return
                temp = temp.decode()
                if temp == "": 
                    print("remove interrupted "+name)
                    quickRemove(name)
                    return
                if temp == "c": #connection check
                    temp = ""
                    clients[name][0].sendall(bytes("3", 'utf-8'))

            size = int(size)
            if size == 0:  
                break
            data = clients[name][0].recv(size)
        except:     #nagle odlaczenie przez blad
            print("nagle odlaczenie "+name)
            break
        if not data:
            break
        msg = data.decode()
        with messages_lock:
            messages.append((name, msg))
        print(msg)
    #cleanup
    print("remove "+name)
    quickRemove(name)

#0 = msg, 1 = add user, 2 =remove user


def sendMsg(receiver, msg):
    try:
        clients[receiver][0].sendall(bytes("0", 'utf-8'))
        clients[receiver][0].sendall(bytes(str(len(msg))+" ", 'utf-8'))
        clients[receiver][0].sendall(bytes(msg, 'utf-8'))
    except:
        print("cannot send in msgHandler")



def msgHandler(sender, msg):
    parts = msg.splitlines()
    receiver = parts[0]
    str = sender + " => " + receiver + ":" + msg[len(receiver):]
    print(str)

    if parts[0] == 'ALL':
        for client in clients:
            sendMsg(client, str)
    else:
        sendMsg(receiver, str)
        sendMsg(sender, str)


def Timer():
    while True:
        if not messages:
            continue
        with messages_lock:
            with clients_lock:
                for sender, msg in messages:
                    msgHandler(sender, msg) 
                                            
            messages.clear()


timer = threading.Thread(target=Timer)
timer.daemon = True
timer.start()

signal(SIGINT, handler)

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen(1)

        while True:
            client_sock, client_addr = server_sock.accept()
            name = client_sock.recv(1024)
            name = name.decode()

            with clients_lock:
                while name in clients:
                    name += '1'
                client_sock.sendall(bytes(str(len(name))+" ", 'utf-8'))   
                client_sock.sendall(bytes(name, 'utf-8'))

                addClient(name, client_sock)   
                
                clients.update({name: [client_sock, client_addr]})

                client = threading.Thread(target=readClient, args=(name,))
                client.deamon = True
                client.start()

                welcomeStr = "accepted\n"
                client_sock.sendall(bytes("0", 'utf-8'))
                client_sock.sendall(bytes(str(len(welcomeStr))+" ", 'utf-8'))
                client_sock.sendall(bytes(welcomeStr, 'utf-8'))
                print("accepted "+str(client_addr)+str(client_sock)+name)


except:
    traceback.print_exc()
    close = True
