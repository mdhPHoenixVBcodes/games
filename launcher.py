import os
import sys
import ast
import subprocess
import threading
import importlib.util
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path

# Optional Pillow support for .ico, .png, and image resizing
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Mapping for imports whose PyPI package name differs from the import statement
PYPI_PACKAGE_MAP = {
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "bs4": "beautifulsoup4",
    "yaml": "pyyaml",
    "OpenGL": "PyOpenGL",
    "sklearn": "scikit-learn"
}

class GameLauncher(tk.Tk):
    def __init__(self, games_dir="."):
        super().__init__()
        self.title("🎮 mdhPHoenixVBcodes - Game Hub")
        self.geometry("860x680")
        self.minsize(650, 450)
        self.configure(bg="#1e1e2e")
        
        self.games_dir = Path(games_dir).resolve()
        self.running_processes = []
        self.all_games = []
        
        # Performance Caches
        self.icon_cache = {}
        self.dep_cache = {}

        self.placeholder_text = "Search Bar..."
        self.placeholder_color = "#6c7086"
        self.text_color = "#cdd6f4"

        self.setup_styles()
        self.create_widgets()
        self.scan_and_populate_games()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        BG_COLOR = "#1e1e2e"
        CARD_BG = "#2b2b3b"
        TEXT_COLOR = "#cdd6f4"
        ACCENT_COLOR = "#89b4fa"
        
        self.style.configure(".", background=BG_COLOR, foreground=TEXT_COLOR)
        self.style.configure("TFrame", background=BG_COLOR)
        self.style.configure("Card.TFrame", background=CARD_BG, relief="flat")
        self.style.configure("Header.TLabel", font=("Helvetica", 16, "bold"), background=BG_COLOR, foreground=ACCENT_COLOR)
        self.style.configure("Title.TLabel", font=("Helvetica", 13, "bold"), background=CARD_BG, foreground=TEXT_COLOR)
        self.style.configure("Sub.TLabel", font=("Helvetica", 9), background=CARD_BG, foreground="#a6adc8")

    def create_widgets(self):
        # Header Section
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        header_title = ttk.Label(header_frame, text="🕹️ Game Launcher", style="Header.TLabel")
        header_title.pack(side="left")

        # Action Buttons in Header
        header_btns = ttk.Frame(header_frame)
        header_btns.pack(side="right")

        self.sync_btn = tk.Button(
            header_btns, text="⚡ Sync Git", command=self.git_sync,
            bg="#89b4fa", fg="#11111b", activebackground="#b4befe", activeforeground="#11111b",
            bd=0, padx=12, pady=6, font=("Helvetica", 9, "bold"), cursor="hand2"
        )
        self.sync_btn.pack(side="left", padx=(0, 8))

        refresh_btn = tk.Button(
            header_btns, text="🔄 Refresh", command=self.scan_and_populate_games,
            bg="#313244", fg="#cdd6f4", activebackground="#45475a", activeforeground="#ffffff",
            bd=0, padx=12, pady=6, font=("Helvetica", 9, "bold"), cursor="hand2"
        )
        refresh_btn.pack(side="left")

        # Search Bar Section
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", padx=20, pady=(0, 15))

        search_icon = tk.Label(search_frame, text="🔍", bg="#1e1e2e", fg="#a6adc8", font=("Helvetica", 11))
        search_icon.pack(side="left", padx=(0, 5))

        self.search_entry = tk.Entry(
            search_frame,
            bg="#313244", fg=self.placeholder_color, insertbackground=self.text_color,
            font=("Helvetica", 11, "italic"), bd=0, relief="flat"
        )
        self.search_entry.insert(0, self.placeholder_text)
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=6, ipadx=8)

        self.search_entry.bind("<FocusIn>", self._on_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_focus_out)
        self.search_entry.bind("<KeyRelease>", lambda e: self.filter_games())

        # Scrollable Canvas Container
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.canvas = tk.Canvas(container, bg="#1e1e2e", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    def _on_focus_in(self, event):
        if self.search_entry.get() == self.placeholder_text:
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(fg=self.text_color, font=("Helvetica", 11, "normal"))

    def _on_focus_out(self, event):
        if not self.search_entry.get().strip():
            self.search_entry.insert(0, self.placeholder_text)
            self.search_entry.config(fg=self.placeholder_color, font=("Helvetica", 11, "italic"))

    def git_sync(self):
        """Fast non-blocking Git Sync with --autostash --rebase."""
        self.sync_btn.config(text="⏳ Syncing...", state="disabled")
        
        def task():
            try:
                res = subprocess.run(
                    ["git", "pull", "--rebase", "--autostash"],
                    capture_output=True, text=True, cwd=str(self.games_dir)
                )
                if res.returncode == 0:
                    self.after(0, lambda: messagebox.showinfo("Git Sync", f"Sync Complete!\n\n{res.stdout}"))
                    self.after(0, self.scan_and_populate_games)
                else:
                    self.after(0, lambda: messagebox.showerror("Git Sync Error", f"Git pull failed:\n\n{res.stderr}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Git Error", f"Could not execute git pull:\n{e}"))
            finally:
                self.after(0, lambda: self.sync_btn.config(text="⚡ Sync Git", state="normal"))

        threading.Thread(target=task, daemon=True).start()

    def load_icon_image(self, icon_path, size=(52, 52)):
        """Fast, robust cached icon loader."""
        if not icon_path or not icon_path.exists():
            return None

        cache_key = str(icon_path)
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]

        try:
            if HAS_PIL:
                with Image.open(icon_path) as img:
                    img = img.convert("RGBA")
                    img = img.resize(size, Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
            else:
                photo = tk.PhotoImage(file=str(icon_path))

            self.icon_cache[cache_key] = photo
            return photo
        except Exception:
            return None

    def scan_missing_dependencies(self, game_entry_path):
        """Cached AST scanner that detects imported external libraries not yet installed."""
        cache_key = str(game_entry_path)
        if cache_key in self.dep_cache:
            return self.dep_cache[cache_key]

        stdlib = getattr(sys, 'stdlib_module_names', {
            'os', 'sys', 'math', 'random', 'time', 'tkinter', 'subprocess',
            'threading', 'pathlib', 'ast', 're', 'json', 'importlib', 'typing',
            'collections', 'functools', 'itertools', 'dataclasses', 'struct'
        })

        target_dir = game_entry_path.parent if game_entry_path.is_file() else game_entry_path
        py_files = list(target_dir.rglob("*.py")) if target_dir.is_dir() else [game_entry_path]

        local_script_names = {f.stem.lower() for f in py_files}
        imported_modules = set()

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(content, filename=str(py_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported_modules.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and node.level == 0:
                            imported_modules.add(node.module.split('.')[0])
            except Exception:
                continue

        missing_packages = []
        for mod in sorted(imported_modules):
            if mod in stdlib or mod.lower() in local_script_names:
                continue
            if importlib.util.find_spec(mod) is None:
                pypi_name = PYPI_PACKAGE_MAP.get(mod, mod)
                if pypi_name not in missing_packages:
                    missing_packages.append(pypi_name)

        self.dep_cache[cache_key] = missing_packages
        return missing_packages

    def install_detected_packages(self, packages):
        """Installs list of missing packages using pip in a background thread."""
        def task():
            try:
                cmd = [sys.executable, "-m", "pip", "install"] + packages
                proc = subprocess.run(cmd, capture_output=True, text=True)
                if proc.returncode == 0:
                    self.dep_cache.clear()  # Force rescanning of dependencies
                    self.after(0, lambda: messagebox.showinfo("Pip Installer", f"Successfully installed: {', '.join(packages)}"))
                    self.after(0, self.scan_and_populate_games)
                else:
                    self.after(0, lambda: self.show_crash_log("Pip Installation Error", proc.stderr))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Installer Error", f"Failed to run pip:\n{e}"))

        threading.Thread(target=task, daemon=True).start()

    def show_crash_log(self, title_name, error_msg):
        """Dark-themed traceback output window."""
        log_win = tk.Toplevel(self)
        log_win.title(f"⚠️ Error Log - {title_name}")
        log_win.geometry("680x480")
        log_win.configure(bg="#1e1e2e")

        lbl = tk.Label(
            log_win, text=f"🚨 '{title_name}' encountered an error:",
            bg="#1e1e2e", fg="#f38ba8", font=("Helvetica", 11, "bold"), pady=10, padx=12, anchor="w"
        )
        lbl.pack(fill="x")

        text_area = scrolledtext.ScrolledText(
            log_win, bg="#11111b", fg="#f38ba8", font=("Consolas", 10),
            insertbackground="#cdd6f4", bd=0, padx=10, pady=10
        )
        text_area.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        text_area.insert(tk.END, error_msg)
        text_area.config(state="disabled")

        close_btn = tk.Button(
            log_win, text="Close Window", command=log_win.destroy,
            bg="#313244", fg="#cdd6f4", activebackground="#45475a",
            bd=0, padx=16, pady=6, font=("Helvetica", 9, "bold"), cursor="hand2"
        )
        close_btn.pack(pady=(0, 12))

    def find_entry_point(self, folder_path):
        all_py_files = [f for f in folder_path.rglob("*.py") if f.is_file() and not f.name.startswith(("_", "."))]
        if not all_py_files:
            return None

        priority_names = [
            "racing.py", "main.py", "game.py", "app.py", "run.py", "play.py",
            f"{folder_path.name.lower()}.py"
        ]
        
        for target in priority_names:
            for py_file in all_py_files:
                if py_file.name.lower() == target:
                    return py_file

        return all_py_files[0]

    def find_icon(self, search_dir, base_name):
        extensions = [".ico", ".png", ".jpg", ".jpeg"]
        preferred_names = ["logo", "icon", "app", base_name.lower(), base_name]

        subfolders = ["Logo", "logo", "Icons", "icons", "Assets", "assets", "Images", "images", "img"]
        dirs_to_check = [search_dir] + [search_dir / sub for sub in subfolders if (search_dir / sub).is_dir()]

        for d in dirs_to_check:
            for name in preferred_names:
                for ext in extensions:
                    icon_path = d / f"{name}{ext}"
                    if icon_path.exists():
                        return icon_path

        return None

    def find_games(self):
        games = []
        current_script = Path(__file__).resolve() if '__file__' in globals() else None

        for item in sorted(self.games_dir.iterdir()):
            if item == current_script or item.name.startswith((".", "_")):
                continue

            if item.is_file() and item.suffix == ".py":
                icon_path = self.find_icon(self.games_dir, item.stem)
                games.append({
                    "name": item.stem.replace("_", " ").title(),
                    "path": item,
                    "desc": f"Script: {item.name}",
                    "icon": icon_path
                })
            
            elif item.is_dir():
                entry_path = self.find_entry_point(item)
                if entry_path and entry_path.is_file():
                    icon_path = self.find_icon(item, item.name)
                    games.append({
                        "name": item.name.replace("_", " ").title(),
                        "path": entry_path,
                        "desc": f"Script: {entry_path.relative_to(self.games_dir)}",
                        "icon": icon_path
                    })
        return games

    def scan_and_populate_games(self):
        self.all_games = self.find_games()
        self.filter_games()

    def filter_games(self):
        query = self.search_entry.get().strip().lower()
        if query == self.placeholder_text.lower():
            query = ""

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        filtered_games = [
            g for g in self.all_games 
            if query in g["name"].lower() or query in g["desc"].lower()
        ]

        if not filtered_games:
            msg = "No games found matching your search." if query else "No games detected in this folder!"
            no_games_lbl = ttk.Label(self.scrollable_frame, text=msg, font=("Helvetica", 11, "italic"))
            no_games_lbl.pack(pady=40, padx=20)
            return

        for game in filtered_games:
            self.create_game_card(game)

    def create_game_card(self, game_info):
        card = ttk.Frame(self.scrollable_frame, style="Card.TFrame", padding=12)
        card.pack(fill="x", expand=True, pady=6, padx=5)

        # Icon Display
        icon_img = self.load_icon_image(game_info["icon"])
        if icon_img:
            icon_label = tk.Label(card, image=icon_img, bg="#2b2b3b")
            icon_label.pack(side="left", padx=(0, 12))
        else:
            badge = tk.Label(
                card, text="🎮", font=("Helvetica", 20),
                bg="#313244", fg="#cdd6f4", width=3, height=1
            )
            badge.pack(side="left", padx=(0, 12))

        # Text Info
        info_frame = ttk.Frame(card, style="Card.TFrame")
        info_frame.pack(side="left", fill="x", expand=True)

        title = ttk.Label(info_frame, text=game_info["name"], style="Title.TLabel")
        title.pack(anchor="w")

        desc = ttk.Label(info_frame, text=game_info["desc"], style="Sub.TLabel")
        desc.pack(anchor="w", pady=(2, 0))

        # Actions Frame
        btn_frame = ttk.Frame(card, style="Card.TFrame")
        btn_frame.pack(side="right")

        # Async Dependency Checker
        def async_check_deps():
            missing = self.scan_missing_dependencies(game_info["path"])
            if missing:
                def add_dep_button():
                    if card.winfo_exists():
                        dep_text = f"📦 Install ({', '.join(missing)})"
                        req_btn = tk.Button(
                            btn_frame, text=dep_text,
                            command=lambda: self.install_detected_packages(missing),
                            bg="#fab387", fg="#11111b", activebackground="#f9e2af", activeforeground="#11111b",
                            font=("Helvetica", 9, "bold"), bd=0, padx=10, pady=6, cursor="hand2"
                        )
                        req_btn.pack(side="left", padx=(0, 8))
                self.after(0, add_dep_button)

        threading.Thread(target=async_check_deps, daemon=True).start()

        # Launch Button
        play_btn = tk.Button(
            btn_frame, text="▶ PLAY",
            command=lambda: self.launch_game(game_info["path"], game_info["name"]),
            bg="#a6e3a1", fg="#11111b", activebackground="#94e2d5", activeforeground="#11111b",
            font=("Helvetica", 10, "bold"), bd=0, padx=16, pady=6, cursor="hand2"
        )
        play_btn.pack(side="left")

    def launch_game(self, game_path, game_name):
        if not game_path.is_file():
            messagebox.showerror("Error", f"Path is not a valid Python file:\n{game_path}")
            return

        try:
            proc = subprocess.Popen(
                [sys.executable, str(game_path)],
                cwd=str(game_path.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.running_processes.append(proc)

            def monitor():
                stdout, stderr = proc.communicate()
                if proc.returncode != 0 and stderr:
                    self.after(0, lambda: self.show_crash_log(game_name, stderr))

            threading.Thread(target=monitor, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Execution Error", f"Could not launch game:\n{e}")

    def on_closing(self):
        for proc in self.running_processes:
            if proc.poll() is None:
                proc.terminate()
        self.destroy()

if __name__ == "__main__":
    app = GameLauncher()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()