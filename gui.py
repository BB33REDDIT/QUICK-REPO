import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess
import os
import re

try:
    from git_smart_commit import git
    from git_smart_commit.engine import analyze
except ImportError:
    messagebox.showerror('Error', "git_smart_commit module not found. Run 'pip install -e .' in the package folder first.")
    exit(1)

BG_DARK = '#121212'
PANEL_BG = '#1e1e1e'
BORDER_COLOR = '#333333'
FG_MAIN = '#e0e0e0'
FG_MUTED = '#888888'
ACCENT_BLUE = '#0066ff'
ACCENT_HOVER = '#2a80ff'
SUCCESS_GREEN = '#00ffcc'
FONT_MONO = ('Consolas', 10)
FONT_BOLD = ('Consolas', 11, 'bold')

class BBRepoSmartCommitGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('BB REPO')
        self.geometry('780x480')
        self.configure(bg=BG_DARK)
        
        self.repo_path = os.path.abspath(os.getcwd())
        self.staged_files = []
        
        header_frame = tk.Frame(self, bg=PANEL_BG, height=40)
        header_frame.pack(fill='x', padx=15, pady=(15, 5))
        header_frame.pack_propagate(False)
        self.path_lbl = tk.Label(header_frame, text=f'repo: {self.repo_path}', bg=PANEL_BG, fg=FG_MAIN, font=FONT_BOLD, anchor='w')
        self.path_lbl.pack(side='left')
        self.btn_browse = tk.Button(header_frame, text='[ switch ]', bg='#2a2a2a', fg=FG_MAIN, font=FONT_MONO, relief='flat', borderwidth=0, cursor='hand2', command=self.browse_repo)
        self.btn_browse.pack(side='right')
        
        self.status_lbl = tk.Label(self, text='status: scanning working tree...', bg=BG_DARK, fg=FG_MUTED, font=FONT_MONO, anchor='w')
        self.status_lbl.pack(fill='x', padx=15, pady=(8, 5))
        
        editor_frame = tk.Frame(self, bg=PANEL_BG, highlightthickness=1, highlightbackground=BORDER_COLOR)
        editor_frame.pack(fill='both', expand=True, padx=15, pady=5)
        
        # ENABLED BULK SELECT: You can now hold Ctrl or Shift to select multiple files
        self.file_list = tk.Listbox(editor_frame, bg='#161616', fg=FG_MUTED, font=('Consolas', 9), relief='flat', width=35, highlightthickness=0, selectbackground=ACCENT_BLUE, selectforeground='#ffffff', selectmode=tk.EXTENDED)
        self.file_list.pack(side='left', fill='y', padx=10, pady=10)
        self.file_list.bind('<<ListboxSelect>>', self.on_file_select)
        
        text_frame = tk.Frame(editor_frame, bg=PANEL_BG)
        text_frame.pack(side='right', fill='both', expand=True)
        
        lbl_box = tk.Label(text_frame, text=' BAKING COOKIES (=^･ｪ･^=) ', bg=PANEL_BG, fg=ACCENT_BLUE, font=FONT_BOLD, anchor='w')
        lbl_box.pack(fill='x', pady=(10, 0))
        
        self.pill_frame = tk.Frame(text_frame, bg=PANEL_BG)
        self.pill_frame.pack(fill='x', pady=(5, 0))
        
        commit_types = ['feat', 'fix', 'test', 'chore', 'docs', 'refactor']
        for t in commit_types:
            btn = tk.Button(self.pill_frame, text=f' {t} ', bg='#2a2a2a', fg=FG_MAIN, font=('Consolas', 9), relief='flat', borderwidth=0, cursor='hand2', command=lambda type_val=t: self.change_commit_type(type_val))
            btn.pack(side='left', padx=(0, 5))
            btn.bind('<Enter>', lambda e, b=btn: b.configure(bg='#3a3a3a'))
            btn.bind('<Leave>', lambda e, b=btn: b.configure(bg='#2a2a2a'))
            
        self.msg_box = tk.Text(text_frame, height=4, bg='#161616', fg=FG_MAIN, font=('Consolas', 11), relief='flat', insertbackground='white', padx=10, pady=10)
        self.msg_box.pack(fill='both', expand=True, pady=10, padx=(0, 10))
        
        action_frame = tk.Frame(self, bg=BG_DARK)
        action_frame.pack(fill='x', padx=15, pady=10)
        
        self.btn_refresh = tk.Button(action_frame, text='[ refresh ]', bg='#252526', fg=FG_MAIN, font=FONT_BOLD, relief='flat', borderwidth=0, cursor='hand2', command=self.refresh)
        self.btn_refresh.pack(side='left')
        
        self.btn_commit = tk.Button(action_frame, text='[ commit changes ]', bg=ACCENT_BLUE, fg='#ffffff', font=FONT_BOLD, relief='flat', borderwidth=0, cursor='hand2', command=self.commit)
        self.btn_commit.pack(side='right')
        
        self.cat_frame = tk.Frame(self, bg='#0d0d0d', height=30)
        self.cat_frame.pack(fill='x', side='bottom')
        self.cat_frame.pack_propagate(False)
        self.cat_lbl = tk.Label(self.cat_frame, text='(=^･ω･^=) bb-repo initialized. waiting for work...', bg='#0d0d0d', fg=SUCCESS_GREEN, font=FONT_MONO)
        self.cat_lbl.pack(side='left', padx=15)
        
        self.cat_state = 0
        self.animate_cat()
        self.refresh()

    def on_file_select(self, event):
        sel = self.file_list.curselection()
        if not sel: return
        
        selected_file = self.staged_files[sel[0]]
        root = git.repo_root(cwd=self.repo_path)
        
        s = analyze([selected_file], root)
        
        self.msg_box.delete('1.0', tk.END)
        if s:
            clean_msg = re.sub(r'\([^)]*\)', '', s.subject).replace('  ', ' ')
            self.msg_box.insert('1.0', clean_msg)
            if len(sel) > 1:
                self.cat_lbl.configure(text=f'(=^✨ω✨^=) Multiple targets locked ({len(sel)} files)')
            else:
                self.cat_lbl.configure(text=f'(=^✨ω✨^=) Target locked: {selected_file.path}')
        else:
            self.msg_box.insert('1.0', f"update: {selected_file.path}")

    def change_commit_type(self, new_type):
        current_text = self.msg_box.get('1.0', 'end-1c')
        if not current_text.strip(): return
        
        current_text = re.sub(r'\([^)]*\)', '', current_text).replace('  ', ' ')
        
        match = re.match(r'^([a-zA-Z]+):\s*(.*)', current_text, flags=re.DOTALL)
        if match:
            self.msg_box.delete('1.0', tk.END)
            self.msg_box.insert('1.0', f'{new_type}: {match.group(2)}')
        else:
            self.msg_box.delete('1.0', tk.END)
            self.msg_box.insert('1.0', f'{new_type}: {current_text}')

    def animate_cat(self):
        states = ['(=^･ω･^=)  *watching branch state*', '(=^-_-^=)   zZz...', '(=^w^=)    ~ local thread active ~', '(=^･ｪ･^=)  ready for staging!']
        self.cat_state = (self.cat_state + 1) % len(states)
        self.cat_lbl.configure(text=states[self.cat_state])
        self.after(3000, self.animate_cat)

    def browse_repo(self):
        chosen = filedialog.askdirectory(initialdir=self.repo_path)
        if chosen:
            self.repo_path = os.path.abspath(chosen)
            self.path_lbl.configure(text=f'repo: {self.repo_path}')
            os.chdir(self.repo_path)
            self.refresh()

    def refresh(self):
        self.msg_box.delete('1.0', tk.END)
        self.file_list.delete(0, tk.END)
        self.staged_files.clear()
        
        try:
            os.chdir(self.repo_path)
            root = git.repo_root(cwd=self.repo_path)
            git_files = git.get_staged_files(root)
            
            if not git_files:
                self.status_lbl.configure(text="status: 0 files staged in working tree. (Run 'git add')")
                self.btn_commit.configure(state='disabled', bg='#2a2a2a', fg='#555555')
                self.cat_lbl.configure(text="(=^･_･^=)  No files staged. Run 'git add' to feed the engine.")
                return
            
            self.staged_files = git_files
            for f in git_files:
                self.file_list.insert(tk.END, f" {f.path}")
                
            s = analyze(git_files, root)
            if s:
                self.status_lbl.configure(text=f'status: {len(git_files)} file(s) staged.')
                clean_msg = re.sub(r'\([^)]*\)', '', s.subject).replace('  ', ' ')
                self.msg_box.insert('1.0', clean_msg)
                self.btn_commit.configure(state='normal', bg=ACCENT_BLUE, fg='#ffffff')
                self.cat_lbl.configure(text=f'(=^✨ω✨^=) Analyzed {len(git_files)} file(s). Select file(s) to isolate.')
        except Exception as e:
            self.status_lbl.configure(text=f'CRASH LOG: {type(e).__name__} - {str(e)}', fg='#ff5555')
            self.btn_commit.configure(state='disabled', bg='#2a2a2a', fg='#555555')
            self.cat_lbl.configure(text='(=^✖_✖^=) engine crashed! check status bar.')

    def commit(self):
        msg = self.msg_box.get('1.0', 'end-1c').strip()
        if not msg:
            messagebox.showwarning('Empty', 'Commit message cannot be empty.')
            return
            
        msg = re.sub(r'\([^)]*\)', '', msg).replace('  ', ' ')
            
        sel = self.file_list.curselection()
        if not sel:
            messagebox.showwarning('Select a File', 'Please select at least one file from the sidebar first! This prevents accidentally committing everything as "update multiple files".')
            return
            
        try:
            # Commits only the files you actively highlighted in the sidebar
            for index in sel:
                selected_file = self.staged_files[index]
                subprocess.run(['git', 'commit', selected_file.path, '-m', msg], cwd=self.repo_path, check=True)
            
            self.refresh()
            self.status_lbl.configure(text='status: local commit written successfully.')
            self.cat_lbl.configure(text='(=^>w<^=) SUCCESS! Selected files committed cleanly without brackets.')
        except subprocess.CalledProcessError:
            messagebox.showerror('Failed', 'Git commit failed. Ensure changes are staged.')

if __name__ == '__main__':
    app = BBRepoSmartCommitGUI()
    app.mainloop()