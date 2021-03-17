import socket
import time
from tkinter import *
import threading
import queue
from tkinter import messagebox
import sys
from signal import signal, SIGINT

HOST = 'localhost'
PORT = 50007
name = ""

send_lock = threading.Lock()

def handler(signal_received, frame):
    print("SIGINT")
    try:
        client.gui.windowObj.exit()
    except:
        pass
    client_sock.close()
    exit(0)


class windowObj:
    def __init__(self, window, controller):
        self.controller = controller
        self.window = window
        self.window.title("Chat:"+name)
        self.window.geometry('1000x600')

        def exit(quitGui=True):
            try:
                client_sock.sendall(bytes("0 ", 'utf-8')) 
            except:
                pass
            self.controller.endApplication()
            if quitGui:
                self.window.destroy()


        self.exitButton = Button(self.window, text="Exit", padx=70, pady=20, command=exit)
        self.exitButton.grid(column=1, row=2)

        self.exit = exit

        self.entry = Text(self.window, width=70, height=10)
        self.entry.grid(column=0, row=1)

        self.listBox = Listbox(self.window, selectmode=SINGLE)
        self.listBox.grid(column=1, row=0, ipadx=30, ipady=153, rowspan=2)
        self.listBox.insert(1, "ALL")
        self.listBox.activate(0)

        self.textBox = Text(self.window, width=70, height=15, state=DISABLED)
        self.textBox.grid(column=0, row=0)

        def sendMsg(event=None):
            text = self.entry.get("1.0", "end")
            if len(text) == 0 or text == "" or text == '\n':
                messagebox.showerror("Error", "Message must be non empty ://")
                self.entry.delete("1.0", "end")
                return 'break'
            if not self.listBox.curselection():
                messagebox.showerror("Error", "To whom?")
                return 'break'
            msg = self.listBox.get(self.listBox.curselection())+"\n"+text
            size = len(msg)
          #  print(size)  print(msg)
            try:
                with send_lock:
                    client_sock.sendall(bytes(str(size)+" ", 'utf-8'))
                    client_sock.sendall(bytes(msg, 'utf-8'))
                    self.entry.delete("1.0", "end")
            except:
                messagebox.showerror("Error", "Connection lost")
                self.msgButton.config(state="disabled")
                self.entry.unbind('<Return>')
            return 'break'

        self.sendMsg = sendMsg

        self.msgButton = Button(self.window, text="Send Message", padx=250, pady=20, command=sendMsg)
        self.msgButton.grid(column=0, row=2)

        self.entry.bind('<Return>', sendMsg)


class GuiPart:
    def __init__(self, window, queue,  controller):
        self.controller = controller
        self.queue = queue
        self.windowObj = windowObj(window, controller)

    def handleQueue(self):
        while self.queue.qsize()>1:
            try:
                type = self.queue.get(0)
                msg = self.queue.get(0)
                print("type: "+type+" "+msg)
                if type == '1':    #mates add
                    self.windowObj.listBox.insert(END, msg)
                    print("add "+msg)
                elif type == '2':   #mates remove
                    idx = self.windowObj.listBox.get(0, END).index(msg)
                    self.windowObj.listBox.delete(idx)
                elif type == '0':
                    self.windowObj.textBox.config(state="normal")
                    self.windowObj.textBox.insert(END, msg)
                    self.windowObj.textBox.config(state="disabled")
                    print("msg "+msg)

            except queue.Empty:
                pass


class ThreadedClient:
    def __init__(self, master):
        self.master = master
        self.queue = queue.Queue()

        self.running = 1
        self.recvThread = threading.Thread(target=self.receive)
        self.recvThread.daemon = True
        self.recvThread.start()

        self.connThread = threading.Thread(target=self.connectionCheck)
        self.connThread.daemon = True
        self.connThread.start()

        self.error = ""

        self.gui = GuiPart(master, self.queue, self)

        self.callHandleQueue()

    def callHandleQueue(self):
        if self.error == "error":
            self.gui.windowObj.msgButton.config(state="disabled")
            self.gui.windowObj.entry.unbind('<Return>')
            messagebox.showerror("Error", "Connection lost")
            self.error = ""
        self.gui.handleQueue()
        if not self.running:
            client_sock.close()
            sys.exit(0)
        self.master.after(200, self.callHandleQueue)

    def connectionCheck(self):
        while True:
            with send_lock:
                try:
                    client_sock.sendall(bytes("c", 'utf-8'))
                except:
                    self.gui.windowObj.exit() 
            time.sleep(1)

    def receive(self):
        client_sock.settimeout(4.0) 
        while self.running:
            try:
                type = client_sock.recv(1).decode()
            except socket.timeout:
                self.error = "error"
                return

            if type == "3": 
                continue

            self.queue.put(type)

            size=""
            temp=""
            while not temp == " ":
                size += temp
                temp = client_sock.recv(1)
                temp = temp.decode()

            size = int(size)

            data = client_sock.recv(size)
            msg = data.decode()
            self.queue.put(msg)
            print(msg)
            print(self.queue.qsize())


    def endApplication(self):
        self.running = 0


#login:
########################################################
loginWindow = Tk()
loginWindow.title("Login")
loginWindow.geometry('230x90')
enterName = Label(loginWindow, text="Enter nickname").grid(row=0)

login = Entry(loginWindow)
login.grid(row=1)
login.focus_set()

def ok(event=None):
    if login.get() == "":
        login.select_clear()
        messagebox.showerror("Error", "Nickaname must be non empty")
        return
    if login.get() == 'ALL':
        login.select_clear()
        messagebox.showerror("Error", "Nickaname can't spell \"ALL\"")
        return
    if login.get().__contains__("\n"):
        login.select_clear()
        messagebox.showerror("Error", "Nickaname cannot contain \"\\n\"")
        return
    if len(login.get())>1000:
        login.select_clear()
        messagebox.showerror("Error", "Nickaname too long")
        return
    global name
    name = login.get()
    loginWindow.destroy()

okButton = Button(loginWindow, text="OK", command=ok).grid(row=2)

loginWindow.bind('<Return>', ok)

loginWindow.mainloop()
#########################################################

if name == "":
    sys.exit(0)



with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_sock:
    try:
        client_sock.connect((HOST, PORT))
        client_sock.sendall(bytes(name, 'utf-8'))
        size = ""
        temp = ""
        while not temp == " ":
            size += temp
            temp = client_sock.recv(1)
            temp = temp.decode()

        size = int(size)
        name = client_sock.recv(size).decode()
        print(name)
    except:
        print("could not connect")
        sys.exit(1)

    signal(SIGINT, handler)

    root = Tk()
    client = ThreadedClient(root)
    root.mainloop()


    try:
        client.gui.windowObj.exit()
    except:
        pass

