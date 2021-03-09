import threading
import time
from tkinter import *
import socket
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText

import queue

sendingLock = threading.Lock()

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


class MyGui(Frame):
    def __init__(self, q, sock, master=None):
        super().__init__(master)
        self.master = master
        self.q = q
        self.sock = sock
        self.master.minsize(1000, 700)
        self.master.title("Chat")
        self.pack(fill="both")

        self.rightFrame = Frame(self)
        self.listbox = Listbox(master=self.rightFrame)
        self.exitButton = Button(master=self.rightFrame, text="Exit", command=self.master.destroy)
        self.createRightFrame()

        self.leftFrame = Frame(self)
        self.messages = ScrolledText(self.leftFrame, height=28, width=80)
        self.myMessage = Text(self.leftFrame, height=12, width=80)
        self.sendButton = Button(master=self.leftFrame, text="Send", command=self.sendMessage)
        self.createLeftFrame()

    def createRightFrame(self):
        self.listbox.pack(side="top", ipadx=100, ipady=200)
        self.listbox.insert(END, "ALL")
        self.exitButton.pack(side="bottom")
        self.rightFrame.pack(side="right", padx=10, pady=10)

    def createLeftFrame(self):
        self.messages.config(state="disabled")
        self.messages.pack(side="top")
        self.myMessage.pack(side="top")
        self.myMessage.bind("<Return>", lambda event: self.sendMessage())
        self.sendButton.pack(side="top")
        self.leftFrame.pack(padx=10, pady=10)

    def sendMessage(self):
        if self.listbox.get(ANCHOR) == "":
            messagebox.showerror("No recipient selected", "Please select a person from the list")
            return 'break'
        if self.myMessage.get(0.0, END) == "\n":
            messagebox.showerror("Empty message", "Cannot send empty message")
            return 'break'
        with sendingLock:
            self.sock.sendall(encode(message, self.listbox.get(ACTIVE) + " " + self.myMessage.get(0.0, END)))
        self.myMessage.delete(0.0, END)
        return 'break'

    def checkQueue(self):
        while not self.q.empty():
            top = self.q.get()
            if top[0] == message:
                sender = top[1].split()[0]
                receiver = top[1].split()[1]
                msg = top[1][len(sender) + len(receiver) + 2::]
                b = False
                if self.messages.yview()[1] == 1.0:
                    b = True
                self.messages.config(state="normal")
                self.messages.insert(END, sender + " => " + receiver + "\n")
                self.messages.insert(END, msg)
                self.messages.config(state="disabled")
                if b:
                    self.messages.yview_moveto(1.0)
            elif top[0] == addClient:
                self.listbox.insert(END, top[1])
            elif top[0] == removeClient:
                self.listbox.delete(self.listbox.get(0, END).index(top[1]))
            elif top[0] == connectionGone:
                self.messages.config(state="normal")
                self.messages.insert(END, "Lost connection to the server\n")
                self.messages.config(state="disabled")
                self.sendButton.config(state="disabled")
                self.myMessage.unbind("<Return>")
                messagebox.showerror("Connection lost", "Connection to the server has been lost")


class Client:
    def __init__(self, master, sock):
        self.q = queue.Queue()
        self.gui = MyGui(self.q, sock, master)
        self.master = master
        threading.Thread(target=self.backgroundThread, args=(sock,), daemon=True).start()
        self.check()

    def backgroundThread(self, sock):
        b = bytes()
        try:
            while True:
                data = sock.recv(1024)
                if data == bytes():
                    self.q.put((connectionGone, ""))
                    return
                b = b''.join([b, data])
                while (trio := decode(b)) is not None:
                    if trio[0] != connectionUpholder:
                        self.q.put((trio[0], trio[1]))
                    b = b[trio[2]::]
        except ConnectionError and socket.timeout and socket.error:
            self.q.put((connectionGone, ""))

    def check(self):
        self.gui.checkQueue()
        self.master.after(200, self.check)


class LoginPopUp:
    def __init__(self, master, sock):
        master.title('Log in')
        threading.Thread(target=self.upholderThread, args=(sock,), daemon=True).start()
        sock.settimeout(5)
        self.frame = Frame(master)
        self.frame.pack(fill="both", pady=50)
        self.master = master
        self.sock = sock
        self.master.maxsize(300, 150)
        self.master.minsize(300, 150)
        self.text = Text(self.frame, height=1, width=20, font=10)
        self.text.pack()
        self.text.focus_set()
        self.text.bind("<Return>", lambda event: self.buttonClick())
        self.button = Button(self.frame, text="Log In", command=self.buttonClick)
        self.button.pack()

    @staticmethod
    def upholderThread(sock):
        try:
            while True:
                time.sleep(2)
                with sendingLock:
                    sock.sendall(encode(connectionUpholder))
        except ConnectionError and socket.timeout and socket.error:
            return

    def buttonClick(self):
        name = self.text.get(0.0, END)
        name = name[:-1:]
        if name == "ALL":
            messagebox.showerror("Incorrect name", "Your name can't be \"ALL\"")
            return 'break'
        if name == "":
            messagebox.showerror("Incorrect name", "Your name can't be empty")
            return 'break'
        if name.__contains__(" ") or name.__contains__("\n"):
            messagebox.showerror("Incorrect name", "Your name can't contain spaces")
            return 'break'
        try:
            with sendingLock:
                self.sock.sendall(encode(nameSet, name))
            while data := self.sock.recv(1024):
                com = decode(data)[0]
                if com == nameTaken:
                    messagebox.showerror("Name taken", "This name is already taken")
                    return 'break'
                elif com == connectionUpholder:
                    continue
                else:
                    self.master.destroy()
                    newRoot = Tk()
                    client = Client(newRoot, self.sock)
                    newRoot.mainloop()
                    return 'break'
        except ConnectionError and socket.timeout and socket.error:
            messagebox.showerror("Server down", "Connection to the server has benn lost")
            self.button.config(state="disabled")
            self.text.unbind("<Return>")
            self.text.config(state="disabled")
            return 'break'


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_sock:
    try:
        client_sock.connect((HOST, PORT))
        root = Tk()
        login = LoginPopUp(root, client_sock)
        root.mainloop()
    except ConnectionError:
        print("Server down")
