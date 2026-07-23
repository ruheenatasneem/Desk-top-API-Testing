import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox, filedialog
import requests, json, sqlite3, threading, time 
import os


class APITester:
    def __init__(self, root):
        self.root = root
        self.root.title("Mini API Tester")
        self.root.geometry("800x700")
        self.style = tb.Style(theme="cosmo")
        self.dark_mode = False
        self.old_requests = []

        self.init_db()
        self.init_ui()

    # ---------------- UI ----------------
    def init_ui(self):
        # Theme toggle
        tb.Button(self.root, text="Toggle Dark/Light Theme", bootstyle=INFO, command=self.toggle_theme).pack(pady=5)

        # Notebook
        self.notebook = tb.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        # Add first tab
        self.add_tab()

        # New tab button
        tb.Button(self.root, text="New Tab", bootstyle=SECONDARY, command=self.add_tab).pack(pady=5)

    def add_tab(self):
        tab = tb.Frame(self.notebook)
        self.notebook.add(tab, text=f"Request {len(self.notebook.tabs())+1}")

        # URL
        tk.Label(tab, text="URL:").pack(anchor="w", padx=5, pady=2)
        url_entry = tk.Entry(tab, width=80)
        url_entry.pack(padx=5, pady=2)

        # Method
        tk.Label(tab, text="Method:").pack(anchor="w", padx=5, pady=2)
        method_var = tk.StringVar(value="GET")
        method_menu = tb.Combobox(tab, textvariable=method_var, values=["GET", "POST", "PUT", "DELETE"])
        method_menu.pack(padx=5, pady=2)

        # Headers
        tk.Label(tab, text="Headers (JSON):").pack(anchor="w", padx=5, pady=2)
        headers_text = tk.Text(tab, height=5, width=80)
        headers_text.pack(padx=5, pady=2)

        # Body
        tk.Label(tab, text="Body (JSON):").pack(anchor="w", padx=5, pady=2)
        body_text = tk.Text(tab, height=5, width=80)
        body_text.pack(padx=5, pady=2)

        # Buttons
        btn_frame = tk.Frame(tab)
        btn_frame.pack(pady=5)

        send_btn = tb.Button(btn_frame, text="Send Request", bootstyle=SUCCESS,
                             command=lambda: self.send_tab_request(tab))
        send_btn.pack(side="left", padx=5)

        export_btn = tb.Button(btn_frame, text="Export Response", bootstyle=INFO,
                               command=lambda: self.export_response(tab))
        export_btn.pack(side="left", padx=5)

        rerun_btn = tb.Button(btn_frame, text="Re-run Last Request", bootstyle=SECONDARY,
                              command=lambda: self.rerun_request(tab))
        rerun_btn.pack(side="left", padx=5)

        # Response
        tk.Label(tab, text="Response:").pack(anchor="w", padx=5, pady=2)
        response_text = tk.Text(tab, height=15, width=80, wrap="word", font=("Courier", 10))
        response_text.pack(padx=5, pady=2, fill="both", expand=True)

        scrollbar = tk.Scrollbar(response_text, command=response_text.yview)
        scrollbar.pack(side="right", fill="y")
        response_text.config(yscrollcommand=scrollbar.set)

        # Request time
        time_label = tk.Label(tab, text="Request Time: N/A")
        time_label.pack(anchor="w", padx=5, pady=2)

        # Store tab widgets
        tab.widgets = {
            "url_entry": url_entry,
            "method_var": method_var,
            "headers_text": headers_text,
            "body_text": body_text,
            "response_text": response_text,
            "time_label": time_label
        }

    # ---------------- Theme ----------------
    def toggle_theme(self):
        light_theme = "cosmo"
        dark_theme = "darkly"
        new_theme = dark_theme if not self.dark_mode else light_theme
        self.style.theme_use(new_theme)
        self.dark_mode = not self.dark_mode

    # ---------------- Send Request ----------------
    def send_tab_request(self, tab):
        threading.Thread(target=self._send_tab_request_thread, args=(tab,), daemon=True).start()

    def _send_tab_request_thread(self, tab):
        widgets = tab.widgets
        url = widgets["url_entry"].get().strip()
        method = widgets["method_var"].get().upper()
        headers_text = widgets["headers_text"].get("1.0", "end-1c").strip()
        body_text = widgets["body_text"].get("1.0", "end-1c").strip()
        response_text = widgets["response_text"]
        response_text.delete("1.0", tk.END)

        if not url:
            messagebox.showwarning("Input Error", "Please enter a valid URL.")
            return

        # Parse headers
        try:
            headers = json.loads(headers_text) if headers_text else {}
            if not isinstance(headers, dict):
                raise ValueError
        except Exception:
            headers = {}
            messagebox.showwarning("Warning", "Invalid header format. Using empty headers.")

        # Parse body
        try:
            body = json.loads(body_text) if body_text else None
        except json.JSONDecodeError:
            messagebox.showwarning("Warning", "Invalid JSON body. Request not sent.")
            return

        # Send request
        try:
            start_time = time.perf_counter()
            response = requests.request(method, url, headers=headers, json=body)
            elapsed = time.perf_counter() - start_time

            # Display response
            response_text.insert(tk.END, f"Status Code: {response.status_code}\n")
            response_text.insert(tk.END, f"Response Time: {elapsed:.3f} seconds\n\n")
            try:
                json_data = response.json()
                pretty_json = json.dumps(json_data, indent=4)
                response_text.insert(tk.END, pretty_json)
            except json.JSONDecodeError:
                response_text.insert(tk.END, response.text)

            widgets["time_label"].config(text=f"Request Time: {elapsed:.2f} seconds")

            # Save history
            self.old_requests.append(url)
            self.save_history(method, url, headers, body_text, response.status_code, response.text, elapsed)

        except requests.exceptions.RequestException as e:
            response_text.insert(tk.END, f"Request Error: {e}") 

            print("Saved to DB:", method, url, response.status_code)


    # ---------------- Rerun ----------------
    def rerun_request(self, tab):
        if not self.old_requests:
            messagebox.showinfo("Info", "No previous requests to rerun!")
            return
        last_url = self.old_requests[-1]
        tab.widgets["url_entry"].delete(0, tk.END)
        tab.widgets["url_entry"].insert(0, last_url)
        self.send_tab_request(tab)

    # ---------------- Export ----------------
    def export_response(self, tab):
        content = tab.widgets["response_text"].get("1.0", tk.END).strip()
        if not content:
            return
        file = filedialog.asksaveasfilename(defaultextension=".txt",
                                            filetypes=[("Text files", "*.txt"), ("JSON files", "*.json")])
        if file:
            with open(file, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Saved", f"Response saved to:\n{file}")

    # ---------------- DATABASE ---------------- 

    def init_db(self):
    # Always store the DB next to the running script or exe  
     
     base_dir = os.path.dirname(os.path.abspath(__file__))
     db_path = os.path.join(base_dir, "api_tester_history.db")
     print("Using DB at:", db_path)  # Debug print — check console
    
     self.conn = sqlite3.connect(db_path, check_same_thread=False)
     self.cursor = self.conn.cursor() 

     print("DB Path:", self.conn.execute("PRAGMA database_list").fetchone()[2]) 
     self.cursor.execute("""
     CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        method TEXT,
        url TEXT,
        headers TEXT,
        body TEXT,
        status_code INTEGER,
        response TEXT,
        response_time REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
     self.conn.commit()
     
    


    def save_history(self, method, url, headers, body, status, response, elapsed):
        self.cursor.execute("""
            INSERT INTO history (method, url, headers, body, status_code, response, response_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (method, url, json.dumps(headers), body, status, response, elapsed))
        self.conn.commit()

    # ---------------- View History ----------------
    def view_history(self):
        history_window = tk.Toplevel(self.root)
        history_window.title("Request History")
        history_window.geometry("900x500")

        tree = tb.Treeview(history_window, columns=("URL", "Method", "Status", "Time"), show="headings")
        tree.heading("URL", text="URL")
        tree.heading("Method", text="Method")
        tree.heading("Status", text="Status Code")
        tree.heading("Time", text="Response Time (s)")
        tree.column("URL", width=400)
        tree.column("Method", width=100)
        tree.column("Status", width=100)
        tree.column("Time", width=120)
        tree.pack(fill=tk.BOTH, expand=True)

        self.cursor.execute("SELECT url, method, status_code, response_time FROM history ORDER BY id DESC")
        rows = self.cursor.fetchall()
        for row in rows:
            tree.insert("", "end", values=row)

        tb.Button(history_window, text="Clear History", bootstyle=DANGER, command=self.clear_history).pack(pady=5)

    def clear_history(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the history?"):
            self.cursor.execute("DELETE FROM history")
            self.conn.commit()
            messagebox.showinfo("Cleared", "Request history cleared.")


