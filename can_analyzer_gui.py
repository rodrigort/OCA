#!/usr/bin/env python3
"""Desktop application for Open CAN Analyzer (OCA)."""

import csv
import collections
import datetime as dt
import json
import math
import queue
import re
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from oca import __version__
from oca.capture import read_capture, replay_delays
from oca import config as app_config
from oca.dbc import DBCDecoder, DBCError
from oca.i18n import Translator
from oca.profiles import DEFAULT_PROFILE, ProfileError, load_profile as read_profile, normalize_id
from oca.protocol import ProtocolError, build_tx, parse_line
from oca.serial_ports import sorted_ports

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None


APP_DIR = app_config.application_root()
PROFILES_DIR = app_config.resource_path("profiles")
LOCALES_DIR = app_config.resource_path("locales")
LOGS_DIR = app_config.config_path().parent / "logs"

class CANAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.config = app_config.load_config()
        self.translator = Translator(LOCALES_DIR, self.config.get("language", "auto"))
        self.tr = self.translator
        self.root.title(self.tr("app.title", version=__version__))
        self.configure_window_geometry(self.config.get("geometry", ""))

        self.profile = DEFAULT_PROFILE.copy()
        self.profile_path = None
        self.profile_ids = {}
        self.auto_responses = {}
        self.quick_tx_buttons = []

        self.serial_port = None
        self.reader_stop = threading.Event()
        self.rx_queue = queue.Queue(maxsize=5000)
        self.queue_dropped = 0
        self.protocol_version = 1
        self.device_name = self.tr("status.device_unknown")
        self.device_status = None
        self.tx_sequence = 0
        self.pending_tx = {}
        self.dbc = DBCDecoder()
        self.replay_frames = []
        self.replay_jobs = []
        self.csv_file = None
        self.csv_writer = None
        self.rx_count = 0
        self.tx_count = 0
        self.hidden_count = 0
        self.paused_count = 0
        self.id_stats = {}
        self.last_rx_time_by_id = {}
        self.last_device_time_by_id = {}
        self.frame_history = {}
        self.graph_running = True
        self.graph_update_pending = False
        self.graph_dbc_signal_names = {}

        self.port_var = tk.StringVar(value=self.config.get("port", ""))
        self.baud_var = tk.StringVar(value=self.config.get("baud", "115200"))
        self.status_var = tk.StringVar(value=self.tr("status.disconnected"))
        self.footer_var = tk.StringVar(value=self.tr("status.ready"))
        self.csv_var = tk.StringVar(value=self.tr("status.csv_off"))
        self.profile_var = tk.StringVar(value=self.tr("profile.label", name=self.tr("profile.generic")))
        self.filter_var = tk.StringVar(value=self.config.get("filter", ""))
        self.search_var = tk.StringVar(value=self.config.get("search", ""))
        saved_direction = self.config.get("direction_filter", "ALL")
        if saved_direction in ("Todos", "All"):
            saved_direction = "ALL"
        self.direction_filter_var = tk.StringVar(
            value=self.tr("common.all") if saved_direction == "ALL" else saved_direction
        )
        self.language_var = tk.StringVar(value=self.config.get("language", "auto"))
        self.language_labels = {
            "auto": self.tr("language.auto"),
            "en": self.tr("language.en"),
            "pt_BR": self.tr("language.pt_BR"),
        }
        self.language_display_var = tk.StringVar(
            value=self.language_labels.get(self.language_var.get(), self.language_labels["auto"])
        )
        self.autoscroll_var = tk.BooleanVar(value=self.config.get("autoscroll", True))
        self.pause_view_var = tk.BooleanVar(value=self.config.get("pause_view", False))
        self.auto_response_var = tk.BooleanVar(value=self.config.get("auto_response", False))
        self.listen_only_var = tk.BooleanVar(value=self.config.get("listen_only", True))
        self.graph_id_var = tk.StringVar(value=self.config.get("graph_id", ""))
        self.graph_signal_var = tk.StringVar(value=self.config.get("graph_signal", "B0"))
        self.graph_window_var = tk.StringVar(value=str(self.config.get("graph_window", 10)))
        self.graph_auto_scale_var = tk.BooleanVar(value=self.config.get("graph_auto_scale", True))
        self.graph_status_var = tk.StringVar(value=self.tr("graph.waiting"))
        self.tx_slot_count_var = tk.StringVar(value=str(self.config.get("tx_slot_count", 1)))
        self.selected_tx_slot_var = tk.IntVar(value=int(self.config.get("selected_tx_slot", 0)))
        self.tx_slots = self.create_tx_slots()
        self.tx_slot_rows = []

        self._build_style()
        self._build_layout()
        self._bind_shortcuts()
        self.refresh_ports()
        self.load_initial_profile()
        self.root.after(60, self.process_rx_queue)
        self.root.after(1000, self.poll_device_status)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def configure_window_geometry(self, saved_geometry):
        """Clamp saved dimensions to the current monitor and center the window."""
        width, height, x, y, minimum_width, minimum_height = app_config.fit_window_geometry(
            saved_geometry, self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        )
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(minimum_width, minimum_height)

    def _build_style(self):
        self.root.configure(bg="#14161a")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="#14161a", foreground="#e7eaf0", fieldbackground="#20242b")
        style.configure("TFrame", background="#14161a")
        style.configure("Panel.TFrame", background="#1b1f26")
        style.configure("TLabel", background="#14161a", foreground="#e7eaf0")
        style.configure("Panel.TLabel", background="#1b1f26", foreground="#e7eaf0")
        style.configure("TButton", background="#2d3440", foreground="#f4f6fa", borderwidth=0, padding=7)
        style.map("TButton", background=[("active", "#3d4654")])
        style.configure("Accent.TButton", background="#d2ad58", foreground="#101216")
        style.map("Accent.TButton", background=[("active", "#e1bf6a")])
        style.configure("Danger.TButton", background="#7a2f3a", foreground="#ffffff")
        style.map("Danger.TButton", background=[("active", "#934250")])
        style.configure("TCombobox", fieldbackground="#20242b", background="#20242b", foreground="#e7eaf0")
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#20242b"), ("disabled", "#252a32")],
            background=[("readonly", "#303744"), ("active", "#3d4654")],
            foreground=[("readonly", "#f4f6fa"), ("disabled", "#8a9099")],
            selectbackground=[("readonly", "#20242b")],
            selectforeground=[("readonly", "#f4f6fa")],
        )
        style.configure("TNotebook", background="#14161a", borderwidth=0, tabmargins=(0, 4, 0, 0))
        style.configure(
            "TNotebook.Tab", background="#2d3440", foreground="#e7eaf0",
            borderwidth=0, padding=(14, 7), focuscolor="",
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#d2ad58"), ("active", "#3d4654")],
            foreground=[("selected", "#101216"), ("active", "#ffffff")],
            expand=[("selected", (1, 1, 1, 0))],
        )
        style.configure("Treeview", background="#101216", foreground="#e7eaf0", fieldbackground="#101216", rowheight=25)
        style.configure("Treeview.Heading", background="#242a33", foreground="#e7eaf0")
        style.configure("TCheckbutton", background="#1b1f26", foreground="#e7eaf0")

    def _build_layout(self):
        t = self.tr
        top = ttk.Frame(self.root, style="Panel.TFrame", padding=10)
        top.pack(fill="x")

        ttk.Label(top, text=t("top.port"), style="Panel.TLabel").pack(side="left")
        self.port_combo = ttk.Combobox(top, textvariable=self.port_var, width=24)
        self.port_combo.pack(side="left", padx=(6, 10))
        ttk.Button(top, text=t("top.refresh"), command=self.refresh_ports).pack(side="left", padx=(0, 10))

        ttk.Label(top, text=t("top.baud"), style="Panel.TLabel").pack(side="left")
        ttk.Entry(top, textvariable=self.baud_var, width=9).pack(side="left", padx=(6, 10))

        ttk.Button(top, text=t("top.connect"), style="Accent.TButton", command=self.connect).pack(side="left", padx=(0, 8))
        ttk.Button(top, text=t("top.disconnect"), style="Danger.TButton", command=self.disconnect).pack(side="left", padx=(0, 8))
        ttk.Button(top, text=t("top.clear"), command=self.clear_screen).pack(side="left", padx=(0, 12))

        ttk.Label(top, textvariable=self.status_var, style="Panel.TLabel").pack(side="left", padx=(0, 16))
        ttk.Button(top, text="CSV", command=self.toggle_csv).pack(side="left")
        ttk.Button(top, text=t("top.csv_auto"), command=self.start_auto_csv).pack(side="left", padx=(6, 0))
        ttk.Label(top, textvariable=self.csv_var, style="Panel.TLabel").pack(side="left", padx=(8, 0))
        ttk.Label(top, text=t("top.language"), style="Panel.TLabel").pack(side="left", padx=(16, 4))
        language_combo = ttk.Combobox(top, textvariable=self.language_display_var, state="readonly", width=20)
        language_combo["values"] = tuple(self.language_labels.values())
        language_combo.pack(side="left")
        language_combo.bind("<<ComboboxSelected>>", self.on_language_changed)

        profile_bar = ttk.Frame(self.root, style="Panel.TFrame", padding=(10, 0, 10, 8))
        profile_bar.pack(fill="x")
        ttk.Button(profile_bar, text=t("profile.load"), command=self.choose_profile).pack(side="left")
        ttk.Button(profile_bar, text=t("profile.edit"), command=self.edit_profile).pack(side="left", padx=(6, 0))
        ttk.Label(profile_bar, textvariable=self.profile_var, style="Panel.TLabel").pack(side="left", padx=(10, 18))
        ttk.Label(profile_bar, text=t("filter.id"), style="Panel.TLabel").pack(side="left")
        filter_entry = ttk.Entry(profile_bar, textvariable=self.filter_var, width=20)
        filter_entry.pack(side="left", padx=(6, 8))
        filter_entry.bind("<KeyRelease>", lambda _event: self.update_summary())
        ttk.Label(profile_bar, text=t("filter.example"), style="Panel.TLabel").pack(side="left", padx=(0, 16))
        ttk.Label(profile_bar, text=t("filter.search"), style="Panel.TLabel").pack(side="left")
        search_entry = ttk.Entry(profile_bar, textvariable=self.search_var, width=16)
        search_entry.pack(side="left", padx=(6, 12))
        search_entry.bind("<KeyRelease>", lambda _event: self.update_summary())
        ttk.Label(profile_bar, text=t("filter.direction"), style="Panel.TLabel").pack(side="left")
        direction_combo = ttk.Combobox(
            profile_bar,
            textvariable=self.direction_filter_var,
            values=(t("common.all"), "RX", "TX", "AUTO", "OK", "ERR"),
            state="readonly",
            width=9,
        )
        direction_combo.pack(side="left", padx=(6, 12))
        ttk.Checkbutton(profile_bar, text=t("filter.autoscroll"), variable=self.autoscroll_var).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(profile_bar, text=t("filter.pause"), variable=self.pause_view_var).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(profile_bar, text=t("filter.auto_response"), variable=self.auto_response_var).pack(side="left")
        ttk.Checkbutton(
            profile_bar, text=t("filter.listen_only"), variable=self.listen_only_var,
            command=self.set_listen_only,
        ).pack(side="left", padx=(16, 0))

        body = ttk.Frame(self.root, padding=10)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True)

        self.quick_frame = ttk.Frame(left, style="Panel.TFrame", padding=8)
        self.quick_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(self.quick_frame, text=t("quick.title"), style="Panel.TLabel").pack(side="left", padx=(0, 10))
        ttk.Button(self.quick_frame, text=t("quick.export_screen"), command=self.export_visible_rows).pack(side="right")
        ttk.Button(self.quick_frame, text=t("quick.export_candump"), command=self.export_candump).pack(side="right", padx=(0, 6))
        ttk.Button(self.quick_frame, text=t("quick.replay"), command=self.choose_and_replay_capture).pack(side="right", padx=(0, 6))
        ttk.Button(self.quick_frame, text=t("quick.load_dbc"), command=self.choose_dbc).pack(side="right", padx=(0, 6))

        columns = ("time", "dir", "id", "dlc", "period", "count", "label", "data", "raw")
        self.views = ttk.Notebook(left)
        self.views.pack(fill="both", expand=True)
        traffic_tab = ttk.Frame(self.views)
        latest_tab = ttk.Frame(self.views)
        graph_tab = ttk.Frame(self.views)
        self.views.add(traffic_tab, text=t("tab.traffic"))
        self.views.add(latest_tab, text=t("tab.latest"))
        self.views.add(graph_tab, text=t("tab.graphs"))
        table_frame = ttk.Frame(traffic_tab)
        table_frame.pack(fill="both", expand=True)

        self.table = ttk.Treeview(table_frame, columns=columns, show="headings")
        table_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        table_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=table_y.set, xscrollcommand=table_x.set)
        headings = {
            "time": t("column.time"),
            "dir": t("column.type"),
            "id": "ID",
            "dlc": "DLC",
            "period": t("column.period"),
            "count": t("column.count"),
            "label": t("column.description"),
            "data": t("column.data"),
            "raw": t("column.raw"),
        }
        widths = {
            "time": 110,
            "dir": 72,
            "id": 80,
            "dlc": 52,
            "period": 85,
            "count": 62,
            "label": 160,
            "data": 260,
            "raw": 340,
        }
        for col in columns:
            self.table.heading(col, text=headings[col])
            self.table.column(col, width=widths[col], anchor="w")
        self.table.grid(row=0, column=0, sticky="nsew")
        table_y.grid(row=0, column=1, sticky="ns")
        table_x.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.table.bind("<<TreeviewSelect>>", self.show_selected_frame_details)
        self.table.bind("<Control-c>", self.copy_selected_row)
        self.table.bind("<Control-C>", self.copy_selected_row)

        self.table.tag_configure("RX", background="#111922")
        self.table.tag_configure("TX", background="#1f1b12")
        self.table.tag_configure("AUTO", background="#211932")
        self.table.tag_configure("OK", background="#132016")
        self.table.tag_configure("ERR", background="#28161a")
        self.table.tag_configure("UNKNOWN", background="#171a1f")

        latest_columns = ("id", "count", "period", "rate", "label", "data", "time")
        self.latest_table = ttk.Treeview(latest_tab, columns=latest_columns, show="headings")
        latest_y = ttk.Scrollbar(latest_tab, orient="vertical", command=self.latest_table.yview)
        self.latest_table.configure(yscrollcommand=latest_y.set)
        latest_headings = {
            "id": "ID", "count": t("column.count"), "period": t("column.period"), "rate": t("column.rate"),
            "label": t("column.description"), "data": t("column.last_data"), "time": t("column.last_rx"),
        }
        latest_widths = {"id": 90, "count": 90, "period": 100, "rate": 100, "label": 220, "data": 280, "time": 130}
        for col in latest_columns:
            self.latest_table.heading(col, text=latest_headings[col])
            self.latest_table.column(col, width=latest_widths[col], anchor="w")
        self.latest_table.pack(side="left", fill="both", expand=True)
        latest_y.pack(side="right", fill="y")
        self.latest_table.bind("<<TreeviewSelect>>", self.select_latest_id)

        graph_toolbar = ttk.Frame(graph_tab, style="Panel.TFrame", padding=10)
        graph_toolbar.pack(fill="x")
        graph_selectors = ttk.Frame(graph_toolbar, style="Panel.TFrame")
        graph_selectors.pack(fill="x")
        graph_commands = ttk.Frame(graph_toolbar, style="Panel.TFrame")
        graph_commands.pack(fill="x", pady=(7, 0))
        ttk.Label(graph_selectors, text="ID", style="Panel.TLabel").pack(side="left")
        self.graph_id_combo = ttk.Combobox(
            graph_selectors, textvariable=self.graph_id_var, state="readonly", width=10,
        )
        self.graph_id_combo.pack(side="left", padx=(6, 14))
        self.graph_id_combo.bind("<<ComboboxSelected>>", self.on_graph_id_changed)
        ttk.Label(graph_selectors, text=t("graph.signal"), style="Panel.TLabel").pack(side="left")
        self.graph_signal_combo = ttk.Combobox(
            graph_selectors, textvariable=self.graph_signal_var, state="readonly", width=28,
        )
        self.graph_signal_combo["values"] = tuple(f"B{index}" for index in range(8))
        self.graph_signal_combo.pack(side="left", padx=(6, 14))
        self.graph_signal_combo.bind("<<ComboboxSelected>>", lambda _event: self.draw_trend_graph())
        ttk.Label(graph_selectors, text=t("graph.window"), style="Panel.TLabel").pack(side="left")
        graph_window = ttk.Spinbox(
            graph_selectors, from_=1, to=3600, textvariable=self.graph_window_var, width=6,
            command=self.draw_trend_graph,
        )
        graph_window.pack(side="left", padx=(6, 4))
        graph_window.bind("<Return>", lambda _event: self.draw_trend_graph())
        ttk.Label(graph_selectors, text="s", style="Panel.TLabel").pack(side="left", padx=(0, 14))
        ttk.Checkbutton(
            graph_selectors, text=t("graph.autoscale"), variable=self.graph_auto_scale_var,
            command=self.draw_trend_graph,
        ).pack(side="left", padx=(0, 14))
        ttk.Button(graph_commands, text=t("graph.start"), style="Accent.TButton", command=self.start_graph).pack(side="left")
        ttk.Button(graph_commands, text=t("graph.pause"), command=self.pause_graph).pack(side="left", padx=(6, 0))
        ttk.Button(graph_commands, text=t("graph.clear"), command=self.clear_graph).pack(side="left", padx=(6, 0))
        ttk.Button(graph_commands, text=t("graph.demo"), command=self.load_graph_demo).pack(side="left", padx=(6, 0))
        ttk.Label(
            graph_commands, text=t("graph.hint"),
            style="Panel.TLabel",
        ).pack(side="left", padx=(14, 0))

        self.graph_canvas = tk.Canvas(graph_tab, bg="#101216", highlightthickness=0)
        self.graph_canvas.pack(fill="both", expand=True)
        self.graph_canvas.bind("<Configure>", lambda _event: self.draw_trend_graph())
        graph_footer = ttk.Frame(graph_tab, style="Panel.TFrame", padding=(10, 5))
        graph_footer.pack(fill="x")
        ttk.Label(graph_footer, textvariable=self.graph_status_var, style="Panel.TLabel").pack(side="left")

        bottom = ttk.Frame(left, style="Panel.TFrame", padding=10)
        bottom.pack(fill="x", pady=(10, 0))
        tx_header = ttk.Frame(bottom, style="Panel.TFrame")
        tx_header.pack(fill="x")
        ttk.Label(tx_header, text=t("tx.options"), style="Panel.TLabel").pack(side="left")
        ttk.Spinbox(
            tx_header,
            from_=1,
            to=5,
            textvariable=self.tx_slot_count_var,
            width=4,
            command=self.update_tx_slot_visibility,
        ).pack(side="left", padx=(6, 12))
        ttk.Label(tx_header, text=t("tx.hint"), style="Panel.TLabel").pack(side="left")
        ttk.Button(tx_header, text=t("tx.send_selected"), style="Accent.TButton", command=self.send_tx).pack(side="right")

        self.tx_slots_frame = ttk.Frame(bottom, style="Panel.TFrame")
        self.tx_slots_frame.pack(fill="x", pady=(8, 0))
        self.build_tx_slot_rows()

        right = ttk.Frame(body, style="Panel.TFrame", padding=12)
        right.pack(side="right", fill="y", padx=(10, 0))
        ttk.Label(right, text=t("panel.summary"), style="Panel.TLabel", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.summary = tk.Text(right, width=38, height=12, bg="#101216", fg="#e7eaf0", relief="flat", insertbackground="#e7eaf0")
        self.summary.pack(fill="x", pady=(8, 12))
        self.summary.configure(state="disabled")

        ttk.Label(right, text=t("panel.counters"), style="Panel.TLabel", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.id_counter_box = tk.Text(right, width=38, height=10, bg="#101216", fg="#e7eaf0", relief="flat", insertbackground="#e7eaf0")
        self.id_counter_box.pack(fill="x", pady=(8, 12))
        self.id_counter_box.configure(state="disabled")

        ttk.Label(right, text=t("panel.rate"), style="Panel.TLabel", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.rate_canvas = tk.Canvas(right, width=300, height=95, bg="#101216", highlightthickness=0)
        self.rate_canvas.pack(fill="x", pady=(8, 12))

        ttk.Label(right, text=t("panel.details"), style="Panel.TLabel", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        self.details_box = tk.Text(right, width=38, height=18, bg="#101216", fg="#d2ad58", relief="flat", insertbackground="#e7eaf0")
        self.details_box.pack(fill="both", expand=True, pady=(8, 0))
        self.details_box.configure(state="disabled")

        footer = ttk.Frame(self.root, style="Panel.TFrame", padding=(10, 5))
        footer.pack(fill="x", side="bottom")
        ttk.Label(footer, textvariable=self.footer_var, style="Panel.TLabel").pack(side="left")
        self.update_summary()

    def _bind_shortcuts(self):
        self.root.bind("<F5>", lambda _event: self.refresh_ports())
        self.root.bind("<Control-l>", lambda _event: self.clear_screen())
        self.root.bind("<Control-L>", lambda _event: self.clear_screen())

    def create_tx_slots(self):
        defaults = self.config.get("tx_slots", [])
        fallback = [
            {"id": "201", "dlc": "8", "data": ["11", "22", "33", "44", "55", "66", "77", "88"]},
            {"id": "351", "dlc": "8", "data": ["AA", "BB", "CC", "DD", "EE", "FF", "12", "34"]},
            {"id": "101", "dlc": "8", "data": ["10", "20", "30", "40", "50", "60", "70", "80"]},
            {"id": "301", "dlc": "8", "data": ["A1", "B2", "C3", "D4", "E5", "F6", "07", "18"]},
            {"id": "100", "dlc": "8", "data": ["00", "11", "22", "33", "44", "55", "66", "77"]},
        ]
        slots = []
        for index in range(5):
            source = defaults[index] if index < len(defaults) else fallback[index]
            data = list(source.get("data", []))[:8]
            while len(data) < 8:
                data.append("00")
            slots.append(
                {
                    "selected": tk.BooleanVar(value=index == self.selected_tx_slot_var.get()),
                    "id": tk.StringVar(value=str(source.get("id", fallback[index]["id"]))),
                    "dlc": tk.StringVar(value=str(source.get("dlc", fallback[index]["dlc"]))),
                    "data": [tk.StringVar(value=str(value).replace("0x", "").replace("0X", "")) for value in data],
                }
            )
        if not any(slot["selected"].get() for slot in slots):
            slots[0]["selected"].set(True)
            self.selected_tx_slot_var.set(0)
        return slots

    def build_tx_slot_rows(self):
        for index, slot in enumerate(self.tx_slots):
            row = ttk.Frame(self.tx_slots_frame, style="Panel.TFrame")
            row.grid(row=index, column=0, sticky="w", pady=2)
            ttk.Checkbutton(row, variable=slot["selected"], command=lambda selected=index: self.select_tx_slot(selected)).pack(side="left")
            ttk.Label(row, text=f"TX {index + 1}", style="Panel.TLabel", width=5).pack(side="left")
            ttk.Label(row, text="ID", style="Panel.TLabel").pack(side="left")
            ttk.Entry(row, textvariable=slot["id"], width=8).pack(side="left", padx=(4, 10))
            ttk.Label(row, text="DLC", style="Panel.TLabel").pack(side="left")
            ttk.Spinbox(row, from_=0, to=8, textvariable=slot["dlc"], width=4).pack(side="left", padx=(4, 10))
            for byte_index, var in enumerate(slot["data"]):
                ttk.Label(row, text=f"B{byte_index}", style="Panel.TLabel").pack(side="left")
                ttk.Entry(row, textvariable=var, width=4).pack(side="left", padx=(3, 6))
            self.tx_slot_rows.append(row)
        self.update_tx_slot_visibility()

    def select_tx_slot(self, selected_index):
        for index, slot in enumerate(self.tx_slots):
            slot["selected"].set(index == selected_index)
        self.selected_tx_slot_var.set(selected_index)

    def tx_slot_count(self):
        try:
            count = int(self.tx_slot_count_var.get())
        except ValueError:
            count = 1
        count = max(1, min(5, count))
        self.tx_slot_count_var.set(str(count))
        return count

    def update_tx_slot_visibility(self):
        count = self.tx_slot_count()
        selected = self.selected_tx_slot_var.get()
        if selected >= count:
            self.select_tx_slot(0)
        for index, row in enumerate(self.tx_slot_rows):
            if index < count:
                row.grid()
            else:
                row.grid_remove()
                self.tx_slots[index]["selected"].set(False)
        if not any(self.tx_slots[index]["selected"].get() for index in range(count)):
            self.select_tx_slot(0)

    def load_initial_profile(self):
        saved = self.config.get("profile_path")
        if saved:
            saved_path = Path(saved)
            if not saved_path.is_absolute():
                saved_path = APP_DIR / saved_path
            if saved_path.exists():
                self.load_profile(saved_path)
                return
        default_path = PROFILES_DIR / "generic.json"
        if default_path.exists():
            self.load_profile(default_path)
        else:
            self.apply_profile(DEFAULT_PROFILE, None)

    def choose_profile(self):
        path = filedialog.askopenfilename(
            title=self.tr("dialog.profile_load"),
            initialdir=str(PROFILES_DIR if PROFILES_DIR.exists() else APP_DIR),
            filetypes=[("JSON", "*.json"), (self.tr("file.all"), "*.*")],
        )
        if path:
            self.load_profile(Path(path))

    def edit_profile(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(self.tr("dialog.profile_editor"))
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("620x520")
        frame = ttk.Frame(dialog, padding=14)
        frame.pack(fill="both", expand=True)

        name_var = tk.StringVar(value=self.profile.get("profile_name", "Generic CAN"))
        bitrate_var = tk.StringVar(value=str(self.profile.get("baudrate_can", 500000)))
        ttk.Label(frame, text=self.tr("dialog.profile_name")).grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=name_var, width=44).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(frame, text=self.tr("dialog.can_bitrate")).grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=bitrate_var, width=16).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        ttk.Label(frame, text=self.tr("dialog.profile_ids")).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(14, 4)
        )
        ids_text = tk.Text(frame, height=18, bg="#101216", fg="#e7eaf0", insertbackground="#e7eaf0")
        ids_text.grid(row=3, column=0, columnspan=2, sticky="nsew")
        ids_text.insert("1.0", "\n".join(
            f"{key.replace('0x', '')}={value}" for key, value in sorted(self.profile_ids.items())
        ))
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(3, weight=1)

        def save_edited_profile():
            try:
                bitrate = int(bitrate_var.get())
                ids = {}
                for line in ids_text.get("1.0", "end").splitlines():
                    if not line.strip():
                        continue
                    key, description = line.split("=", 1)
                    ids[normalize_id(key)] = description.strip()
                updated = dict(self.profile)
                updated.update({"profile_name": name_var.get().strip(), "baudrate_can": bitrate, "ids": ids})
                path = filedialog.asksaveasfilename(
                    parent=dialog,
                    title=self.tr("dialog.profile_save"),
                    initialdir=str(PROFILES_DIR),
                    initialfile=(self.profile_path.name if self.profile_path else "new_profile.json"),
                    defaultextension=".json",
                    filetypes=[("JSON", "*.json")],
                )
                if not path:
                    return
                Path(path).write_text(json.dumps(updated, indent=2, ensure_ascii=True), encoding="utf-8")
                self.load_profile(Path(path))
            except (OSError, ValueError) as exc:
                messagebox.showerror(self.tr("dialog.invalid_profile"), str(exc), parent=dialog)
                return
            dialog.destroy()

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text=self.tr("common.cancel"), command=dialog.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text=self.tr("dialog.profile_save_button"), style="Accent.TButton", command=save_edited_profile).pack(side="left")

    def load_profile(self, path):
        try:
            profile = read_profile(path)
        except ProfileError as exc:
            messagebox.showerror(
                self.tr("dialog.invalid_profile"),
                self.tr("dialog.profile_load_failed", error=self.profile_error_text(exc)),
            )
            return
        self.apply_profile(profile, path)
        self.save_config()

    def apply_profile(self, profile, path):
        self.profile = {**DEFAULT_PROFILE, **profile}
        self.profile_path = path
        self.profile_ids = {}
        for key, value in self.profile.get("ids", {}).items():
            try:
                normalized = self.normalize_id(key)
            except ValueError:
                continue
            if normalized:
                self.profile_ids[normalized] = value
        self.auto_responses = {}
        for rule in self.profile.get("auto_responses", []):
            if rule.get("enabled", True):
                try:
                    rx_id = self.normalize_id(rule.get("rx_id", ""))
                except ValueError:
                    rx_id = ""
                if rx_id:
                    self.auto_responses[rx_id] = rule
        self.profile_var.set(self.tr("profile.label", name=self.profile.get("profile_name", self.tr("common.none"))))
        self.build_quick_buttons()
        self.update_summary()

    def profile_error_text(self, error):
        key = f"profile_error.{getattr(error, 'code', 'read')}"
        context = getattr(error, "context", {})
        return self.tr(key, **context)

    def build_quick_buttons(self):
        for button in self.quick_tx_buttons:
            button.destroy()
        self.quick_tx_buttons.clear()
        for item in self.profile.get("quick_tx", []):
            label = item.get("label", item.get("tx_id", "TX"))
            button = ttk.Button(
                self.quick_frame,
                text=label,
                command=lambda payload=item: self.send_tx_profile_item(payload, manual=True),
            )
            button.pack(side="left", padx=(0, 8))
            self.quick_tx_buttons.append(button)

    def refresh_ports(self):
        if list_ports is None:
            messagebox.showerror(self.tr("dialog.pyserial_missing"), self.tr("dialog.pyserial_install"))
            return
        port_objects = sorted_ports(list_ports.comports())
        ports = [port.device for port in port_objects]
        self.port_combo["values"] = ports
        if ports and self.port_var.get() not in ports:
            self.port_var.set(ports[0])
        self.footer_var.set(self.tr(
            "status.ports", ports=", ".join(ports) if ports else self.tr("status.no_ports")
        ))

    def connect(self):
        if serial is None:
            messagebox.showerror(self.tr("dialog.pyserial_missing"), self.tr("dialog.pyserial_install"))
            return
        if self.serial_port and self.serial_port.is_open:
            return
        try:
            port_name = self.port_var.get().strip()
            if not port_name:
                raise ValueError(self.tr("status.no_ports"))
            self.serial_port = serial.Serial(port_name, int(self.baud_var.get()), timeout=0.1)
        except Exception as exc:
            messagebox.showerror(
                self.tr("dialog.serial_error"),
                self.tr("dialog.serial_open_failed", port=self.port_var.get(), error=exc),
            )
            return

        self.reader_stop.clear()
        self.protocol_version = 1
        self.device_name = self.tr("status.device_waiting")
        self.device_status = None
        threading.Thread(target=self.reader_loop, daemon=True).start()
        connected_text = self.tr("status.connected", port=self.port_var.get().strip())
        self.status_var.set(connected_text)
        self.footer_var.set(connected_text)
        self.save_config()
        self.update_summary()
        self.root.after(150, lambda: self.send_control_command("HELLO?\n"))

    def disconnect(self):
        self.reader_stop.set()
        if self.serial_port:
            try:
                self.serial_port.close()
            except Exception:
                pass
        self.status_var.set(self.tr("status.disconnected"))
        self.footer_var.set(self.tr("status.disconnected"))
        self.update_summary()

    def reader_loop(self):
        while not self.reader_stop.is_set():
            try:
                line = self.serial_port.readline().decode("ascii", errors="replace").strip()
            except Exception as exc:
                try:
                    self.rx_queue.put_nowait(("ERR", self.tr("terminal.read_error", error=exc)))
                except queue.Full:
                    pass
                self.reader_stop.set()
                break
            if line:
                try:
                    self.rx_queue.put_nowait(("LINE", line))
                except queue.Full:
                    self.queue_dropped += 1

    def process_rx_queue(self):
        processed = 0
        while processed < 250:
            try:
                kind, value = self.rx_queue.get_nowait()
            except queue.Empty:
                break
            processed += 1
            if kind == "ERR":
                self.add_row("ERR", "", "", "", "", value, "")
                self.status_var.set(self.tr("status.serial_error"))
                self.footer_var.set(value)
                self.disconnect()
            else:
                self.handle_serial_line(value)
        self.root.after(60, self.process_rx_queue)

    def handle_serial_line(self, line):
        try:
            message = parse_line(line)
        except ProtocolError as exc:
            self.add_row("ERR", "", "", "", "", self.tr("dialog.invalid_line", line=line, error=exc), "")
            self.update_summary()
            return

        if message.kind == "FRAME":
            frame = message.frame
            can_id = f"0x{frame.can_id:03X}"
            dlc = str(frame.dlc)
            data = " ".join(f"{item:02X}" for item in frame.data)
            self.record_graph_frame(can_id, frame.timestamp_ms, frame.dlc, frame.data)
            period = self.update_period(can_id, frame.timestamp_ms)
            self.rx_count += 1
            stat = self.id_stats.setdefault(can_id, {"count": 0, "last_time": "", "period": "", "data": ""})
            stat["count"] += 1
            stat["last_time"] = dt.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            stat["period"] = period
            stat["data"] = data
            self.add_row("RX", can_id, dlc, period, data, line, "")
            self.set_details_text(self.describe_frame("RX", can_id, dlc, period, data, line))
            self.write_csv(
                "RX", can_id, dlc, period, self.description_for_id(can_id), data, line,
                device_timestamp_ms=frame.timestamp_ms,
            )
            if self.auto_response_var.get() and can_id in self.auto_responses:
                self.send_tx_profile_item(self.auto_responses[can_id], manual=False)
        elif message.kind == "TX_OK":
            if message.sequence is not None:
                self.pending_tx.pop(message.sequence, None)
            self.add_row("OK", "", "", "", "", line, "")
        elif message.kind == "STATUS":
            self.device_status = message.status
            self.listen_only_var.set(message.status.mode == "LISTEN")
        elif message.kind == "HELLO":
            self.protocol_version = 2
            self.device_name = message.text
            self.footer_var.set(self.tr("status.device_identified", device=message.text))
            self.send_control_command("GET,STATUS\n")
            if self.listen_only_var.get():
                self.send_control_command("SET,LISTEN,1\n")
        elif message.kind == "MODE":
            self.listen_only_var.set(message.text == "LISTEN")
            self.footer_var.set(self.tr("status.can_mode", mode=message.text))
        elif message.kind == "ERROR":
            self.add_row("ERR", "", "", "", "", line, "")
            if message.text.startswith("CAN"):
                self.set_details_text(self.tr("error.can_busy"))
        else:
            self.add_row("INFO", "", "", "", "", line, "")
        self.update_summary()

    def send_tx(self):
        self.update_tx_slot_visibility()
        selected = self.selected_tx_slot_var.get()
        if selected >= self.tx_slot_count():
            selected = 0
            self.select_tx_slot(selected)
        slot = self.tx_slots[selected]
        self.send_tx_values(slot["id"].get(), slot["dlc"].get(), [var.get() for var in slot["data"]], manual=True)

    def send_tx_profile_item(self, item, manual):
        self.send_tx_values(item.get("tx_id", ""), str(item.get("dlc", "8")), item.get("data", []), manual=manual)

    def send_tx_values(self, tx_id_text, dlc_text, data_texts, manual):
        if not self.serial_port or not self.serial_port.is_open:
            if manual:
                messagebox.showwarning(self.tr("dialog.disconnected"), self.tr("dialog.connect_first"))
            return
        if self.listen_only_var.get():
            if manual:
                messagebox.showwarning(self.tr("dialog.listen_only"), self.tr("dialog.listen_only_tx"))
            return
        try:
            can_id = int(self.normalize_id(tx_id_text), 16)
            dlc = int(dlc_text, 0)
            data = [int(str(value).replace("0x", "").replace("0X", ""), 16) for value in data_texts]
            while len(data) < 8:
                data.append(0)
            if can_id > 0x7FF or not 0 <= dlc <= 8 or len(data) > 8 or any(byte > 0xFF or byte < 0 for byte in data):
                raise ValueError
        except ValueError:
            if manual:
                messagebox.showerror(self.tr("dialog.invalid_tx"), self.tr("dialog.invalid_tx_help"))
            return

        sequence = None
        if self.protocol_version >= 2:
            self.tx_sequence = (self.tx_sequence + 1) & 0xFFFF
            sequence = self.tx_sequence
        command = build_tx(can_id, dlc, data[:8], sequence=sequence)
        try:
            self.serial_port.write(command.encode("ascii"))
        except Exception as exc:
            self.disconnect()
            if manual:
                messagebox.showerror(self.tr("dialog.tx_error"), str(exc))
            return

        direction = "TX" if manual else "AUTO"
        if sequence is not None:
            self.pending_tx[sequence] = (can_id, dt.datetime.now())
        self.tx_count += 1
        can_id_text = f"0x{can_id:03X}"
        data_text = " ".join(f"{byte:02X}" for byte in data[:8])
        self.add_row(direction, can_id_text, str(dlc), "", data_text, command.strip(), "")
        self.write_csv(direction, can_id_text, str(dlc), "", self.description_for_id(can_id_text), data_text, command.strip())
        self.footer_var.set(self.tr(
            "status.tx_sent", direction=direction, can_id=can_id_text, dlc=dlc, data=data_text
        ))
        self.update_summary()

    def add_row(self, direction, can_id, dlc, period, data, raw, extra_tag):
        if can_id and direction == "RX":
            self.update_latest_row(can_id, period, data)
        selected_direction = self.direction_filter_var.get()
        if selected_direction != self.tr("common.all") and direction != selected_direction:
            self.hidden_count += 1
            return
        if can_id and not self.filter_allows(can_id):
            self.hidden_count += 1
            return
        if not self.search_allows(direction, can_id, dlc, period, data, raw):
            self.hidden_count += 1
            return
        if self.pause_view_var.get():
            self.paused_count += 1
            return
        now = dt.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        label = self.description_for_id(can_id)
        count = self.id_stats.get(can_id, {}).get("count", "") if can_id else ""
        if direction == "AUTO":
            tag = "AUTO"
        elif direction in ("OK", "ERR", "TX"):
            tag = direction
        elif can_id and not label:
            tag = "UNKNOWN"
        else:
            tag = "RX"
        if extra_tag:
            tag = extra_tag
        item = self.table.insert("", 0, values=(now, direction, can_id, dlc, period, count, label, data, raw), tags=(tag,))
        if self.autoscroll_var.get():
            self.table.see(item)
        children = self.table.get_children()
        if len(children) > 1000:
            self.table.delete(children[-1])

    def update_latest_row(self, can_id, period, data):
        stat = self.id_stats.get(can_id, {})
        rate = ""
        if period.endswith(" ms"):
            try:
                period_ms = float(period[:-3])
                if period_ms > 0.0:
                    rate = f"{1000.0 / period_ms:.1f} fps"
            except ValueError:
                pass
        values = (
            can_id,
            stat.get("count", ""),
            period,
            rate,
            self.description_for_id(can_id),
            data,
            stat.get("last_time", ""),
        )
        item_id = can_id.replace("0x", "id_")
        if self.latest_table.exists(item_id):
            self.latest_table.item(item_id, values=values)
        else:
            self.latest_table.insert("", "end", iid=item_id, values=values)

    def select_latest_id(self, _event=None):
        selected = self.latest_table.selection()
        if not selected:
            return
        values = self.latest_table.item(selected[0], "values")
        if values:
            self.select_graph_id(values[0])

    def show_selected_frame_details(self, _event=None):
        selected = self.table.selection()
        if not selected:
            return
        values = self.table.item(selected[0], "values")
        if len(values) < 9:
            return
        _time, direction, can_id, dlc, period, _count, _label, data, raw = values
        if can_id and direction == "RX":
            self.select_graph_id(can_id)
        self.set_details_text(self.describe_frame(direction, can_id, dlc, period, data, raw))

    def record_graph_frame(self, can_id, device_timestamp_ms, dlc, data):
        history = self.frame_history.setdefault(can_id, collections.deque(maxlen=5000))
        history.append((device_timestamp_ms, time.monotonic(), dlc, tuple(data)))
        known_ids = tuple(sorted(self.frame_history, key=lambda value: int(value, 16)))
        self.graph_id_combo["values"] = known_ids
        if not self.graph_id_var.get() or self.graph_id_var.get() not in self.frame_history:
            self.select_graph_id(can_id)
        if self.graph_running and can_id == self.graph_id_var.get() and not self.graph_update_pending:
            self.graph_update_pending = True
            self.root.after(200, self.refresh_trend_graph)

    def select_graph_id(self, can_id):
        if not can_id:
            return
        self.graph_id_var.set(can_id)
        self.update_graph_signal_choices()
        self.draw_trend_graph()

    def on_graph_id_changed(self, _event=None):
        self.update_graph_signal_choices()
        self.draw_trend_graph()

    def update_graph_signal_choices(self):
        choices = [f"B{index}" for index in range(8)]
        self.graph_dbc_signal_names = {}
        try:
            can_id = int(self.graph_id_var.get(), 16)
        except ValueError:
            can_id = None
        if can_id is not None:
            for name, unit in self.dbc.signal_choices(can_id):
                display = f"DBC: {name}" + (f" [{unit}]" if unit else "")
                choices.append(display)
                self.graph_dbc_signal_names[display] = name
        self.graph_signal_combo["values"] = tuple(choices)
        if self.graph_signal_var.get() not in choices:
            self.graph_signal_var.set("B0")

    def graph_window_seconds(self):
        try:
            value = float(self.graph_window_var.get())
        except ValueError:
            value = 10.0
        value = max(1.0, min(3600.0, value))
        self.graph_window_var.set(f"{value:g}")
        return value

    def graph_points(self):
        can_id_text = self.graph_id_var.get()
        history = list(self.frame_history.get(can_id_text, ()))
        if not history:
            return [], "", None, None
        window = self.graph_window_seconds()
        last_device_time = history[-1][0]
        last_host_time = history[-1][1]
        candidates = []
        for device_time, host_time, dlc, data in history:
            if last_device_time is not None and device_time is not None:
                age = ((last_device_time - device_time) & 0xFFFFFFFF) / 1000.0
            else:
                age = last_host_time - host_time
            if 0.0 <= age <= window:
                candidates.append((-age, dlc, data))
        if len(candidates) > 1200:
            step = (len(candidates) + 1199) // 1200
            reduced = candidates[::step]
            if reduced[-1] != candidates[-1]:
                reduced.append(candidates[-1])
            candidates = reduced

        source = self.graph_signal_var.get()
        points = []
        unit = "decimal"
        dbc_minimum = None
        dbc_maximum = None
        if source.startswith("B") and len(source) == 2 and source[1].isdigit():
            byte_index = int(source[1])
            for sample_time, dlc, data in candidates:
                if byte_index < dlc:
                    points.append((sample_time, float(data[byte_index])))
        else:
            signal_name = self.graph_dbc_signal_names.get(source)
            if signal_name:
                can_id = int(can_id_text, 16)
                for sample_time, _dlc, data in candidates:
                    decoded = self.dbc.decode_signal(can_id, data, signal_name)
                    if decoded is not None:
                        value, unit, dbc_minimum, dbc_maximum = decoded
                        points.append((sample_time, value))
        return points, unit, dbc_minimum, dbc_maximum

    def draw_trend_graph(self):
        canvas = self.graph_canvas
        canvas.delete("all")
        width = max(420, canvas.winfo_width())
        height = max(260, canvas.winfo_height())
        left, right, top, bottom = 72, 24, 48, 54
        plot_width = width - left - right
        plot_height = height - top - bottom
        can_id = self.graph_id_var.get()
        source = self.graph_signal_var.get()
        window = self.graph_window_seconds()

        canvas.create_text(
            left, 20, anchor="w", fill="#e7eaf0", font=("Segoe UI", 11, "bold"),
            text=f"{can_id or self.tr('graph.no_id')}  |  {source}",
        )
        canvas.create_line(left, top, left, top + plot_height, fill="#68717f")
        canvas.create_line(left, top + plot_height, left + plot_width, top + plot_height, fill="#68717f")

        points, unit, dbc_minimum, dbc_maximum = self.graph_points()
        values = [value for _sample_time, value in points]
        if values:
            y_min = min(values)
            y_max = max(values)
        else:
            y_min, y_max = 0.0, 255.0

        if not self.graph_auto_scale_var.get() and source.startswith("B"):
            y_min, y_max = 0.0, 255.0
        elif not self.graph_auto_scale_var.get() and dbc_minimum is not None and dbc_maximum is not None:
            y_min, y_max = float(dbc_minimum), float(dbc_maximum)
        else:
            if y_min == y_max:
                padding = max(1.0, abs(y_min) * 0.05)
            else:
                padding = (y_max - y_min) * 0.08
            y_min -= padding
            y_max += padding

        if y_max <= y_min:
            y_max = y_min + 1.0

        for index in range(6):
            ratio = index / 5.0
            x = left + ratio * plot_width
            elapsed = -window + ratio * window
            canvas.create_line(x, top, x, top + plot_height, fill="#242a33")
            canvas.create_text(x, top + plot_height + 18, fill="#9ca3ad", text=f"{elapsed:.1f}s")
            y = top + plot_height - ratio * plot_height
            tick_value = y_min + ratio * (y_max - y_min)
            canvas.create_line(left, y, left + plot_width, y, fill="#242a33")
            canvas.create_text(left - 10, y, anchor="e", fill="#9ca3ad", text=f"{tick_value:.2f}")

        canvas.create_text(
            16, top + plot_height / 2, angle=90, fill="#9ca3ad",
            text=unit or self.tr("graph.value"),
        )
        canvas.create_text(
            left + plot_width / 2, height - 12, fill="#9ca3ad", text=self.tr("graph.relative_time")
        )

        if len(points) >= 2:
            coordinates = []
            for sample_time, value in points:
                x = left + ((sample_time + window) / window) * plot_width
                y = top + plot_height - ((value - y_min) / (y_max - y_min)) * plot_height
                coordinates.extend((x, y))
            canvas.create_line(*coordinates, fill="#d2ad58", width=2, smooth=False)
            last_x, last_y = coordinates[-2], coordinates[-1]
            canvas.create_oval(last_x - 3, last_y - 3, last_x + 3, last_y + 3, fill="#f4d47b", outline="")
        elif len(points) == 1:
            sample_time, value = points[0]
            x = left + ((sample_time + window) / window) * plot_width
            y = top + plot_height - ((value - y_min) / (y_max - y_min)) * plot_height
            canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#f4d47b", outline="")
        else:
            canvas.create_text(
                left + plot_width / 2, top + plot_height / 2,
                fill="#9ca3ad", text=self.tr("graph.waiting_samples"),
            )

        state = self.tr("graph.running") if self.graph_running else self.tr("graph.paused")
        if values:
            self.graph_status_var.set(self.tr(
                "graph.stats", state=state, points=len(points), current=values[-1], unit=unit,
                minimum=min(values), maximum=max(values),
            ))
        else:
            self.graph_status_var.set(self.tr("graph.no_visible_samples", state=state))

    def refresh_trend_graph(self):
        self.graph_update_pending = False
        if self.graph_running:
            self.draw_trend_graph()

    def start_graph(self):
        self.graph_running = True
        self.draw_trend_graph()

    def pause_graph(self):
        self.graph_running = False
        self.draw_trend_graph()

    def clear_graph(self):
        can_id = self.graph_id_var.get()
        if can_id in self.frame_history:
            self.frame_history[can_id].clear()
        self.draw_trend_graph()

    def load_graph_demo(self):
        can_id = "0x7FE"
        history = collections.deque(maxlen=5000)
        now = time.monotonic()
        for index in range(240):
            value = int(127.5 + 105.0 * math.sin(index / 15.0))
            data = (value, 0, 0, 0, 0, 0, 0, 0)
            history.append((index * 50, now - ((239 - index) * 0.05), 8, data))
        self.frame_history[can_id] = history
        self.graph_id_combo["values"] = tuple(sorted(self.frame_history, key=lambda item: int(item, 16)))
        self.graph_signal_var.set("B0")
        self.graph_window_var.set("10")
        self.graph_running = True
        self.select_graph_id(can_id)
        self.footer_var.set(self.tr("graph.demo_loaded"))

    def describe_frame(self, direction, can_id, dlc, period, data, raw):
        lines = [self.tr("details.type", value=direction), f"ID: {can_id or '-'}", f"DLC: {dlc or '-'}"]
        if can_id:
            lines.append(self.tr(
                "details.description", value=self.description_for_id(can_id) or self.tr("common.unknown_id")
            ))
        if period:
            lines.append(self.tr("details.period", value=period))
        bytes_hex = [part for part in data.split() if part]
        if bytes_hex:
            decimal = []
            binary = []
            for byte in bytes_hex:
                try:
                    value = int(byte, 16)
                except ValueError:
                    continue
                decimal.append(str(value))
                binary.append(format(value, "08b"))
            lines.append(f"HEX: {' '.join(bytes_hex)}")
            lines.append(f"DEC: {' '.join(decimal)}")
            lines.append(f"BIN: {' '.join(binary)}")
            try:
                dbc_text = self.dbc.decode(int(can_id, 16), [int(item, 16) for item in bytes_hex])
            except ValueError:
                dbc_text = ""
            if dbc_text:
                lines.append("")
                lines.append(dbc_text)
        lines.append(self.tr("details.serial", value=raw))
        return "\n".join(lines)

    def set_details_text(self, text):
        self.details_box.configure(state="normal")
        self.details_box.delete("1.0", "end")
        self.details_box.insert("end", text)
        self.details_box.configure(state="disabled")

    def filter_allows(self, can_id):
        wanted = self.normalized_filter_ids()
        return not wanted or can_id in wanted

    def normalized_filter_ids(self):
        text = self.filter_var.get().strip()
        if not text:
            return set()
        values = set()
        for part in text.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start_text, end_text = part.split("-", 1)
                    start = int(normalize_id(start_text), 16)
                    end = int(normalize_id(end_text), 16)
                    if start <= end:
                        values.update(f"0x{can_id:03X}" for can_id in range(start, end + 1))
                except ValueError:
                    pass
                continue
            try:
                normalized = self.normalize_id(part)
            except ValueError:
                continue
            if normalized:
                values.add(normalized)
        return values

    def search_allows(self, direction, can_id, dlc, period, data, raw):
        query = self.search_var.get().strip().lower()
        if not query:
            return True
        haystack = " ".join(
            [
                direction,
                can_id,
                dlc,
                period,
                self.description_for_id(can_id),
                data,
                raw,
            ]
        ).lower()
        return query in haystack

    def normalize_id(self, value):
        value = str(value).strip()
        if not value:
            return ""
        if value.lower().startswith("0x"):
            value = value[2:]
        return f"0x{int(value, 16):03X}"

    def description_for_id(self, can_id):
        return self.profile_ids.get(can_id, "")

    def update_period(self, can_id, device_timestamp_ms=None):
        if device_timestamp_ms is not None:
            previous_device = self.last_device_time_by_id.get(can_id)
            self.last_device_time_by_id[can_id] = device_timestamp_ms
            if previous_device is None:
                return ""
            elapsed = (device_timestamp_ms - previous_device) & 0xFFFFFFFF
            return f"{elapsed:.1f} ms"
        now = dt.datetime.now()
        previous = self.last_rx_time_by_id.get(can_id)
        self.last_rx_time_by_id[can_id] = now
        if previous is None:
            return ""
        period_ms = (now - previous).total_seconds() * 1000.0
        return f"{period_ms:.1f} ms"

    def clear_screen(self):
        for item in self.table.get_children():
            self.table.delete(item)
        self.rx_count = 0
        self.tx_count = 0
        self.hidden_count = 0
        self.paused_count = 0
        self.id_stats.clear()
        self.last_rx_time_by_id.clear()
        self.last_device_time_by_id.clear()
        self.frame_history.clear()
        self.graph_id_var.set("")
        self.graph_id_combo["values"] = ()
        self.update_graph_signal_choices()
        for item in self.latest_table.get_children():
            self.latest_table.delete(item)
        self.set_details_text("")
        self.draw_rate_chart()
        self.draw_trend_graph()
        self.footer_var.set(self.tr("status.graph_cleared"))
        self.update_summary()

    def copy_selected_row(self, _event=None):
        selected = self.table.selection()
        if not selected:
            self.footer_var.set(self.tr("status.no_copy"))
            return
        values = self.table.item(selected[0], "values")
        text = "\t".join(str(value) for value in values)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.footer_var.set(self.tr("status.copied"))

    def update_summary(self):
        device = self.device_status
        can_state = f"{device.state}/{device.mode}" if device else self.tr("summary.no_telemetry")
        can_errors = f"TEC/REC: {device.tec}/{device.rec}" if device else "TEC/REC: -/-"
        firmware_losses = (
            self.tr("summary.firmware_losses", queue=device.dropped, can=device.message_lost)
            if device else self.tr("summary.no_firmware_losses")
        )
        text = self.tr(
            "summary.content",
            status=self.status_var.get(), device=self.device_name, protocol=self.protocol_version,
            profile=self.profile.get("profile_name", "-"), rx=self.rx_count, tx=self.tx_count,
            hidden=self.hidden_count, paused=self.paused_count, pc_losses=self.queue_dropped,
            firmware_losses=firmware_losses, can_state=can_state, can_errors=can_errors,
            port=self.port_var.get() or "-", baud=self.baud_var.get(),
            can_baud=self.profile.get("baudrate_can", "-"),
            filter_value=self.filter_var.get() or self.tr("common.all"),
            direction=self.direction_filter_var.get(),
            auto_response=self.tr("state.on") if self.auto_response_var.get() else self.tr("state.off"),
            csv=self.csv_var.get(),
        )
        self.summary.configure(state="normal")
        self.summary.delete("1.0", "end")
        self.summary.insert("end", text)
        self.summary.configure(state="disabled")

        counter_lines = []
        for can_id, stat in sorted(self.id_stats.items()):
            counter_lines.append(
                f"{can_id} {stat['count']:5d} {stat['period']:>9} {stat['last_time']:>12}\n"
                f"  {self.description_for_id(can_id) or self.tr('common.unknown_id')}\n"
                f"  {stat['data']}"
            )
        self.id_counter_box.configure(state="normal")
        self.id_counter_box.delete("1.0", "end")
        self.id_counter_box.insert("end", "\n\n".join(counter_lines))
        self.id_counter_box.configure(state="disabled")
        self.draw_rate_chart()

    def send_control_command(self, command):
        if not self.serial_port or not self.serial_port.is_open:
            return False
        try:
            self.serial_port.write(command.encode("ascii"))
            return True
        except Exception:
            return False

    def set_listen_only(self):
        if self.protocol_version < 2:
            if self.serial_port and self.serial_port.is_open:
                messagebox.showwarning(self.tr("dialog.listen_only"), self.tr("dialog.listen_only_v2"))
            return
        enabled = 1 if self.listen_only_var.get() else 0
        self.send_control_command(f"SET,LISTEN,{enabled}\n")

    def poll_device_status(self):
        if self.protocol_version >= 2:
            self.send_control_command("GET,STATUS\n")
        self.root.after(1000, self.poll_device_status)

    def choose_dbc(self):
        path = filedialog.askopenfilename(
            title=self.tr("dialog.load_dbc"),
            filetypes=[(self.tr("file.can_database"), "*.dbc"), (self.tr("file.all"), "*.*")],
        )
        if not path:
            return
        try:
            self.dbc.load(Path(path))
        except DBCError as exc:
            detail = self.tr("dialog.cantools_install") if str(exc) == "cantools_missing" else str(exc)
            messagebox.showerror("DBC", self.tr("dialog.dbc_failed", error=detail))
            return
        self.footer_var.set(self.tr("status.dbc_loaded", name=Path(path).name))
        self.update_graph_signal_choices()
        self.draw_trend_graph()

    def choose_and_replay_capture(self):
        if not self.serial_port or not self.serial_port.is_open:
            messagebox.showwarning("Replay", self.tr("dialog.connect_first"))
            return
        path = filedialog.askopenfilename(
            title=self.tr("dialog.select_csv"),
            initialdir=str(LOGS_DIR if LOGS_DIR.exists() else APP_DIR),
            filetypes=[("CSV", "*.csv"), (self.tr("file.all"), "*.*")],
        )
        if not path:
            return
        try:
            frames = read_capture(path)
        except OSError as exc:
            messagebox.showerror("Replay", str(exc))
            return
        if not frames:
            messagebox.showwarning("Replay", self.tr("dialog.replay_no_frames"))
            return
        if not messagebox.askyesno(
            self.tr("dialog.confirm_replay"),
            self.tr("dialog.replay_warning", count=len(frames)),
        ):
            return
        self.cancel_replay()
        for delay, (_timestamp, can_id, dlc, data) in zip(replay_delays(frames, 10), frames):
            job = self.root.after(delay, lambda cid=can_id, length=dlc, payload=data: self.send_tx_values(
                f"{cid:03X}", str(length), [f"{value:02X}" for value in payload], manual=False
            ))
            self.replay_jobs.append(job)
        self.footer_var.set(self.tr("status.replay_scheduled", count=len(frames), name=Path(path).name))

    def cancel_replay(self):
        for job in self.replay_jobs:
            try:
                self.root.after_cancel(job)
            except (ValueError, tk.TclError):
                pass
        self.replay_jobs.clear()

    def draw_rate_chart(self):
        self.rate_canvas.delete("all")
        if not self.id_stats:
            self.rate_canvas.create_text(10, 12, anchor="nw", fill="#8a9099", text=self.tr("chart.no_rx"))
            return

        width = max(260, self.rate_canvas.winfo_width() - 18)
        rows = []
        max_rate = 0.0
        for can_id, stat in sorted(self.id_stats.items()):
            rate = 0.0
            period_text = stat.get("period", "")
            if period_text.endswith(" ms"):
                try:
                    period_ms = float(period_text[:-3])
                    if period_ms > 0.0:
                        rate = 1000.0 / period_ms
                except ValueError:
                    rate = 0.0
            rows.append((can_id, rate))
            max_rate = max(max_rate, rate)

        y = 8
        for can_id, rate in rows[:5]:
            bar_width = 0 if max_rate == 0.0 else int((rate / max_rate) * (width - 92))
            self.rate_canvas.create_text(8, y + 8, anchor="w", fill="#e7eaf0", text=can_id)
            self.rate_canvas.create_rectangle(72, y, 72 + bar_width, y + 16, fill="#d2ad58", outline="")
            self.rate_canvas.create_text(width, y + 8, anchor="e", fill="#e7eaf0", text=f"{rate:.1f} fps")
            y += 18

    def toggle_csv(self):
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None
            self.csv_var.set(self.tr("status.csv_off"))
            self.update_summary()
            return
        path = filedialog.asksaveasfilename(
            title=self.tr("dialog.save_csv"),
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), (self.tr("file.all"), "*.*")],
        )
        if path:
            self.open_csv(Path(path))

    def start_auto_csv(self):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        profile_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", self.profile.get("profile_name", "generic")).strip("._")
        profile_name = profile_name or "generic"
        self.open_csv(LOGS_DIR / f"can_log_{profile_name}_{timestamp}.csv")

    def export_visible_rows(self):
        path = filedialog.asksaveasfilename(
            title=self.tr("dialog.export_rows"),
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), (self.tr("file.all"), "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8") as export_file:
                writer = csv.writer(export_file)
                writer.writerow(["time", "type", "id", "dlc", "period", "count", "description", "data", "raw"])
                for item in self.table.get_children():
                    writer.writerow(self.table.item(item, "values"))
        except OSError as exc:
            messagebox.showerror(self.tr("dialog.csv_error"), self.tr("dialog.csv_export_failed", error=exc))
            return

        self.footer_var.set(self.tr("status.rows_exported", path=path))

    def export_candump(self):
        path = filedialog.asksaveasfilename(
            title=self.tr("dialog.export_candump"),
            defaultextension=".log",
            filetypes=[("candump log", "*.log"), (self.tr("file.all"), "*.*")],
        )
        if not path:
            return
        lines = []
        relative_seconds = 0.0
        for item in reversed(self.table.get_children()):
            values = self.table.item(item, "values")
            if len(values) < 9 or values[1] not in ("RX", "TX", "AUTO") or not values[2]:
                continue
            can_id = values[2].replace("0x", "").upper()
            payload = "".join(values[7].split()[:int(values[3])])
            lines.append(f"({relative_seconds:.6f}) can0 {can_id}#{payload}")
            relative_seconds += 0.001
        try:
            Path(path).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="ascii")
        except OSError as exc:
            messagebox.showerror(self.tr("dialog.export_candump"), str(exc))
            return
        self.footer_var.set(self.tr("status.candump_exported", count=len(lines)))

    def open_csv(self, path):
        if self.csv_file:
            self.csv_file.close()
        try:
            self.csv_file = open(path, "a", newline="", encoding="utf-8")
        except OSError as exc:
            self.csv_file = None
            self.csv_writer = None
            messagebox.showerror(
                self.tr("dialog.csv_error"), self.tr("dialog.csv_open_failed", path=path, error=exc)
            )
            return False
        self.csv_writer = csv.writer(self.csv_file)
        if self.csv_file.tell() == 0:
            self.csv_writer.writerow([
                "timestamp", "device_timestamp_ms", "type", "id", "dlc",
                "period", "description", "data", "raw",
            ])
        self.csv_var.set(f"CSV: {path}")
        self.footer_var.set(self.tr("status.csv_active", path=path))
        self.update_summary()
        return True

    def write_csv(self, direction, can_id, dlc, period, description, data, raw, device_timestamp_ms=""):
        if not self.csv_writer:
            return
        self.csv_writer.writerow([
            dt.datetime.now().isoformat(timespec="milliseconds"),
            "" if device_timestamp_ms is None else device_timestamp_ms,
            direction, can_id, dlc, period, description, data, raw,
        ])
        self.csv_file.flush()

    def load_config(self):
        return app_config.load_config()

    def on_language_changed(self, _event=None):
        selected_label = self.language_display_var.get()
        self.language_var.set(next(
            (code for code, label in self.language_labels.items() if label == selected_label), "auto"
        ))
        self.save_config()
        messagebox.showinfo(
            self.tr("language.restart_title"),
            self.tr("language.restart_message"),
        )

    def save_config(self):
        self.update_tx_slot_visibility()
        profile_path = ""
        if self.profile_path:
            try:
                profile_path = self.profile_path.resolve().relative_to(APP_DIR.resolve()).as_posix()
            except ValueError:
                profile_path = str(self.profile_path)
        data = {
            "language": self.language_var.get(),
            "port": self.port_var.get(),
            "baud": self.baud_var.get(),
            "filter": self.filter_var.get(),
            "search": self.search_var.get(),
            "direction_filter": (
                "ALL" if self.direction_filter_var.get() == self.tr("common.all")
                else self.direction_filter_var.get()
            ),
            "autoscroll": self.autoscroll_var.get(),
            "pause_view": self.pause_view_var.get(),
            "auto_response": self.auto_response_var.get(),
            "listen_only": self.listen_only_var.get(),
            "graph_id": self.graph_id_var.get(),
            "graph_signal": self.graph_signal_var.get(),
            "graph_window": self.graph_window_seconds(),
            "graph_auto_scale": self.graph_auto_scale_var.get(),
            "profile_path": profile_path,
            "geometry": self.root.geometry(),
            "tx_slot_count": self.tx_slot_count(),
            "selected_tx_slot": self.selected_tx_slot_var.get(),
            "tx_slots": [
                {
                    "id": slot["id"].get(),
                    "dlc": slot["dlc"].get(),
                    "data": [var.get() for var in slot["data"]],
                }
                for slot in self.tx_slots
            ],
        }
        try:
            app_config.save_config(data)
        except OSError:
            pass

    def on_close(self):
        self.cancel_replay()
        self.save_config()
        self.disconnect()
        if self.csv_file:
            self.csv_file.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    CANAnalyzerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
