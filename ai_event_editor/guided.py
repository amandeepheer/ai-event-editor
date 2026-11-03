"""Guided local desktop workflow. All Tk operations run on the main thread."""
from dataclasses import asdict
import json
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .workflow import Setup, prepare_footage, create_edit, coverage, save_session, load_session
from .planner import ORDER
from .styles import PRESETS

class GuidedEditor:
    def __init__(self, root):
        self.root = root
        root.title('AI Event Editor — Local Studio')
        root.geometry('1040x740')
        root.minsize(800, 620)
        self.paths, self.candidates, self.edit = [], [], None
        self.cache = tempfile.TemporaryDirectory(prefix='ai-event-review-')
        self.events = queue.Queue()
        self.busy, self.photo = False, None
        self.music = tk.StringVar()
        self.start = tk.StringVar(value='0')
        self.end = tk.StringVar()
        self.duration = tk.StringVar(value='60')
        self.style = tk.StringVar(value='energetic-event')
        self.pacing = tk.StringVar(value='Balanced')
        self.ai = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value='Add local footage to begin. Your original files stay unchanged.')
        self.summary = tk.StringVar(value='No edit created yet.')
        self.source_label = tk.StringVar(value='No footage added')
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=16, pady=12)
        self.setup_tab, self.review_tab, self.create_tab = [ttk.Frame(self.notebook, padding=16) for _ in range(3)]
        for tab, title in zip((self.setup_tab, self.review_tab, self.create_tab), ('1 · Footage & music', '2 · Review moments', '3 · Create edit')):
            self.notebook.add(tab, text=title)
        self.setup_screen()
        self.review_screen()
        self.create_screen()
        ttk.Label(root, textvariable=self.status, wraplength=960).pack(fill='x', padx=20, pady=8)
        for variable in (self.music, self.start, self.end, self.duration, self.style, self.pacing):
            variable.trace_add('write', lambda *args:self.invalidate())
        self.root.after(100, self.poll)
        self.root.protocol('WM_DELETE_WINDOW', self.close)

    def setup_screen(self):
        frame = self.setup_tab
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text='Create an event highlight', font=('', 19, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', pady=(0,16))
        ttk.Button(frame, text='Add footage', command=self.add_files).grid(row=1, column=0, sticky='w')
        ttk.Button(frame, text='Add folder', command=self.add_folder).grid(row=1, column=1, sticky='w')
        ttk.Button(frame, text='Clear footage', command=self.clear_files).grid(row=1, column=2)
        ttk.Label(frame, textvariable=self.source_label, wraplength=800).grid(row=2, column=0, columnspan=3, sticky='w', pady=12)
        fields = [('Music (optional)', self.music), ('Excerpt start (seconds)', self.start),
                  ('Excerpt end (blank = start + edit length)', self.end), ('Edit length (30–300 seconds)', self.duration)]
        for row, (label, variable) in enumerate(fields, 3):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky='w', pady=8)
            ttk.Entry(frame, textvariable=variable).grid(row=row, column=1, sticky='ew', padx=12)
        ttk.Button(frame, text='Choose music', command=self.choose_music).grid(row=3, column=2)
        ttk.Button(frame, text='Listen to excerpt', command=self.preview_music).grid(row=4, column=2)
        for row, label, variable, values in [(7, 'Style', self.style, tuple(PRESETS)), (8, 'Pacing', self.pacing, ('Calm','Balanced','Energetic'))]:
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky='w', pady=8)
            ttk.Combobox(frame, textvariable=variable, values=values, state='readonly').grid(row=row, column=1, sticky='ew', padx=12)
        ttk.Checkbutton(frame, text='Suggest categories using an already cached local CLIP model (optional)', variable=self.ai).grid(row=9, column=0, columnspan=3, sticky='w', pady=12)
        ttk.Label(frame, text='Default analysis creates unranked moments for you to review. AI mode needs vision extras and cached model weights; it never downloads models here.', wraplength=850).grid(row=10, column=0, columnspan=3, sticky='w')
        ttk.Button(frame, text='Prepare moments →', command=self.prepare).grid(row=11, column=1, sticky='e', pady=20)
        ttk.Button(frame, text='Open saved review', command=self.open_review).grid(row=11, column=0, sticky='w')
        ttk.Button(frame, text='Render an existing plan…', command=lambda: subprocess.Popen([sys.executable, '-m', 'ai_event_editor.desktop', '--legacy'])).grid(row=12, column=0, sticky='w')

    def review_screen(self):
        frame = self.review_tab
        ttk.Label(frame, text='Choose the moments that matter', font=('', 18, 'bold')).pack(anchor='w')
        ttk.Label(frame, text='Keep makes a shot eligible. Must include guarantees an excerpt from that moment. Reject excludes it.').pack(anchor='w', pady=8)
        columns = ('decision','file','range','category','quality')
        self.tree = ttk.Treeview(frame, columns=columns, show='headings', selectmode='extended', height=13)
        for col, title, width in zip(columns, ('Decision','Source clip','Seconds','Category','Quality heuristic'), (100,270,120,120,130)):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width)
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.show_shot)
        actions = ttk.Frame(frame)
        actions.pack(fill='x', pady=10)
        for text, decision in [('Keep','keep'), ('Reject','reject'), ('Must include','must_include')]:
            ttk.Button(actions, text=text, command=lambda d=decision: self.decide(d)).pack(side='left', padx=3)
        ttk.Button(actions, text='Preview moment', command=self.preview_shot).pack(side='left', padx=8)
        self.category = tk.StringVar(value='performance')
        ttk.Combobox(actions, textvariable=self.category, values=ORDER, state='readonly', width=14).pack(side='left')
        ttk.Button(actions, text='Set category', command=self.set_category).pack(side='left', padx=3)
        details = ttk.Frame(frame)
        details.pack(fill='x')
        self.thumbnail = ttk.Label(details, text='Select a moment to see its thumbnail')
        self.thumbnail.pack(side='left', padx=(0,16))
        self.coverage_label = ttk.Label(details, wraplength=650)
        self.coverage_label.pack(side='left')
        bottom = ttk.Frame(frame)
        bottom.pack(fill='x', pady=12)
        ttk.Button(bottom, text='Save review', command=self.save_review).pack(side='left')
        ttk.Button(bottom, text='Create reviewed edit →', command=self.build).pack(side='right')

    def create_screen(self):
        frame = self.create_tab
        ttk.Label(frame, text='Your reviewed edit', font=('', 19, 'bold')).pack(anchor='w')
        ttk.Label(frame, textvariable=self.summary, wraplength=850).pack(anchor='w', pady=20)
        ttk.Button(frame, text='Save edit for Premiere', command=self.save_edit).pack(anchor='w', pady=8)
        ttk.Button(frame, text='Render MP4 locally', command=self.render).pack(anchor='w', pady=8)
        ttk.Button(frame, text='← Return to shot review', command=lambda: self.notebook.select(self.review_tab)).pack(anchor='w', pady=8)
        ttk.Label(frame, text='In the Premiere panel, choose Open reviewed edit, select the saved file, then Create new sequence. Native integration is experimental until tested in your Premiere installation.\n\nEffects intensity and interviews/speech mixing are planned for later. Current creation uses normal-speed cuts; style names describe pacing, not applied transitions or colour grading.', wraplength=850).pack(anchor='w', pady=20)

    def ensure_idle(self):
        if self.busy:
            self.status.set('An operation is running. Wait for it to finish.')
            return False
        return True

    def invalidate(self):
        self.edit = None
        self.summary.set('Inputs changed. Create the edit again after review.')

    def add_files(self):
        if not self.ensure_idle(): return
        paths = filedialog.askopenfilenames(filetypes=[('Video clips','*.mp4 *.mov *.mxf *.m4v'), ('All files','*.*')])
        if paths: self.set_paths([*self.paths, *paths])

    def add_folder(self):
        if not self.ensure_idle(): return
        folder = filedialog.askdirectory()
        if folder:
            from .media import SUPPORTED
            self.set_paths([*self.paths, *(str(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.suffix.lower() in SUPPORTED)])

    def clear_files(self):
        if self.ensure_idle(): self.set_paths([])

    def set_paths(self, paths):
        self.paths = list(dict.fromkeys(paths))
        self.source_label.set(f'{len(self.paths)} source clips selected. Preparing again preserves decisions for unchanged moments.')
        self.invalidate()

    def choose_music(self):
        if not self.ensure_idle(): return
        selected = filedialog.askopenfilename(filetypes=[('Audio','*.wav *.mp3 *.m4a *.aac *.flac'), ('All files','*.*')])
        if selected:
            self.music.set(selected)
            self.invalidate()

    def setup(self):
        return Setup(duration=int(self.duration.get()), style=self.style.get(), pacing=self.pacing.get(), music=self.music.get(),
                     audio_start=float(self.start.get()), audio_end=float(self.end.get()) if self.end.get().strip() else None)

    def lock_controls(self, locked):
        def descendants(parent):
            for widget in parent.winfo_children():
                yield widget
                yield from descendants(widget)
        if locked:
            self.previous_states = []
            for widget in descendants(self.notebook):
                if isinstance(widget, (ttk.Button, ttk.Entry, ttk.Checkbutton, ttk.Treeview)):
                    self.previous_states.append((widget, widget.state()))
                    widget.state(['disabled'])
        else:
            for widget, state in getattr(self, 'previous_states', []):
                widget.state(['!disabled'])
                if state: widget.state(state)

    def job(self, function, done):
        if not self.ensure_idle(): return
        self.busy = True
        self.lock_controls(True)
        def worker():
            try: self.events.put(('done', done, function()))
            except Exception as error: self.events.put(('error', str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == 'progress': self.status.set(event[1])
                elif event[0] == 'error':
                    self.busy = False
                    self.lock_controls(False)
                    self.status.set('Could not complete: '+event[1])
                    messagebox.showerror('Operation failed', event[1])
                else:
                    self.busy = False
                    self.lock_controls(False)
                    try: event[1](event[2])
                    except Exception as error:
                        self.status.set('Could not update the view: '+str(error))
                        messagebox.showerror('Display error', str(error))
        except queue.Empty: pass
        self.root.after(100, self.poll)

    def prepare(self):
        if not self.ensure_idle(): return
        if not self.paths:
            messagebox.showwarning('No footage', 'Add footage first.'); return
        paths, use_ai = list(self.paths), self.ai.get()
        self.status.set('Inspecting local footage…')
        old = {c['id']: c for c in self.candidates}
        def done(result):
            self.candidates = [{**c, **{k:old[c['id']][k] for k in ('decision','category') if c['id'] in old}} for c in result['candidates']]
            self.invalidate()
            self.refresh()
            self.notebook.select(self.review_tab)
            self.status.set(result['analysis']+f". {len(result['errors'])} file errors.")
            if result['errors']: messagebox.showwarning('Some clips could not be read', '\n'.join(result['errors'][:12]))
        self.job(lambda: prepare_footage(paths, self.cache.name, use_ai, lambda m:self.events.put(('progress',m))), done)

    def refresh(self):
        selection = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        for c in self.candidates:
            self.tree.insert('', 'end', iid=c['id'], values=(c['decision'],Path(c['path']).name,f"{c['start']:.2f}–{c['end']:.2f}",c['category'],f"{c.get('quality',.5):.2f}" if c.get('model')!='manual-review' else 'Unranked'))
        self.tree.selection_set([i for i in selection if self.tree.exists(i)])
        report = coverage(self.candidates)
        self.coverage_label.configure(text=f"{report['kept']} eligible moments · {report['must_include']} must include · {report['available_seconds']:g}s before overlap removal.\nMissing coverage: {', '.join(report['missing_categories']) or 'none'}. Missing categories never block creation.")

    def decide(self, decision):
        if not self.ensure_idle(): return
        selected = set(self.tree.selection())
        for c in self.candidates:
            if c['id'] in selected: c['decision'] = decision
        self.invalidate(); self.refresh()

    def set_category(self):
        if not self.ensure_idle(): return
        selected = set(self.tree.selection())
        for c in self.candidates:
            if c['id'] in selected: c['category'] = self.category.get()
        self.invalidate(); self.refresh()

    def current_shot(self):
        selected = self.tree.selection()
        return next((c for c in self.candidates if selected and c['id']==selected[0]), None)

    def show_shot(self, event=None):
        shot = self.current_shot()
        if not shot: return
        self.category.set(shot['category'])
        try:
            self.photo = tk.PhotoImage(file=shot['thumbnail']) if shot.get('thumbnail') else None
            self.thumbnail.configure(image=self.photo or '', text='' if self.photo else 'Thumbnail unavailable')
        except tk.TclError:
            self.photo = None
            self.thumbnail.configure(image='', text='Thumbnail unavailable')

    def preview_shot(self):
        shot = self.current_shot()
        if shot:
            self.play(['-ss', str(shot['start']), '-t', str(shot['end']-shot['start']), shot['path']])

    def preview_music(self):
        try:
            setup = self.setup()
            if not setup.music: raise ValueError('Choose music first')
            from .music import AudioRange
            end = setup.audio_end if setup.audio_end is not None else setup.audio_start+setup.duration
            AudioRange(setup.audio_start, end).validate()
            self.play(['-nodisp', '-ss', str(setup.audio_start), '-t', str(end-setup.audio_start), setup.music])
        except ValueError as error: messagebox.showerror('Invalid excerpt', str(error))

    def play(self, args):
        try: subprocess.Popen(['ffplay','-autoexit','-loglevel','error',*args])
        except OSError as error: messagebox.showerror('Preview unavailable', str(error))

    def save_review(self):
        if not self.ensure_idle(): return
        try:
            setup = self.setup()
            path = filedialog.asksaveasfilename(defaultextension='.json', initialfile='event-review.json')
            if path:
                save_session(path, self.candidates, setup)
                self.status.set('Review saved: '+path)
        except (ValueError, OSError) as error: messagebox.showerror('Save failed',str(error))

    def open_review(self):
        if not self.ensure_idle(): return
        path = filedialog.askopenfilename(filetypes=[('Saved review','*.json')])
        if not path: return
        try:
            candidates, setup = load_session(path)
            self.candidates = candidates
            self.paths = list(dict.fromkeys(c['path'] for c in candidates))
            for name, value in asdict(setup).items():
                {'duration':self.duration,'style':self.style,'pacing':self.pacing,'music':self.music,'audio_start':self.start,'audio_end':self.end}[name].set('' if value is None else value)
            self.invalidate(); self.refresh()
            self.source_label.set(f'{len(self.paths)} clips from saved review')
            self.notebook.select(self.review_tab)
            self.status.set('Review restored. Re-prepare moments to regenerate missing temporary thumbnails.')
        except (ValueError, OSError, KeyError, TypeError) as error: messagebox.showerror('Open failed',str(error))

    def build(self):
        if not self.ensure_idle(): return
        try: setup = self.setup()
        except ValueError as error: messagebox.showerror('Invalid setup',str(error)); return
        from copy import deepcopy
        candidates = deepcopy(self.candidates)
        self.status.set('Building your reviewed edit locally…')
        def done(edit):
            self.edit = edit
            self.summary.set(f"{edit['duration_seconds']:g} seconds · {len(edit['segments'])} editable clip segments · {edit['fps']} fps\n{setup.pacing} pacing · {setup.style}\n"+ '\n'.join(edit['warnings']))
            self.notebook.select(self.create_tab)
            self.status.set('Edit created. Save for Premiere or render an MP4.')
        self.job(lambda:create_edit(candidates,setup),done)

    def save_edit(self):
        if not self.ensure_idle(): return
        if not self.edit:
            messagebox.showwarning('No edit','Create a reviewed edit first.'); return
        path = filedialog.asksaveasfilename(defaultextension='.json',initialfile='reviewed-edit.json')
        if path:
            try:
                Path(path).write_text(json.dumps(self.edit, indent=2, allow_nan=False),encoding='utf-8')
                self.status.set('Saved for Premiere: '+path)
            except OSError as error: messagebox.showerror('Save failed',str(error))

    def render(self):
        if not self.ensure_idle(): return
        if not self.edit:
            messagebox.showwarning('No edit','Create a reviewed edit first.'); return
        destination = filedialog.asksaveasfilename(defaultextension='.mp4',initialfile='highlight.mp4',filetypes=[('MP4 video','*.mp4')])
        if destination:
            from .render import render
            from copy import deepcopy
            edit = deepcopy(self.edit)
            audio = edit.get('audio',{})
            self.status.set('Rendering locally with FFmpeg…')
            self.job(lambda:render(edit,destination,audio.get('path'),audio.get('start_seconds',0)),lambda p:self.status.set('MP4 created: '+p))

    def close(self):
        if self.busy:
            messagebox.showinfo('Operation running','Wait for the current local operation to finish before closing.'); return
        self.cache.cleanup()
        self.root.destroy()


def main():
    root = tk.Tk()
    GuidedEditor(root)
    root.mainloop()

if __name__ == '__main__': main()
