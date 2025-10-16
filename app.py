# app.py
import threading
import time
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import cv2
import numpy as np
from PIL import Image, ImageTk

from config import CAM_INDEX, FPS_LIMIT, WINDOW_TITLE, ATTEND_COOLDOWN_SEC
from face_engine import FaceEngine
from registry import Registry
from attendance import log_event, daily_stats, user_attendance_stats, can_attend_today, get_next_attendance_status, get_detailed_attendance_data
from utils import CooldownKeeper

class AttendanceApp:
    def __init__(self, root):
        self.root = root
        root.title(WINDOW_TITLE)
        root.geometry("1200x800")
        
        # Adobe Creative Cloud inspired color scheme
        self.colors = {
            'primary': '#6366f1',       # Vibrant Indigo
            'primary_dark': '#4f46e5',  # Darker Indigo
            'secondary': '#8b5cf6',     # Purple
            'success': '#10b981',       # Emerald Green
            'warning': '#f59e0b',       # Amber
            'danger': '#ef4444',        # Red
            'background': '#f0f9ff',    # Sky blue background
            'surface': '#ffffff',       # White surface
            'surface_light': '#e0f2fe', # Light cyan surface
            'text_primary': '#0f172a',  # Dark text
            'text_secondary': '#475569', # Gray text
            'text_muted': '#64748b',   # Muted text
            'border': '#cbd5e1',        # Light border
            'border_light': '#e2e8f0',  # Lighter border
            'accent': '#06b6d4',        # Cyan accent
            'sidebar': '#e0f2fe',       # Light cyan sidebar
            'card': '#ffffff',          # White card
            'hover': '#e0f2fe',         # Light cyan hover
            'gradient_start': '#667eea', # Gradient start
            'gradient_end': '#764ba2',   # Gradient end
            'accent_pink': '#ec4899',    # Pink accent
            'accent_orange': '#f97316',  # Orange accent
            'accent_teal': '#14b8a6'     # Teal accent
        }
        
        # Configure root background
        root.configure(bg=self.colors['background'])
        
        # Configure grid weights for responsive design
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        
        # Main container - no padding for full screen feel
        main_frame = tk.Frame(root, bg=self.colors['background'])
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # No sidebar: use full width for content
        self.nav_buttons = {}
        self.current_nav = "dashboard"
        
        # Main content area
        content_frame = tk.Frame(main_frame, bg=self.colors['background'])
        content_frame.grid(row=0, column=0, sticky="nsew")
        content_frame.grid_rowconfigure(1, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
        
        # Top header bar
        header_frame = tk.Frame(content_frame, bg=self.colors['surface'], height=60)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Header title
        header_title = tk.Label(header_frame, text="Dashboard", 
                               font=("Segoe UI", 18, "bold"), 
                               fg=self.colors['text_primary'], 
                               bg=self.colors['surface'])
        header_title.grid(row=0, column=0, padx=30, pady=20, sticky="w")
        
        # Status indicator in header
        status_frame = tk.Frame(header_frame, bg=self.colors['surface'])
        status_frame.grid(row=0, column=2, padx=30, pady=20, sticky="e")
        
        status_dot = tk.Label(status_frame, text="●", font=("Arial", 12), 
                             fg=self.colors['success'], bg=self.colors['surface'])
        status_dot.pack(side="left", padx=(0, 8))
        
        self.status = tk.Label(status_frame, text="Ready", 
                              font=("Segoe UI", 12), 
                              fg=self.colors['text_secondary'], 
                              bg=self.colors['surface'])
        self.status.pack(side="left")
        
        # Main content area with cards
        main_content = tk.Frame(content_frame, bg=self.colors['background'])
        main_content.grid(row=1, column=0, sticky="nsew", padx=30, pady=20)
        main_content.grid_rowconfigure(0, weight=1)
        main_content.grid_columnconfigure(0, weight=2)
        main_content.grid_columnconfigure(1, weight=1)
        
        # Left side - Video card
        video_card = tk.Frame(main_content, bg=self.colors['card'], relief="flat", bd=0)
        video_card.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        video_card.grid_rowconfigure(1, weight=1)
        video_card.grid_columnconfigure(0, weight=1)
        
        # Video card header
        video_header = tk.Frame(video_card, bg=self.colors['card'], height=50)
        video_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 0))
        video_header.grid_columnconfigure(0, weight=1)
        
        video_title = tk.Label(video_header, text="Camera Preview", 
                              font=("Segoe UI", 16, "bold"), 
                              fg=self.colors['text_primary'], 
                              bg=self.colors['card'])
        video_title.grid(row=0, column=0, sticky="w")
        
        # Video display area
        video_frame = tk.Frame(video_card, bg=self.colors['card'], 
                              relief="flat", bd=0)
        video_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 20))
        
        self.video_label = tk.Label(video_frame, text="Camera not started", 
                                   background="#0a0a0a", foreground="#ffffff", 
                                   font=("Segoe UI", 12), width=80, height=30)
        self.video_label.pack(expand=True, fill="both", padx=2, pady=2)
        
        # Right side - Control cards
        right_panel = tk.Frame(main_content, bg=self.colors['background'])
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)
        
        # Quick Actions Card
        actions_card = tk.Frame(right_panel, bg=self.colors['card'], relief="flat", bd=0)
        actions_card.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        actions_card.grid_columnconfigure(0, weight=1)
        
        # Actions content
        actions_content = tk.Frame(actions_card, bg=self.colors['card'])
        actions_content.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 20))
        actions_content.grid_columnconfigure(0, weight=1)
        
        # Modern rounded button with drop shadow using Canvas
        def create_action_button(parent, text, command, row, bg_color=None, fg_color='#ffffff'):
            if bg_color is None:
                bg_color = self.colors['primary']
            app_self = self  # capture outer self for use inside inner class

            class _CanvasRoundedButton:
                # Draw a rounded rectangle path on canvas
                def __init__(self, master, text_value, on_click, background_color, foreground_color):
                    self.master = master
                    self.text_value = text_value
                    self.on_click = on_click
                    self.background_color = background_color
                    self.foreground_color = foreground_color
                    self.state = tk.NORMAL
                    self.is_hovered = False

                    self.container = tk.Frame(master, bg=app_self.colors['card'])
                    self.canvas = tk.Canvas(self.container, height=48, bg=app_self.colors['card'], bd=0, highlightthickness=0, relief='flat')
                    self.canvas.pack(fill='x', expand=True)

                    self.radius = 12
                    self.padding_x = 4
                    self.padding_y = 4
                    self.shadow_offset = 3

                    self._draw_button(self.background_color, self.foreground_color)

                    self.canvas.bind('<Button-1>', self._handle_click)
                    self.canvas.bind('<Enter>', self._on_enter)
                    self.canvas.bind('<Leave>', self._on_leave)
                    self.container.bind('<Enter>', self._on_enter)
                    self.container.bind('<Leave>', self._on_leave)
                    self.container.config(cursor='hand2')

                def _rounded_rect_path(self, x1, y1, x2, y2, r):
                    points = [
                        x1+r, y1,
                        x2-r, y1,
                        x2, y1,
                        x2, y1+r,
                        x2, y2-r,
                        x2, y2,
                        x2-r, y2,
                        x1+r, y2,
                        x1, y2,
                        x1, y2-r,
                        x1, y1+r,
                        x1, y1
                    ]
                    return points

                def _draw_button(self, bg, fg):
                    self.canvas.delete('all')
                    width = self.canvas.winfo_width() or self.container.winfo_width() or 200
                    if width < 120:
                        width = 200
                    height = 40

                    x1 = self.padding_x
                    y1 = self.padding_y
                    x2 = width - self.padding_x
                    y2 = height + self.padding_y

                    # Shadow (stronger on hover)
                    self.shadow_offset = 5 if self.is_hovered else 3
                    shadow_color = '#7ea6ff' if self.is_hovered else '#a3bffa'
                    self.canvas.create_polygon(
                        self._rounded_rect_path(x1+self.shadow_offset, y1+self.shadow_offset, x2+self.shadow_offset, y2+self.shadow_offset, self.radius),
                        smooth=True, fill=shadow_color, outline=''
                    )

                    # Main rounded rect
                    self.canvas.create_polygon(
                        self._rounded_rect_path(x1, y1, x2, y2, self.radius),
                        smooth=True, fill=bg, outline=''
                    )

                    # Text
                    self.text_id = self.canvas.create_text((x1+x2)//2, (y1+y2)//2, text=self.text_value, fill=fg, font=("Segoe UI", 11, "bold"))

                    # Resize handling
                    self.canvas.bind('<Configure>', lambda e: self._draw_button(self.background_color, self.foreground_color))

                def _handle_click(self, _event):
                    if self.state == tk.NORMAL and callable(self.on_click):
                        self.on_click()

                def _on_enter(self, _event):
                    if self.state == tk.NORMAL:
                        self.is_hovered = True
                        self._draw_button(self._hover_color(self.background_color), self.foreground_color)

                def _on_leave(self, _event):
                    if self.state == tk.NORMAL:
                        self.is_hovered = False
                        self._draw_button(self.background_color, self.foreground_color)

                def _hover_color(self, color_hex):
                    # lighten color slightly
                    try:
                        r = int(color_hex[1:3], 16)
                        g = int(color_hex[3:5], 16)
                        b = int(color_hex[5:7], 16)
                        r = min(255, int(r + (255 - r) * 0.08))
                        g = min(255, int(g + (255 - g) * 0.08))
                        b = min(255, int(b + (255 - b) * 0.08))
                        return f'#{r:02x}{g:02x}{b:02x}'
                    except Exception:
                        return color_hex

                def grid(self, **kwargs):
                    self.container.grid(**kwargs)

                def pack(self, **kwargs):
                    self.container.pack(**kwargs)

                def place(self, **kwargs):
                    self.container.place(**kwargs)

                def config(self, **kwargs):
                    # Support bg, fg, state
                    bg = kwargs.get('bg') or kwargs.get('background')
                    fg = kwargs.get('fg') or kwargs.get('foreground')
                    state = kwargs.get('state')
                    if bg:
                        self.background_color = bg
                    if fg:
                        self.foreground_color = fg
                    if state is not None:
                        self.state = state
                        if self.state == tk.DISABLED:
                            disabled_bg = '#94a3b8'
                            disabled_fg = '#ffffff'
                            self._draw_button(disabled_bg, disabled_fg)
                            return
                    self._draw_button(self.background_color, self.foreground_color)

                def __setitem__(self, key, value):
                    if key == 'state':
                        self.config(state=value)
                    else:
                        # ignore unsupported for now
                        pass

            widget = _CanvasRoundedButton(parent, text, command, bg_color, fg_color)
            widget.grid(row=row, column=0, sticky='ew', pady=6, padx=0)
            return widget
        
        # Create rounded card frame
        def create_rounded_card(parent, row, column, sticky="ew", pady=0, padx=0):
            card = tk.Frame(parent, bg=self.colors['card'], relief="flat", bd=0)
            card.grid(row=row, column=column, sticky=sticky, pady=pady, padx=padx)
            return card
        
        self.btn_register = create_action_button(actions_content, "👤 Register Face", 
                                                self.register_flow, 0, 
                                                self.colors['accent_pink'], '#ffffff')
        
        self.btn_start = create_action_button(actions_content, "▶️ Start Attendance", 
                                             self.start_scan, 1, 
                                             self.colors['success'], '#ffffff')
        
        self.btn_stop = create_action_button(actions_content, "⏹️ Stop Attendance", 
                                            self.stop_scan, 2, 
                                            self.colors['danger'], '#ffffff')  # Red background, white text
        self.btn_stop.config(state=tk.DISABLED, bg='#6c757d', fg='#ffffff')  # Gray when disabled
        
        # Stats Card
        stats_card = tk.Frame(right_panel, bg=self.colors['card'], relief="flat", bd=0)
        stats_card.grid(row=1, column=0, sticky="nsew", pady=(0, 15))
        stats_card.grid_rowconfigure(1, weight=1)
        stats_card.grid_columnconfigure(0, weight=1)
        
        # Stats content
        stats_content = tk.Frame(stats_card, bg=self.colors['card'])
        stats_content.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 20))
        stats_content.grid_rowconfigure(1, weight=1)
        stats_content.grid_columnconfigure(0, weight=1)
        
        # Stats buttons
        stats_btn_frame = tk.Frame(stats_content, bg=self.colors['card'])
        stats_btn_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        stats_btn_frame.grid_columnconfigure(0, weight=1)
        
        self.btn_stats = create_action_button(stats_btn_frame, "📊 View Statistics", 
                                             self.show_stats, 0, 
                                             self.colors['surface_light'], self.colors['text_primary'])
        
        self.btn_users = create_action_button(stats_btn_frame, "👥 Manage Users", 
                                             self.show_user_list, 1, 
                                             self.colors['surface_light'], self.colors['text_primary'])
        
        self.btn_report = create_action_button(stats_btn_frame, "📈 Create Report", 
                                              self.show_attendance_report, 2, 
                                              self.colors['surface_light'], self.colors['text_primary'])
        
        # Attendance list
        attendance_frame = tk.Frame(stats_content, bg=self.colors['card'])
        attendance_frame.grid(row=1, column=0, sticky="nsew")
        attendance_frame.grid_rowconfigure(1, weight=1)
        attendance_frame.grid_columnconfigure(0, weight=1)
        
        attendance_label = tk.Label(attendance_frame, text="Today's Attendance", 
                                   font=("Segoe UI", 12, "bold"), 
                                   fg=self.colors['text_primary'], 
                                   bg=self.colors['card'])
        attendance_label.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        self.attendance_listbox = tk.Listbox(attendance_frame, height=6, 
                                            font=("Segoe UI", 10),
                                            bg=self.colors['surface_light'],
                                            fg=self.colors['text_primary'],
                                            selectbackground=self.colors['primary'],
                                            selectforeground='#ffffff',
                                            relief="flat", bd=0)
        self.attendance_listbox.grid(row=1, column=0, sticky="nsew")
        
        
        # Auto-stop checkbox
        auto_stop_frame = tk.Frame(right_panel, bg=self.colors['background'])
        auto_stop_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))
        
        self.auto_stop_var = tk.BooleanVar(value=True)
        self.auto_stop_check = tk.Checkbutton(auto_stop_frame, 
                                             text="Auto-stop after 5s of inactivity",
                                             variable=self.auto_stop_var,
                                             command=self._toggle_auto_stop,
                                             font=("Segoe UI", 10),
                                             fg=self.colors['text_secondary'],
                                             bg=self.colors['background'],
                                             selectcolor=self.colors['primary'],
                                             activebackground=self.colors['background'],
                                             activeforeground=self.colors['text_primary'])
        self.auto_stop_check.pack(anchor="w")
        
        self.cap = None
        self.running = False
        self.engine = None
        self.reg = Registry()
        self.cooldown = CooldownKeeper(ATTEND_COOLDOWN_SEC)
        self._last_state = {}  # name -> last status (IN/OUT)
        self._last_seen = {}  # name -> timestamp when last seen
        
        # Auto-stop variables
        self.auto_stop_enabled = True
        self.auto_stop_timeout = 5  # seconds of inactivity before auto-stop
        self.last_activity_time = time.time()
        self.auto_stop_timer = None
        
        # System ready
        print("System ready!")
        print("Click 'Register Face' to add new users")
        print("Click 'Start Attendance' to begin scanning")
        print("Rule: Alternating IN -> OUT -> IN -> OUT...")
        print(f"Cooldown between scans: {ATTEND_COOLDOWN_SEC} seconds")
        print("Auto-stop after 5 seconds of inactivity")
        
        # Initialize attendance display
        self._update_attendance_display()

    def _switch_navigation(self, nav_key):
        """Switch between navigation sections"""
        self.current_nav = nav_key
        self._highlight_nav_button(nav_key)
        
        # Update header title
        titles = {
            "dashboard": "Dashboard",
            "users": "User Management", 
            "reports": "Reports & Statistics"
        }
        
        # Find and update header title
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Frame):
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, tk.Label) and grandchild.cget("text") in ["Dashboard", "User Management", "Reports & Analytics", "Settings"]:
                                grandchild.config(text=titles[nav_key])
                                break
        
        # Show appropriate content based on navigation
        if nav_key == "dashboard":
            print(f"Switched to {titles[nav_key]}")
        elif nav_key == "users":
            self.show_user_list()
        elif nav_key == "reports":
            self.show_attendance_report()

    def _highlight_nav_button(self, active_key):
        """Highlight the active navigation button"""
        for key, btn in self.nav_buttons.items():
            if key == active_key:
                btn.config(bg=self.colors['accent_teal'], fg='#ffffff')
            else:
                btn.config(bg=self.colors['sidebar'], fg=self.colors['text_secondary'])

    def _toggle_auto_stop(self):
        """Toggle auto-stop feature"""
        self.auto_stop_enabled = self.auto_stop_var.get()
        if self.auto_stop_enabled:
            print("OK: Auto-stop enabled after 5s of inactivity")
        else:
            print("OFF: Auto-stop disabled")
            if self.auto_stop_timer:
                self.root.after_cancel(self.auto_stop_timer)
                self.auto_stop_timer = None


    def _update_attendance_display(self):
        """Update the attendance display with current day's data"""
        # Clear current display
        self.attendance_listbox.delete(0, tk.END)
        
        # Get attendance stats
        user_stats = user_attendance_stats()
        
        if not user_stats:
            self.attendance_listbox.insert(tk.END, "Chưa có điểm danh nào hôm nay")
            return
        
        # Sort users by total attendance (descending)
        sorted_users = sorted(user_stats.items(), key=lambda x: x[1]['total'], reverse=True)
        
        # Add header
        self.attendance_listbox.insert(tk.END, "User Name     IN  OUT  Total")
        self.attendance_listbox.insert(tk.END, "─" * 30)
        
        # Add user data
        for name, stats in sorted_users:
            display_name = name.replace("_", " ").title()
            # Format with balanced spacing
            line = f"{display_name:<15} {stats['in']:>2}  {stats['out']:>2}  {stats['total']:>3}"
            self.attendance_listbox.insert(tk.END, line)

    def ensure_engine(self):
        if self.engine is None:
            self.status["text"] = "Initializing model..."
            self.status["fg"] = self.colors['warning']
            print("Initializing AI model... (first time may take a while)")
            self.root.update_idletasks()
            self.engine = FaceEngine()
            self.status["text"] = "Ready"
            self.status["fg"] = self.colors['success']
            print("AI model ready!")

    def open_cam(self):
        if self.cap is None:
            print("Connecting to camera...")
            self.cap = cv2.VideoCapture(CAM_INDEX)
            if not self.cap.isOpened():
                self.cap.release()
                self.cap = None
                print("ERROR: Cannot connect to camera!")
                raise RuntimeError("Không mở được webcam.")
            print("Camera connected successfully!")

    def close_cam(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            print("CAM: Camera turned off")

    def register_flow(self):
        name = simpledialog.askstring("Register Face", 
                                    "Enter full name to register:", 
                                    parent=self.root)
        if not name:
            return
            
        # Check existing user before proceeding
        normalized = name.strip().replace(" ", "_")
        existing_users = [u.lower() for u in self.reg.list_people()]
        if normalized.lower() in existing_users:
            display_name = normalized.replace("_", " ").title()
            messagebox.showwarning("Cảnh báo", f"Người dùng '{display_name}' đã tồn tại.")
            return

        print(f"Starting registration for: {name}")
        
        try:
            self.ensure_engine()
            self.open_cam()
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))
            print(f"ERROR during initialization: {str(e)}")
            return

        # Create modern registration window
        reg_window = tk.Toplevel(self.root)
        reg_window.title(f"Register Face - {name}")
        reg_window.geometry("900x700")
        reg_window.configure(bg='#f0f0f0')
        reg_window.resizable(False, False)
        
        # Center the window
        reg_window.transient(self.root)
        reg_window.grab_set()
        
        # Main container
        main_frame = ttk.Frame(reg_window, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 20))
        
        title_label = ttk.Label(title_frame, text=f"Register face for: {name}", 
                               font=("Arial", 16, "bold"))
        title_label.pack()
        
        # Content area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True)
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=2)
        content_frame.grid_columnconfigure(1, weight=1)
        
        # Video preview area
        video_frame = ttk.LabelFrame(content_frame, text="Camera Preview", padding="10")
        video_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        
        video_label = tk.Label(video_frame, text="Đang tải camera...", 
                              background="black", foreground="white", width=80, height=30)
        video_label.pack(expand=True, fill="both")
        
        # Control panel
        control_frame = ttk.LabelFrame(content_frame, text="Điều khiển", padding="15")
        control_frame.grid(row=0, column=1, sticky="nsew")
        
        # Instructions
        instruction_frame = ttk.Frame(control_frame)
        instruction_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(instruction_frame, text="Hướng dẫn:", font=("Arial", 10, "bold")).pack(anchor="w")
        instructions = [
            "• Nhìn thẳng vào camera",
            "• Đảm bảo ánh sáng đủ",
            "• Giữ khuôn mặt trong khung",
            "• Nhấn 'Bắt đầu đăng ký'",
            "• Tự động chụp sau 5 giây"
        ]
        
        for instruction in instructions:
            ttk.Label(instruction_frame, text=instruction, font=("Arial", 9)).pack(anchor="w", pady=1)
        
        # Countdown display
        countdown_frame = ttk.Frame(control_frame)
        countdown_frame.pack(fill="x", pady=(0, 15))
        
        self.countdown_label = ttk.Label(countdown_frame, text="", 
                                        font=("Arial", 24, "bold"), 
                                        foreground="red")
        self.countdown_label.pack()
        
        # Buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill="x", pady=15)
        
        self.capture_btn = ttk.Button(button_frame, text="📸 Bắt đầu đăng ký", 
                                     command=lambda: self._start_auto_capture(name, reg_window),
                                     width=20)
        self.capture_btn.pack(fill="x", pady=5)
        
        close_btn = ttk.Button(button_frame, text="❌ Đóng", 
                              command=lambda: self._close_registration(reg_window),
                              width=20)
        close_btn.pack(fill="x", pady=5)
        
        # Status for registration
        self.reg_status = ttk.Label(control_frame, text="Ready to register", 
                                   foreground="green", font=("Arial", 9))
        self.reg_status.pack(pady=(10, 0))
        
        # Auto capture variables
        self.auto_capturing = False
        self.capture_countdown = 0
        
        # Start video preview
        self._register_preview_loop(reg_window, video_label)

    def _register_preview_loop(self, reg_window, video_label):
        """Preview video in registration window"""
        if not reg_window.winfo_exists():
            return
            
        ok, frame = self.cap.read()
        if ok:
            # Resize frame to fixed display size
            display_width = 640
            display_height = 480
            frame = cv2.resize(frame, (display_width, display_height))
            
            # Convert to RGB and display
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            video_label.imgtk = imgtk
            video_label.configure(image=imgtk)
        
        # Schedule next frame
        reg_window.after(30, lambda: self._register_preview_loop(reg_window, video_label))

    def _start_auto_capture(self, name, reg_window):
        """Start automatic capture with countdown"""
        if self.auto_capturing:
            return
            
        self.auto_capturing = True
        self.capture_countdown = 5
        self.capture_btn["state"] = tk.DISABLED
        self.reg_status["text"] = "Chuẩn bị chụp ảnh..."
        self.reg_status["foreground"] = "orange"
        
        # Start countdown
        self._countdown_capture(name, reg_window)

    def _countdown_capture(self, name, reg_window):
        """Handle countdown and auto capture"""
        if not reg_window.winfo_exists() or not self.auto_capturing:
            return
            
        if self.capture_countdown > 0:
            self.countdown_label["text"] = str(self.capture_countdown)
            self.capture_countdown -= 1
            reg_window.after(1000, lambda: self._countdown_capture(name, reg_window))
        else:
            # Time to capture
            self.countdown_label["text"] = "CHỤP!"
            self._auto_capture_face(name, reg_window)

    def _auto_capture_face(self, name, reg_window):
        """Automatically capture face"""
        self.reg_status["text"] = "Đang chụp ảnh..."
        self.reg_status["foreground"] = "orange"
        reg_window.update()
        
        ok, frame = self.cap.read()
        if not ok:
            self.reg_status["text"] = "Lỗi camera"
            self.reg_status["foreground"] = "red"
            self.countdown_label["text"] = "LỖI"
            self._reset_capture_ui(reg_window)
            return
            
        emb, bbox = self.engine.embed_crop(frame)
        if emb is None:
            self.reg_status["text"] = "Không thấy khuôn mặt"
            self.reg_status["foreground"] = "red"
            self.countdown_label["text"] = "KHÔNG THẤY KHUÔN MẶT"
            self._reset_capture_ui(reg_window)
            return
            
        # Success
        self.reg.add_sample(name, emb, frame)
        self.reg_status["text"] = "Saved successfully!"
        self.reg_status["foreground"] = "green"
        self.countdown_label["text"] = "SUCCESS!"
        self.countdown_label["foreground"] = "green"
        print(f"Auto-saved face sample for {name}")
        
        # Reset after 2 seconds
        reg_window.after(2000, lambda: self._reset_capture_ui(reg_window))

    def _reset_capture_ui(self, reg_window):
        """Reset capture UI to initial state"""
        if not reg_window.winfo_exists():
            return
            
        self.auto_capturing = False
        self.capture_countdown = 0
        self.capture_btn["state"] = tk.NORMAL
        self.countdown_label["text"] = ""
        self.countdown_label["foreground"] = "red"
        self.reg_status["text"] = "Ready to register"
        self.reg_status["foreground"] = "green"

    def _capture_face(self, name, reg_window):
        """Capture face for registration"""
        self.reg_status["text"] = "Processing..."
        self.reg_status["foreground"] = "orange"
        reg_window.update()
        
        ok, frame = self.cap.read()
        if not ok:
            self.reg_status["text"] = "Lỗi camera"
            self.reg_status["foreground"] = "red"
            messagebox.showerror("Lỗi", "Không thể đọc từ camera")
            return
            
        emb, bbox = self.engine.embed_crop(frame)
        if emb is None:
            self.reg_status["text"] = "Không thấy khuôn mặt"
            self.reg_status["foreground"] = "red"
            messagebox.showwarning("Cảnh báo", "Không thấy khuôn mặt đủ lớn. Thử lại.")
            return
            
        self.reg.add_sample(name, emb, frame)
        self.reg_status["text"] = "Saved successfully!"
        self.reg_status["foreground"] = "green"
        print(f"Saved face sample for {name}")
        messagebox.showinfo("Thành công", f"Đã lưu mẫu cho {name}!\nCó thể chụp thêm để tăng độ chính xác.")

    def _close_registration(self, reg_window):
        """Close registration window and release camera"""
        reg_window.destroy()
        self.close_cam()

    def start_scan(self):
        try:
            self.ensure_engine()
            self.open_cam()
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))
            print(f"ERROR starting scan: {str(e)}")
            return
            
        self.running = True
        self.btn_start["state"] = tk.DISABLED
        self.btn_start.config(bg=self.colors['accent_orange'], fg='#ffffff')
        self.btn_stop["state"] = tk.NORMAL
        self.btn_stop.config(bg=self.colors['danger'], fg='#ffffff')  # Red when active
        self.status["text"] = "Scanning..."
        self.status["fg"] = self.colors['primary']
        self.last_activity_time = time.time()
        
        # Reset attendance state for new scan session
        self._last_state = {}
        self._last_seen = {}
        
        print("SCAN: Starting automatic face scanning...")
        print("System will automatically recognize and mark attendance")
        
        # Clear any previous text and prepare for video
        self.video_label.configure(text="")
        
        # Start auto-stop timer if enabled
        if self.auto_stop_enabled:
            self._start_auto_stop_timer()
            
        threading.Thread(target=self._scan_loop, daemon=True).start()

    def stop_scan(self):
        self.running = False
        self.btn_start["state"] = tk.NORMAL
        self.btn_start.config(bg=self.colors['success'], fg='#ffffff')
        self.btn_stop["state"] = tk.DISABLED
        self.btn_stop.config(bg='#6c757d', fg='#ffffff')  # Gray when disabled
        self.status["text"] = "Đã dừng"
        self.status["fg"] = self.colors['warning']
        
        # Cancel auto-stop timer
        if self.auto_stop_timer:
            self.root.after_cancel(self.auto_stop_timer)
            self.auto_stop_timer = None
            
        print("STOP: Face scanning stopped")
        print("System has paused automatic attendance")

    def _start_auto_stop_timer(self):
        """Start auto-stop timer"""
        if self.auto_stop_timer:
            self.root.after_cancel(self.auto_stop_timer)
        
        self.auto_stop_timer = self.root.after(self.auto_stop_timeout * 1000, self._check_auto_stop)

    def _check_auto_stop(self):
        """Check if should auto-stop due to inactivity"""
        if not self.running or not self.auto_stop_enabled:
            return
            
        current_time = time.time()
        inactive_time = current_time - self.last_activity_time
        
        if inactive_time >= self.auto_stop_timeout:
            print(f"TIMER: Auto-stop after {self.auto_stop_timeout}s of inactivity")
            self._auto_stop_attendance()
        else:
            # Check again in 1 second
            remaining = self.auto_stop_timeout - inactive_time
            self.auto_stop_timer = self.root.after(1000, self._check_auto_stop)

    def _auto_stop_attendance(self):
        """Automatically stop attendance"""
        if self.running:
            self.running = False
            self.btn_start["state"] = tk.NORMAL
            self.btn_start.config(bg=self.colors['success'])
            self.btn_stop["state"] = tk.DISABLED
            self.btn_stop.config(bg=self.colors['secondary'])
            self.status["text"] = "Auto-stop"
            self.status["fg"] = self.colors['warning']
            
            if self.auto_stop_timer:
                self.root.after_cancel(self.auto_stop_timer)
                self.auto_stop_timer = None
                
            print("AUTO: System auto-stopped and turned off camera")

    def _scan_loop(self):
        last = 0.0
        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                self.status["text"] = "Mất tín hiệu camera"
                self.status["fg"] = self.colors['danger']
                print("Camera signal lost!")
                break
            now = time.time()
            if now - last < 1.0 / max(1, FPS_LIMIT):
                time.sleep(0.001)
                continue
            last = now

            # Resize frame to fixed display size
            display_width = 640
            display_height = 480
            frame = cv2.resize(frame, (display_width, display_height))

            dets = self.engine.detect_and_embed(frame)
            display = frame.copy()
            info = ""
            current_time = time.time()
            
            # Track who is currently seen
            currently_seen = set()
            
            for bbox, kps, score, emb in dets:
                name, sim = self.reg.match(emb)
                if name:
                    # Track that this person is currently seen
                    currently_seen.add(name)
                    self._last_seen[name] = current_time
                    
                    # Check if person can attend today
                    can_attend, limit_message = can_attend_today(name)
                    
                    if not can_attend:
                        # Show popup notification for daily limit
                        messagebox.showinfo("Thông báo", f"{name}: {limit_message}")
                        info = f"{name} - Đã đủ điểm danh hôm nay"
                        print(f"WARN: {name} has already attended today")
                    elif self.cooldown.ready(name):
                        # Alternating logic based on actual attendance history: IN → OUT → IN → OUT → ...
                        last_attendance = self._get_last_attendance_status(name)
                        if last_attendance == "IN":
                            new_state = "OUT"  # Last was IN, next should be OUT
                        else:
                            new_state = "IN"   # Last was OUT or no history, next should be IN
                        
                        # Only log ONCE per scan session (per button press)
                        if name not in self._last_state:
                            log_event(name, new_state)
                            self._last_state[name] = new_state
                            info = f"{name} -> {new_state} (sim={sim:.2f})"
                            
                            # Reset auto-stop timer on activity
                            self.last_activity_time = time.time()
                            if self.auto_stop_enabled and self.auto_stop_timer:
                                self._start_auto_stop_timer()
                            
                            # Enhanced notification
                            if new_state == "IN":
                                print(f"IN: {name} checked in (confidence: {sim:.2f})")
                            else:
                                print(f"OUT: {name} checked out (confidence: {sim:.2f})")
                            
                            # Update attendance display
                            self._update_attendance_display()
                            
                            # Refresh attendance report if it's open
                            self._refresh_attendance_report()
                        else:
                            info = f"{name} - {self._last_state[name]} (sim={sim:.2f})"
                    else:
                        info = f"{name} (sim={sim:.2f}) - Chờ cooldown"
                        
                    # Draw bounding box with status
                    self.engine.draw_bbox(display, bbox, name, sim)
                else:
                    self.engine.draw_bbox(display, bbox, "Unknown", None)
            
            # Clear state for people not seen for more than 3 seconds
            for name in list(self._last_seen.keys()):
                if name not in currently_seen and current_time - self._last_seen[name] > 3:
                    # Clear their state so they can be recognized again
                    if name in self._last_state:
                        del self._last_state[name]
                    del self._last_seen[name]

            # Show to Tk only if still running
            if self.running:
                rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
                if not info:
                    self.status["text"] = "Scanning..."
                    self.status["fg"] = self.colors['primary']
        
        # Clear video display when loop ends
        self.video_label.configure(image="", text="Camera stopped")
        self.close_cam()

    def show_stats(self):
        s = daily_stats()
        messagebox.showinfo("Today's Statistics",
                            f"Total records: {s['count']}\n"
                            f"Check-ins: {s['in']}\n"
                            f"Check-outs: {s['out']}\n"
                            f"Unique people: {s['unique']}")

    def show_user_list(self):
        """Show list of registered users"""
        users = self.reg.list_people()
        
        if not users:
            messagebox.showinfo("User List", "No users have been registered yet.")
            return
        
        # Create user list window (unified theme)
        user_window = tk.Toplevel(self.root)
        user_window.title("Registered Users List")
        user_window.geometry("640x520")
        user_window.configure(bg=self.colors['background'])
        user_window.resizable(False, False)

        user_window.transient(self.root)
        user_window.grab_set()

        # Title area
        header = tk.Frame(user_window, bg=self.colors['surface'])
        header.pack(fill="x", padx=16, pady=(16, 8))
        tk.Label(header, text="Registered Users List", font=("Segoe UI", 16, "bold"),
                 fg=self.colors['text_primary'], bg=self.colors['surface']).pack(anchor='w')
        tk.Label(header, text=f"Total: {len(users)} people", font=("Segoe UI", 11),
                 fg=self.colors['text_secondary'], bg=self.colors['surface']).pack(anchor='w')

        # Body
        body = tk.Frame(user_window, bg=self.colors['background'])
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        list_frame = tk.Frame(body, bg=self.colors['card'])
        list_frame.pack(fill="both", expand=True)

        self.user_listbox = tk.Listbox(list_frame, font=("Segoe UI", 11), height=14,
                                       bg=self.colors['surface_light'], fg=self.colors['text_primary'],
                                       selectbackground=self.colors['primary'], selectforeground='#ffffff',
                                       relief='flat', bd=0)
        self.user_listbox.pack(side="left", fill="both", expand=True, padx=(8,0), pady=8)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.user_listbox.yview)
        scrollbar.pack(side="right", fill="y", padx=(0,8), pady=8)
        self.user_listbox.configure(yscrollcommand=scrollbar.set)

        for i, user in enumerate(users, 1):
            display_name = user.replace("_", " ").title()
            self.user_listbox.insert(tk.END, f"{i:2d}. {display_name}")

        # Local rounded button factory for this window
        app_self = self
        def create_modal_button(parent, text, command, side='left'):
            class _Btn:
                def __init__(self, master, title, cb):
                    self.state = tk.NORMAL
                    self.bg = app_self.colors['primary']
                    self.fg = '#ffffff'
                    self.container = tk.Frame(master, bg=app_self.colors['background'])
                    self.canvas = tk.Canvas(self.container, height=40, bg=app_self.colors['background'], bd=0, highlightthickness=0)
                    self.canvas.pack()
                    self.title = title
                    self.cb = cb
                    self.radius = 10
                    self._draw(self.bg, self.fg)
                    self.canvas.bind('<Button-1>', lambda _e: self.cb() if self.state==tk.NORMAL else None)
                    self.canvas.bind('<Enter>', lambda _e: self._draw(self._hover(self.bg), self.fg) if self.state==tk.NORMAL else None)
                    self.canvas.bind('<Leave>', lambda _e: self._draw(self.bg, self.fg) if self.state==tk.NORMAL else None)
                def _path(self, x1,y1,x2,y2,r):
                    return [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2, x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
                def _draw(self, bg, fg):
                    self.canvas.delete('all')
                    w = 180
                    h = 36
                    x1,y1=4,4
                    x2,y2=w-4,h
                    self.canvas.create_polygon(self._path(x1+2,y1+2,x2+2,y2+2,self.radius), smooth=True, fill='#a3bffa', outline='')
                    self.canvas.create_polygon(self._path(x1,y1,x2,y2,self.radius), smooth=True, fill=bg, outline='')
                    self.canvas.create_text((x1+x2)//2,(y1+y2)//2, text=self.title, fill=fg, font=("Segoe UI", 10, "bold"))
                def _hover(self, c):
                    r=int(c[1:3],16); g=int(c[3:5],16); b=int(c[5:7],16)
                    r=min(255,int(r+(255-r)*0.08)); g=min(255,int(g+(255-g)*0.08)); b=min(255,int(b+(255-b)*0.08))
                    return f'#{r:02x}{g:02x}{b:02x}'
                def pack(self, **kwargs):
                    self.container.pack(**kwargs)
                def grid(self, **kwargs):
                    self.container.grid(**kwargs)
            w = _Btn(parent, text, command)
            if side=='left':
                w.pack(side='left', padx=6)
            else:
                w.pack(side='right', padx=6)
            return w

        # Buttons row
        footer = tk.Frame(body, bg=self.colors['background'])
        footer.pack(fill='x', pady=(12,0))
        create_modal_button(footer, 'View Details', lambda: self._view_user_details(user_window), side='left')
        create_modal_button(footer, 'Delete User', lambda: self._delete_user(user_window), side='left')
        create_modal_button(footer, 'Close', user_window.destroy, side='right')

        self.user_listbox.bind('<<ListboxSelect>>', lambda e: self._on_user_select())

        print(f"Displaying list of {len(users)} registered users")

    def _on_user_select(self):
        """Handle user selection in listbox"""
        selection = self.user_listbox.curselection()
        if selection:
            index = selection[0]
            # You can add additional logic here if needed
            pass

    def _view_user_details(self, parent_window):
        """View details of selected user"""
        selection = self.user_listbox.curselection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một người dùng để xem chi tiết.")
            return
        
        index = selection[0]
        users = self.reg.list_people()
        if index >= len(users):
            return
            
        user = users[index]
        display_name = user.replace("_", " ").title()
        
        # Get user data
        embed_file = self.reg._embed_file(user)
        if embed_file.exists():
            data = np.load(embed_file)
            vecs = data['vecs']
            num_samples = len(vecs)
        else:
            num_samples = 0
        
        # Count face images
        person_dir = Path("faces") / user
        if person_dir.exists():
            num_images = len(list(person_dir.glob("*.jpg")))
        else:
            num_images = 0
        
        # Show details
        details = f"Tên: {display_name}\n"
        details += f"Số mẫu khuôn mặt: {num_samples}\n"
        details += f"Số ảnh đã lưu: {num_images}\n"
        details += f"Trạng thái: {'Đã đăng ký' if num_samples > 0 else 'Chưa có mẫu'}"
        
        messagebox.showinfo(f"Chi tiết - {display_name}", details)

    def _delete_user(self, parent_window):
        """Delete selected user"""
        selection = self.user_listbox.curselection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một người dùng để xóa.")
            return
        
        index = selection[0]
        users = self.reg.list_people()
        if index >= len(users):
            return
            
        user = users[index]
        display_name = user.replace("_", " ").title()
        
        # Confirm deletion
        result = messagebox.askyesno("Xác nhận xóa", 
                                   f"Bạn có chắc chắn muốn xóa người dùng '{display_name}'?\n\n"
                                   f"Thao tác này sẽ xóa:\n"
                                   f"- Tất cả mẫu khuôn mặt\n"
                                   f"- Tất cả ảnh đã lưu\n"
                                   f"- Không thể hoàn tác!")
        
        if result:
            try:
                # Delete embedding file
                embed_file = self.reg._embed_file(user)
                if embed_file.exists():
                    embed_file.unlink()
                
                # Delete face images directory
                person_dir = Path("faces") / user
                if person_dir.exists():
                    shutil.rmtree(person_dir)
                
                print(f"Deleted user: {display_name}")
                messagebox.showinfo("Thành công", f"Đã xóa người dùng '{display_name}' thành công!")
                
                # Refresh the list
                parent_window.destroy()
                self.show_user_list()
                
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể xóa người dùng: {str(e)}")

    def show_attendance_report(self):
        """Show detailed attendance report window"""
        report_window = tk.Toplevel(self.root)
        report_window.title("Detailed Attendance Report")
        report_window.geometry("900x620")
        report_window.resizable(True, True)
        report_window.configure(bg=self.colors['background'])

        # Title area
        header = tk.Frame(report_window, bg=self.colors['surface'])
        header.pack(fill='x', padx=16, pady=(16,8))
        tk.Label(header, text="Detailed Attendance Report", font=("Segoe UI", 16, "bold"),
                 fg=self.colors['text_primary'], bg=self.colors['surface']).pack(anchor='w')

        # Action row with unified buttons
        actions = tk.Frame(report_window, bg=self.colors['background'])
        actions.pack(fill='x', padx=16, pady=(0,8))

        # Date control only
        controls = tk.Frame(actions, bg=self.colors['background'])
        controls.pack(side='left')

        # Date selector (DateTimePicker if available; fallback to combobox)
        tk.Label(controls, text="Date:", font=("Segoe UI", 10), fg=self.colors['text_secondary'], bg=self.colors['background']).pack(side='left', padx=(0,6))
        self.report_date_var = tk.StringVar(value="")
        self.report_date_combo = None
        self.report_date_picker = None
        try:
            from tkcalendar import DateEntry  # type: ignore
            self.report_date_picker = DateEntry(controls, date_pattern='dd/mm/yyyy', width=12)
            self.report_date_picker.pack(side='left', padx=(0,12))
            # Comment: Bind date selected event for DateEntry
            self.report_date_picker.bind('<<DateEntrySelected>>', lambda _e: self._on_report_date_change())
        except Exception:
            # Fallback to combobox with available dates
            self.report_date_combo = ttk.Combobox(controls, textvariable=self.report_date_var, values=[], state="readonly", width=12)
            self.report_date_combo.pack(side='left', padx=(0,12))
            self.report_date_combo.bind('<<ComboboxSelected>>', lambda _e: self._on_report_date_change())

        # Username filter
        tk.Label(controls, text="User:", font=("Segoe UI", 10), fg=self.colors['text_secondary'], bg=self.colors['background']).pack(side='left', padx=(0,6))
        self.report_user_var = tk.StringVar(value="")
        self.report_user_entry = ttk.Entry(controls, textvariable=self.report_user_var, width=18)
        self.report_user_entry.pack(side='left', padx=(0,12))
        # Comment: Update table on typing username
        self.report_user_entry.bind('<KeyRelease>', lambda _e: self._on_report_date_change())

        # Local rounded button creator
        app_self = self
        def create_modal_button(parent, text, command, side='left'):
            class _Btn:
                def __init__(self, master, title, cb, bg):
                    self.state = tk.NORMAL
                    self.bg = bg
                    self.fg = '#ffffff' if bg != app_self.colors['surface_light'] else app_self.colors['text_primary']
                    self.container = tk.Frame(master, bg=app_self.colors['background'])
                    self.canvas = tk.Canvas(self.container, height=40, bg=app_self.colors['background'], bd=0, highlightthickness=0)
                    self.canvas.pack()
                    self.title = title
                    self.cb = cb
                    self.radius = 10
                    self._draw(self.bg, self.fg)
                    self.canvas.bind('<Button-1>', lambda _e: self.cb() if self.state==tk.NORMAL else None)
                    self.canvas.bind('<Enter>', lambda _e: self._draw(self._hover(self.bg), self.fg) if self.state==tk.NORMAL else None)
                    self.canvas.bind('<Leave>', lambda _e: self._draw(self.bg, self.fg) if self.state==tk.NORMAL else None)
                def _path(self, x1,y1,x2,y2,r):
                    return [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2, x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
                def _draw(self, bg, fg):
                    self.canvas.delete('all')
                    w = 180
                    h = 36
                    x1,y1=4,4
                    x2,y2=w-4,h
                    self.canvas.create_polygon(self._path(x1+2,y1+2,x2+2,y2+2,self.radius), smooth=True, fill='#a3bffa', outline='')
                    self.canvas.create_polygon(self._path(x1,y1,x2,y2,self.radius), smooth=True, fill=bg, outline='')
                    self.canvas.create_text((x1+x2)//2,(y1+y2)//2, text=self.title, fill=fg, font=("Segoe UI", 10, "bold"))
                def _hover(self, c):
                    if c.startswith('#'):
                        r=int(c[1:3],16); g=int(c[3:5],16); b=int(c[5:7],16)
                        r=min(255,int(r+(255-r)*0.08)); g=min(255,int(g+(255-g)*0.08)); b=min(255,int(b+(255-b)*0.08))
                        return f'#{r:02x}{g:02x}{b:02x}'
                    return c
                def pack(self, **kwargs):
                    self.container.pack(**kwargs)
            w = _Btn(parent, text, command, app_self.colors['success'] if 'Refresh' in text else app_self.colors['accent'])
            if 'Export' in text:
                w = _Btn(parent, text, command, app_self.colors['accent'])
            if 'Refresh' in text:
                w = _Btn(parent, text, command, app_self.colors['success'])
            if side=='left':
                w.pack(side='left', padx=6)
            else:
                w.pack(side='right', padx=6)
            return w

        create_modal_button(actions, 'Refresh', lambda: self._refresh_attendance_report(), side='left')
        create_modal_button(actions, 'Export to Excel', lambda: self._export_to_excel(report_window), side='right')

        # Table with styled Treeview
        table_frame = tk.Frame(report_window, bg=self.colors['background'])
        table_frame.pack(fill='both', expand=True, padx=16, pady=(0,8))

        style = ttk.Style(report_window)
        try:
            style.theme_use('clam')
        except:
            pass
        style.configure('Card.Treeview', background=self.colors['card'], fieldbackground=self.colors['card'],
                        foreground=self.colors['text_primary'], rowheight=28, bordercolor=self.colors['border'])
        style.map('Card.Treeview', background=[('selected', self.colors['primary'])],
                  foreground=[('selected', '#ffffff')])
        style.configure('Card.Treeview.Heading', background=self.colors['surface_light'], foreground=self.colors['text_primary'],
                        relief='flat', font=("Segoe UI", 10, 'bold'))

        columns = ("Tên", "Ngày", "Giờ vào", "Giờ ra")
        self.report_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20, style='Card.Treeview')

        self.report_tree.heading("Tên", text="User Name")
        self.report_tree.heading("Ngày", text="Date")
        self.report_tree.heading("Giờ vào", text="Check-in Time")
        self.report_tree.heading("Giờ ra", text="Check-out Time")

        self.report_tree.column("Tên", width=220, anchor="w")
        self.report_tree.column("Ngày", width=120, anchor="center")
        self.report_tree.column("Giờ vào", width=140, anchor="center")
        self.report_tree.column("Giờ ra", width=140, anchor="center")

        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.report_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.report_tree.xview)
        self.report_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        self.report_tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")

        # Initialize date options and load data + zebra striping
        self._refresh_report_date_options()
        self._load_attendance_report_data()
        for i, iid in enumerate(self.report_tree.get_children()):
            self.report_tree.item(iid, tags=('odd',) if i % 2 else ('even',))
        self.report_tree.tag_configure('odd', background=self.colors['surface_light'])

        # Footer status
        status = tk.Frame(report_window, bg=self.colors['surface'])
        status.pack(fill='x', padx=16, pady=(0,16))
        data_count = len(self.report_tree.get_children())
        tk.Label(status, text=f"Total records: {data_count}", font=("Segoe UI", 10),
                 fg=self.colors['text_secondary'], bg=self.colors['surface']).pack(anchor='e')

    def _load_attendance_report_data(self):
        """Load attendance data into the report table"""
        # Clear existing data
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
        
        # Get detailed data
        data = get_detailed_attendance_data()
        # Filter by selected date (format dd/mm/YYYY)
        selected_date = ''
        try:
            if getattr(self, 'report_date_picker', None) is not None:
                # tkcalendar DateEntry returns date object
                d = self.report_date_picker.get_date()
                selected_date = d.strftime('%d/%m/%Y')
            elif getattr(self, 'report_date_combo', None) is not None:
                selected_date = getattr(self, 'report_date_var', None).get()
        except Exception:
            selected_date = ''
        if selected_date:
            data = [r for r in data if r.get('date') == selected_date]
        # Filter by username contains (case-insensitive)
        username_kw = ''
        if hasattr(self, 'report_user_var'):
            username_kw = (self.report_user_var.get() or '').strip().lower()
        if username_kw:
            data = [r for r in data if username_kw in (r.get('name','') or '').lower()]
        
        # Insert data or empty state
        if data:
            # Comment: Restore default column alignment for data rows
            try:
                self.report_tree.column("Tên", anchor="w")
                self.report_tree.column("Ngày", anchor="center")
                self.report_tree.column("Giờ vào", anchor="center")
                self.report_tree.column("Giờ ra", anchor="center")
            except Exception:
                pass
            for record in data:
                self.report_tree.insert("", "end", values=(
                    record["name"],
                    record["date"],
                    record["time_in"],
                    record["time_out"]
                ))
        else:
            # Comment: Show a placeholder row when there is no data
            try:
                # Center align all columns for the placeholder row only case
                self.report_tree.column("Tên", anchor="center")
                self.report_tree.column("Ngày", anchor="center")
                self.report_tree.column("Giờ vào", anchor="center")
                self.report_tree.column("Giờ ra", anchor="center")
            except Exception:
                pass
            self.report_tree.insert("", "end", values=("Trống", "Trống", "Trống", "Trống"), tags=('empty',))

        # Re-apply zebra striping
        for i, iid in enumerate(self.report_tree.get_children()):
            tags = self.report_tree.item(iid, 'tags')
            if 'empty' in tags:
                continue
            self.report_tree.item(iid, tags=('odd',) if i % 2 else ('even',))
        self.report_tree.tag_configure('odd', background=self.colors['surface_light'])
        self.report_tree.tag_configure('empty', foreground=self.colors['danger'])

    
    # Removed sorting feature by request; keep date filtering only

    def _on_report_date_change(self):
        """Handle change of selected date and reload data.
        Comment: Refresh table when user selects a different date.
        """
        # Reload table on date or username change
        if hasattr(self, 'report_tree') and self.report_tree.winfo_exists():
            self._load_attendance_report_data()
            # Count only non-empty rows
            data_count = 0
            for iid in self.report_tree.get_children():
                if 'empty' not in self.report_tree.item(iid, 'tags'):
                    data_count += 1
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Frame):
                            for grandchild in child.winfo_children():
                                if isinstance(grandchild, ttk.Label) and "Total records" in str(grandchild.cget("text")):
                                    grandchild.configure(text=f"Total records: {data_count}")
                                    break

    def _refresh_report_date_options(self):
        """Populate date combobox with available report dates; default to today or latest.
        Comment: Scan reports folder for CSVs and parse dates.
        """
        from datetime import datetime
        from config import REPORTS_DIR

        dates = []
        if REPORTS_DIR.exists():
            for csv_path in REPORTS_DIR.glob('*.csv'):
                stem = csv_path.stem
                if stem.startswith('attendance_'):
                    try:
                        d = datetime.strptime(stem[11:], '%Y%m%d').strftime('%d/%m/%Y')
                        dates.append(d)
                    except Exception:
                        continue
        dates = sorted(set(dates), key=lambda s: datetime.strptime(s, '%d/%m/%Y'), reverse=True)

        # If using DateEntry, set default to today; else populate combobox
        if getattr(self, 'report_date_picker', None) is not None:
            try:
                # Comment: Set picker value to today (or latest available if today not present)
                today_str = datetime.now().strftime('%d/%m/%Y')
                if dates:
                    # Prefer today if present, else latest date from reports
                    target = today_str if today_str in dates else dates[0]
                    day, month, year = map(int, target.split('/'))
                    from datetime import date as _date
                    self.report_date_picker.set_date(_date(year, month, day))
            except Exception:
                pass
        elif getattr(self, 'report_date_combo', None) is not None:
            self.report_date_combo['values'] = dates
            today_str = datetime.now().strftime('%d/%m/%Y')
            default_date = today_str if today_str in dates else (dates[0] if dates else '')
            self.report_date_var.set(default_date)
    
    def _get_last_attendance_status(self, name):
        """Get the last attendance status for a person today"""
        from pathlib import Path
        from datetime import datetime
        import csv
        
        path = Path("app/reports") / (datetime.now().strftime("attendance_%Y%m%d.csv"))
        if not path.exists():
            return None
        
        last_status = None
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["name"] == name:
                    last_status = row["status"]
        
        return last_status

    def _refresh_attendance_report(self):
        """Refresh the attendance report data"""
        if hasattr(self, 'report_tree') and self.report_tree.winfo_exists():
            self._load_attendance_report_data()
            # Update status label (exclude placeholder row)
            data_count = 0
            for iid in self.report_tree.get_children():
                if 'empty' not in self.report_tree.item(iid, 'tags'):
                    data_count += 1
            # Find and update status label
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Frame):
                            for grandchild in child.winfo_children():
                                if isinstance(grandchild, ttk.Label) and "Total records" in str(grandchild.cget("text")):
                                    grandchild.configure(text=f"Total records: {data_count}")
                                    break
            print("REFRESH: Attendance report data refreshed")

    def _export_to_excel(self, parent_window):
        """Export attendance report to Excel file"""
        try:
            import pandas as pd
            from tkinter import filedialog
            from datetime import datetime
            
            # Get currently displayed (sorted) data from the table
            data = []
            if hasattr(self, 'report_tree') and self.report_tree.winfo_exists():
                for iid in self.report_tree.get_children():
                    values = self.report_tree.item(iid, 'values')
                    if values and len(values) == 4:
                        data.append({
                            "name": values[0],
                            "date": values[1],
                            "time_in": values[2],
                            "time_out": values[3]
                        })
            else:
                # Fallback to raw data if table not available
                data = get_detailed_attendance_data()
                data = self._sort_report_data(data)
            
            if not data:
                messagebox.showwarning("Cảnh báo", "Không có dữ liệu điểm danh để xuất!")
                return
            
            # Create DataFrame
            df = pd.DataFrame(data)
            df.columns = ["User Name", "Date", "Check-in Time", "Check-out Time"]
            
            # Ask for save location
            filename = filedialog.asksaveasfilename(
                parent=parent_window,
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="Lưu báo cáo điểm danh"
            )
            
            if filename:
                # Export to Excel
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Báo cáo điểm danh', index=False)
                    
                    # Get the workbook and worksheet
                    workbook = writer.book
                    worksheet = writer.sheets['Báo cáo điểm danh']
                    
                    # Auto-adjust column widths
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                
                messagebox.showinfo("Thành công", f"Đã xuất báo cáo thành công!\nFile: {filename}")
                print(f"EXPORT: Excel report exported: {filename}")
                
        except ImportError:
            messagebox.showerror("Lỗi", "Cần cài đặt pandas và openpyxl để xuất Excel!\nChạy: pip install pandas openpyxl")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xuất file Excel:\n{str(e)}")

def main():
    root = tk.Tk()
    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except:
        pass
    # Start maximized (windowed, with decorations)
    # Comment: Run app maximized (not fullscreen); ESC to exit
    try:
        root.state('zoomed')
    except Exception:
        # Fallback: set geometry to screen size
        try:
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            root.geometry(f"{sw}x{sh}+0+0")
        except Exception:
            pass
    # Allow ESC to close the app
    root.bind('<Escape>', lambda _e: (root.quit(), root.destroy()))
    app = AttendanceApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop_scan(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    main()
