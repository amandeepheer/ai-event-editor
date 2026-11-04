"""Setup/status and optional local AI downloads, without terminal commands."""
from pathlib import Path
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk,messagebox
from .installed_runtime import install_media_tools,data_directory
from .service import configure_plugin


def main():
    root=tk.Tk();root.title('AI Event Editor — Setup & AI Add-on');root.geometry('760x700')
    frame=ttk.Frame(root,padding=20);frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='AI Event Editor setup',font=('',18,'bold')).pack(anchor='w')
    ttk.Label(frame,text='No system Python or terminal commands are needed. Install basic tools first; AI downloads are optional.',wraplength=710).pack(anchor='w',pady=10)
    status=tk.StringVar(value='Basic media tools: about 81 MB if needed. CLIP AI: hundreds of MB on CPU or several GB on NVIDIA. Optional Ollama installer: about 1.7 GB; Qwen model: about 5.2 GB. Downloads use internet/disk space, not a subscription.')
    ttk.Label(frame,textvariable=status,wraplength=710).pack(anchor='w',pady=10)
    events=queue.Queue();busy=False;tasks=[]
    def job(function):
        nonlocal busy
        if busy:return
        busy=True
        selector.configure(state='disabled')
        for button in tasks:button.configure(state='disabled')
        def work():
            try:events.put(('done',function(lambda text:events.put(('progress',text)))))
            except Exception as error:events.put(('error',str(error)))
        threading.Thread(target=work,daemon=True).start()
    def button(label,function):
        widget=ttk.Button(frame,text=label,command=lambda:job(function));widget.pack(anchor='w',pady=4);tasks.append(widget)
    def basic(progress):
        install_media_tools(progress=progress);path=configure_plugin()
        return 'Basic setup ready. Install the Adobe panel, then select the private connection file:\n'+str(path)
    button('1 · Finish basic setup',basic)
    app=Path(sys.executable).parent
    def open_panel():
        package=app/'AIEventEditor-Premiere.ccx'
        try:os.startfile(str(package))
        except OSError as error:messagebox.showerror('Adobe installation',str(error)+'\nOpen the .ccx with Creative Cloud Desktop.')
    ttk.Button(frame,text='2 · Install Premiere panel',command=open_panel).pack(anchor='w',pady=4)
    ttk.Button(frame,text='3 · Open connection-file folder',command=lambda:os.startfile(str(data_directory()))).pack(anchor='w',pady=4)
    ttk.Separator(frame).pack(fill='x',pady=12)
    ttk.Label(frame,text='Optional AI footage suggestions',font=('',12,'bold')).pack(anchor='w')
    ttk.Label(frame,text='Choose a device, then install packages and CLIP. Keep several GB free. NVIDIA mode needs a compatible driver; CPU mode is slower. Reconnect the panel after setup.',wraplength=710).pack(anchor='w',pady=6)
    mode=tk.StringVar(value='NVIDIA GPU (RTX 50-series)')
    selector=ttk.Combobox(frame,textvariable=mode,values=['NVIDIA GPU (RTX 50-series)','CPU (smaller download)'],state='readonly',width=35);selector.pack(anchor='w')
    # Capture mode on UI thread; worker must not read Tk variables.
    clip_button=ttk.Button(frame,text='Install / repair CLIP AI',command=lambda:install_clip_job())
    clip_button.pack(anchor='w',pady=4);tasks.append(clip_button)
    def install_clip_job():
        selected='cuda' if mode.get().startswith('NVIDIA') else 'cpu'
        def action(progress):
            from .ai_runtime import install_clip
            result=install_clip(selected,progress)
            return 'CLIP inference verified on '+result['device']+'. Reconnect Premiere to enable AI suggestions.'
        job(action)
    ttk.Separator(frame).pack(fill='x',pady=12)
    ttk.Label(frame,text='Optional local language understanding',font=('',12,'bold')).pack(anchor='w')
    def ollama(progress):
        from .local_language import install_ollama
        install_ollama(progress);return 'Ollama installer finished. Use Download language model next.'
    def model(progress):
        from .local_language import pull_model
        pull_model(progress);return 'Qwen ready locally. Enable local Ollama/Qwen in the Premiere panel and review its proposed changes.'
    button('Install Ollama (vendor installer)',ollama)
    button('Download Qwen3 8B language model',model)
    ttk.Label(frame,text='AI proposes categories and settings; it is not guaranteed to identify the best moment. Slow motion, effects, titles and speech editing remain unfinished.',wraplength=710).pack(anchor='w',pady=10)
    ttk.Button(frame,text='Open installation guide',command=lambda:os.startfile(str(app/'INSTALL_README.txt'))).pack(anchor='w',pady=4)
    def poll():
        nonlocal busy
        try:
            while True:
                kind,value=events.get_nowait()
                status.set(value)
                if kind!='progress':
                    busy=False
                    selector.configure(state='readonly')
                    for widget in tasks:widget.configure(state='normal')
                    if kind=='error':messagebox.showerror('Setup failed',value)
        except queue.Empty:pass
        root.after(100,poll)
    def close():
        if busy:messagebox.showinfo('Setup running','Wait for the current download/setup operation before closing.');return
        root.destroy()
    root.protocol('WM_DELETE_WINDOW',close);root.after(100,poll);root.mainloop()
