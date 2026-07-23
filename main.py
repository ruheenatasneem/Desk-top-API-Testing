import os 
import tkinter as tk 
import tkinter.ttk as ttk 
from tkinter.messagebox import showinfo 
import ttkbootstrap as tb
from ttkbootstrap.constants import * 
from ui.main_window import APITester

 
if __name__ == "__main__":
    root = tb.Window()
    app = APITester(root)
    
    # Optional button to view full history
    tb.Button(root, text="View History", bootstyle=INFO, command=app.view_history).pack(pady=5)
    
    # Set the app icon safely
    icon_path = os.path.join(os.path.dirname(__file__),'API.ico')
    
    root.mainloop()
