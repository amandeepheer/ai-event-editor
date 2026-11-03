"""Minimal Windows-friendly standalone render interface (Tkinter, stdlib only).

This is a manual edit-plan renderer, not yet an AI-powered visual timeline.
"""
from pathlib import Path
import threading
import json
import queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

def main():
    root = tk.Tk()
    root.title("AI Event Editor — Standalone Preview")
    root.geometry("640x360")
    plan = tk.StringVar()
    music = tk.StringVar()
    output = tk.StringVar(value=str(Path.home() / "Videos" / "ai-event-highlight.mp4"))
    status = tk.StringVar(value="Select an existing edit-plan.json to render.")
    root.columnconfigure(1, weight=1)

    def choose(variable, types):
        selected = filedialog.askopenfilename(filetypes=types)
        if selected:
            variable.set(selected)

    for row, (label, variable, types) in enumerate([
        ("Edit plan", plan, [("JSON files", "*.json")]),
        ("Music (optional)", music, [("Audio files", "*.mp3 *.wav *.m4a"), ("All files", "*.*")]),
    ]):
        ttk.Label(root, text=label).grid(row=row, column=0, padx=12, pady=14, sticky="w")
        ttk.Entry(root, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=8)
        ttk.Button(root, text="Browse", command=lambda v=variable, t=types: choose(v, t)).grid(row=row, column=2, padx=8)
    ttk.Label(root, text="Output MP4").grid(row=2, column=0, padx=12, pady=14, sticky="w")
    ttk.Entry(root, textvariable=output).grid(row=2, column=1, sticky="ew", padx=8)
    ttk.Button(root, text="Save as", command=lambda: output.set(
        filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 video", "*.mp4")]) or output.get()
    )).grid(row=2, column=2, padx=8)

    button = ttk.Button(root, text="Render MP4")
    button.grid(row=3, column=1, pady=20)
    ttk.Label(root, textvariable=status, wraplength=560).grid(row=4, column=0, columnspan=3, padx=12)

    def inspect():
        try:
            from .edit_plan import preflight_plan
            report = preflight_plan(json.loads(Path(plan.get()).read_text(encoding="utf-8")))
            support = "Ready for normal-speed rendering." if report["standalone_supported"] else "Rendering blocked: speed effects are not supported yet."
            status.set(f"{report['clips']} clips · {report['duration_seconds']:g}s · {report['fps']:g} fps. {support}")
        except (ValueError, OSError) as error:
            status.set("Plan check failed: " + str(error))

    ttk.Button(root, text="Check edit plan", command=inspect).grid(row=3, column=0, padx=12)
    completed = queue.Queue()

    def finish(destination, error=None):
        button.configure(state="normal")
        status.set("Render failed: " + str(error) if error else "MP4 created: " + destination)
        if error:
            messagebox.showerror("Render failed", str(error))

    def worker(plan_path, destination, music_path):
        try:
            from .render import render_file
            render_file(plan_path, destination, music_path or None)
            completed.put((destination, None))
        except Exception as error:
            completed.put((destination, error))

    def poll():
        try:
            finish(*completed.get_nowait())
        except queue.Empty:
            pass
        root.after(100, poll)

    def start():
        if not plan.get() or not output.get():
            messagebox.showwarning("Missing input", "Choose an edit plan and output location.")
            return
        button.configure(state="disabled")
        status.set("Rendering locally with FFmpeg. Please wait...")
        threading.Thread(target=worker, args=(plan.get(), output.get(), music.get()), daemon=True).start()

    button.configure(command=start)
    root.after(100, poll)
    root.mainloop()

if __name__ == "__main__":
    import sys
    if "--legacy" in sys.argv:
        main()
    else:
        from .guided import main as guided_main
        guided_main()
