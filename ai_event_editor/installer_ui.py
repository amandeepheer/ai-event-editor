"""Small setup/status window for the packaged helper, not a standalone video editor."""
from pathlib import Path
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from .installed_runtime import install_media_tools, data_directory
from .service import configure_plugin


def main():
    root=tk.Tk();root.title('AI Event Editor — Setup & Status');root.geometry('700x490')
    frame=ttk.Frame(root,padding=22);frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='Finish setting up AI Event Editor',font=('',18,'bold')).pack(anchor='w')
    ttk.Label(frame,text='The processing engine is included. No Python installation or terminal commands are needed.',wraplength=640).pack(anchor='w',pady=12)
    ttk.Label(frame,text='1. Finish setup: download media tools if needed and prepare automatic startup.\n2. Install the Premiere panel through Adobe Creative Cloud.\n3. In Premiere, choose Set up automatic start and select the connection file.',wraplength=640).pack(anchor='w')
    status=tk.StringVar(value='First setup needs internet for an approximately 81 MB verified media-tools download. GPU AI models and Ollama are not included.')
    ttk.Label(frame,textvariable=status,wraplength=640).pack(anchor='w',pady=18)
    events=queue.Queue();busy=False
    def finish():
        nonlocal busy
        if busy:return
        busy=True;button.configure(state='disabled')
        def work():
            try:
                install_media_tools(progress=lambda text:events.put(('progress',text)))
                path=configure_plugin()
                events.put(('done',str(path)))
            except Exception as error:events.put(('error',str(error)))
        threading.Thread(target=work,daemon=True).start()
    button=ttk.Button(frame,text='1 · Finish setup',command=finish);button.pack(anchor='w',pady=5)
    app=Path(sys.executable).parent
    def open_panel():
        package=app/'AIEventEditor-Premiere.ccx'
        if not package.is_file():messagebox.showerror('Missing panel','The Adobe package is missing. Reinstall AI Event Editor.');return
        try:os.startfile(str(package))
        except OSError as error:messagebox.showerror('Adobe installation',str(error)+'\nOpen the .ccx file with Adobe Creative Cloud Desktop.');
    ttk.Button(frame,text='2 · Install Premiere panel',command=open_panel).pack(anchor='w',pady=5)
    ttk.Button(frame,text='3 · Open connection-file folder',command=lambda:os.startfile(str(data_directory()))).pack(anchor='w',pady=5)
    ttk.Button(frame,text='Open installation guide',command=lambda:os.startfile(str(app/'INSTALL_README.txt'))).pack(anchor='w',pady=5)
    def poll():
        nonlocal busy
        try:
            while True:
                kind,value=events.get_nowait()
                if kind=='progress':status.set(value)
                else:
                    busy=False;button.configure(state='normal')
                    if kind=='done':status.set('Setup ready. Install the Adobe panel, then select this private connection file in the panel:\n'+value)
                    else:status.set('Setup failed: '+value);messagebox.showerror('Setup failed',value)
        except queue.Empty:pass
        root.after(100,poll)
    def close():
        if busy:messagebox.showinfo('Setup running','Wait for setup to finish before closing.');return
        root.destroy()
    root.protocol('WM_DELETE_WINDOW',close);root.after(100,poll);root.mainloop()
