import os
import re
import threading
import subprocess
from typing import Dict, Any, List, Optional
import customtkinter as ctk
from tkinter import filedialog, messagebox

from downloader.detector import PlatformDetector, Platform
from downloader.universal_extractor import UniversalExtractor
from downloader.universal_downloader import UniversalDownloader
from downloader.queue_manager import QueueManager
from downloader.api import TikTokDramaAPI


class UniversalDownloaderApp(ctk.CTk):
    """
    Universal Social Media & Short Drama Downloader GUI.
    Aesthetic: Muted Sage Grey & Warm Cream Beige typography (strictly no icons).
    """

    # Swatch Card Combination: Muted Sage Grey (#A5A79B) & Warm Cream Beige (#E8D2B5)
    BG_COLOR = "#A5A79B"
    PANEL_BG = "#E8D2B5"
    WELL_BG = "#F5EAE0"
    BORDER_COLOR = "#8E9183"
    ACCENT_SAGE = "#A5A79B"
    ACCENT_HOVER = "#8E9183"
    BTN_SEC_BG = "#DFCAAC"
    BTN_SEC_HOVER = "#CBB18F"
    TEXT_CREAM = "#232822"
    TEXT_CREAM_MUTED = "#555A51"
    TEXT_CREAM_SUBTLE = "#6F7265"

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("Universal Video Downloader")
        self.geometry("1060 x 820")
        self.minsize(940, 680)

        # Set appearance
        ctk.set_appearance_mode("Dark")
        self.configure(fg_color=self.BG_COLOR)

        # Core logic instances
        self.detector = PlatformDetector()
        self.extractor = UniversalExtractor()
        self.universal_downloader = UniversalDownloader()
        self.queue_manager = QueueManager()

        # State tracking
        self.current_metadata: Optional[Dict[str, Any]] = None
        self.active_mode: str = "empty"
        self.base_download_dir = os.path.abspath(os.path.join(os.getcwd(), "Downloads"))
        self.current_dest_folder = self.base_download_dir
        self.episode_checkboxes: List[Dict[str, Any]] = []

        # Setup QueueManager callbacks (for Batch/Drama Mode)
        self._setup_queue_callbacks()

        # Build UI layout
        self._build_ui()

        # Setup real-time URL detection listener
        self.url_var.trace_add("write", self._on_url_text_changed)

    # =========================================================================
    # UI CONSTRUCTION
    # =========================================================================

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ---------------- 1. TOP HEADER & BRANDING ----------------
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=24, pady=(16, 8), sticky="ew")

        title_label = ctk.CTkLabel(
            header_frame,
            text="Universal Downloader",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.TEXT_CREAM
        )
        title_label.pack(side="left")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="YouTube • TikTok Dramas • Instagram • Facebook • X • Reddit",
            font=ctk.CTkFont(size=12),
            text_color=self.TEXT_CREAM_SUBTLE
        )
        subtitle_label.pack(side="right", pady=4)

        # ---------------- 2. URL INPUT & DETECTOR BAR ----------------
        input_container = ctk.CTkFrame(self, fg_color=self.PANEL_BG, corner_radius=10, border_width=1, border_color=self.BORDER_COLOR)
        input_container.grid(row=1, column=0, padx=24, pady=8, sticky="ew")
        input_container.grid_columnconfigure(1, weight=1)

        # Platform badge indicator (Auto-updates in real time, no icons)
        self.platform_badge = ctk.CTkButton(
            input_container,
            text="Auto-Detect",
            width=140,
            height=38,
            corner_radius=8,
            fg_color=self.BTN_SEC_BG,
            hover_color=self.BTN_SEC_HOVER,
            text_color=self.TEXT_CREAM,
            font=ctk.CTkFont(size=12, weight="bold"),
            state="disabled"
        )
        self.platform_badge.grid(row=0, column=0, padx=(12, 8), pady=12)

        # URL Text Entry
        self.url_var = ctk.StringVar()
        self.url_entry = ctk.CTkEntry(
            input_container,
            textvariable=self.url_var,
            placeholder_text="Paste YouTube, TikTok (video/drama), Instagram, Facebook, or X link...",
            height=38,
            fg_color=self.WELL_BG,
            border_color=self.BORDER_COLOR,
            text_color=self.TEXT_CREAM,
            placeholder_text_color=self.TEXT_CREAM_SUBTLE,
            font=ctk.CTkFont(size=13)
        )
        self.url_entry.grid(row=0, column=1, padx=6, pady=12, sticky="ew")
        self.url_entry.bind("<Return>", lambda e: self._on_fetch_clicked())

        # Paste Button (No Icons)
        self.paste_btn = ctk.CTkButton(
            input_container,
            text="Paste",
            width=75,
            height=38,
            fg_color=self.BTN_SEC_BG,
            hover_color=self.BTN_SEC_HOVER,
            text_color=self.TEXT_CREAM,
            font=ctk.CTkFont(size=13),
            command=self._on_paste_clicked
        )
        self.paste_btn.grid(row=0, column=2, padx=4, pady=12)

        # Clear Button (No Icons)
        self.clear_btn = ctk.CTkButton(
            input_container,
            text="Clear",
            width=75,
            height=38,
            fg_color=self.BTN_SEC_BG,
            hover_color=self.BTN_SEC_HOVER,
            text_color=self.TEXT_CREAM,
            font=ctk.CTkFont(size=13),
            command=self._on_clear_clicked
        )
        self.clear_btn.grid(row=0, column=3, padx=4, pady=12)

        # Fetch Button (No Icons)
        self.fetch_btn = ctk.CTkButton(
            input_container,
            text="Analyze",
            width=110,
            height=38,
            fg_color=self.ACCENT_SAGE,
            hover_color=self.ACCENT_HOVER,
            text_color=self.TEXT_CREAM,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_fetch_clicked
        )
        self.fetch_btn.grid(row=0, column=4, padx=(4, 12), pady=12)

        # ---------------- 3. ADAPTIVE CONTENT WORKSPACE ----------------
        self.content_area = ctk.CTkFrame(self, fg_color=self.PANEL_BG, corner_radius=10, border_width=1, border_color=self.BORDER_COLOR)
        self.content_area.grid(row=2, column=0, padx=24, pady=8, sticky="nsew")
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)

        # Create sub-views inside content area:
        self._build_empty_view()
        self._build_single_video_view()
        self._build_batch_drama_view()

        # Default to empty view
        self._switch_mode("empty")

        # ---------------- 4. GLOBAL BOTTOM STATUS BAR ----------------
        status_bar = ctk.CTkFrame(self, height=32, fg_color="transparent")
        status_bar.grid(row=3, column=0, padx=24, pady=(4, 10), sticky="ew")
        status_bar.grid_columnconfigure(0, weight=1)

        self.global_status_label = ctk.CTkLabel(
            status_bar,
            text="Ready. Paste a link to begin.",
            font=ctk.CTkFont(size=12),
            text_color=self.TEXT_CREAM_SUBTLE,
            anchor="w"
        )
        self.global_status_label.grid(row=0, column=0, sticky="w")

        self.dest_folder_hint = ctk.CTkLabel(
            status_bar,
            text=f"Save path: {self.base_download_dir}",
            font=ctk.CTkFont(size=11),
            text_color=self.TEXT_CREAM_SUBTLE,
            anchor="e"
        )
        self.dest_folder_hint.grid(row=0, column=1, sticky="e")

    # =========================================================================
    # SUB-VIEW BUILDERS
    # =========================================================================

    def _build_empty_view(self):
        """Displays when no URL has been analyzed yet."""
        self.empty_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.empty_frame.grid(row=0, column=0, sticky="nsew")
        self.empty_frame.grid_columnconfigure(0, weight=1)
        self.empty_frame.grid_rowconfigure(0, weight=1)

        center_box = ctk.CTkFrame(self.empty_frame, fg_color="transparent")
        center_box.grid(row=0, column=0)

        ctk.CTkLabel(
            center_box,
            text="Universal Downloader",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.TEXT_CREAM
        ).pack(pady=(0, 6))

        ctk.CTkLabel(
            center_box,
            text="Paste any video or drama link above.\nThe platform is detected automatically in real-time.",
            font=ctk.CTkFont(size=13),
            text_color=self.TEXT_CREAM_MUTED,
            justify="center"
        ).pack(pady=(0, 18))

        # Supported chips (No icons, pure sage and cream)
        badges_row = ctk.CTkFrame(center_box, fg_color="transparent")
        badges_row.pack(pady=4)

        for text in [
            "YouTube",
            "TikTok (Video / Drama)",
            "Instagram Reels",
            "Facebook",
            "X / Twitter",
            "Reddit"
        ]:
            ctk.CTkLabel(
                badges_row,
                text=f"  {text}  ",
                fg_color=self.BTN_SEC_BG,
                corner_radius=6,
                font=ctk.CTkFont(size=11),
                text_color=self.TEXT_CREAM_MUTED
            ).pack(side="left", padx=4)

    def _build_single_video_view(self):
        """Card view for YouTube, Instagram, Facebook, X, and standalone TikTok videos."""
        self.single_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.single_frame.grid_columnconfigure(0, weight=1)

        # Video Information Box
        info_card = ctk.CTkFrame(self.single_frame, fg_color=self.WELL_BG, corner_radius=10, border_width=1, border_color=self.BORDER_COLOR)
        info_card.grid(row=0, column=0, padx=20, pady=16, sticky="ew")
        info_card.grid_columnconfigure(1, weight=1)

        self.single_title_lbl = ctk.CTkLabel(
            info_card,
            text="Video Title Placeholder",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.TEXT_CREAM,
            anchor="w",
            wraplength=680,
            justify="left"
        )
        self.single_title_lbl.grid(row=0, column=1, sticky="w", padx=16, pady=(16, 4))

        self.single_author_lbl = ctk.CTkLabel(
            info_card,
            text="Creator • Duration: --:--",
            font=ctk.CTkFont(size=12),
            text_color=self.TEXT_CREAM_MUTED,
            anchor="w"
        )
        self.single_author_lbl.grid(row=1, column=1, sticky="w", padx=16, pady=(0, 16))

        # Destination Folder Selector
        dest_card = ctk.CTkFrame(self.single_frame, fg_color=self.WELL_BG, corner_radius=10, border_width=1, border_color=self.BORDER_COLOR)
        dest_card.grid(row=1, column=0, padx=20, pady=8, sticky="ew")
        dest_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(dest_card, text="Save To:", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.TEXT_CREAM).grid(row=0, column=0, padx=(16, 8), pady=12)
        self.single_dest_entry = ctk.CTkEntry(dest_card, height=32, font=ctk.CTkFont(size=12), fg_color=self.PANEL_BG, border_color=self.BORDER_COLOR, text_color=self.TEXT_CREAM)
        self.single_dest_entry.grid(row=0, column=1, padx=6, pady=12, sticky="ew")
        self.single_dest_entry.insert(0, self.base_download_dir)

        ctk.CTkButton(
            dest_card,
            text="Browse...",
            width=80,
            height=32,
            fg_color=self.BTN_SEC_BG,
            hover_color=self.BTN_SEC_HOVER,
            text_color=self.TEXT_CREAM,
            command=self._on_browse_dest_single
        ).grid(row=0, column=2, padx=6, pady=12)

        ctk.CTkButton(
            dest_card,
            text="Open Folder",
            width=90,
            height=32,
            fg_color=self.BTN_SEC_BG,
            hover_color=self.BTN_SEC_HOVER,
            text_color=self.TEXT_CREAM,
            command=self._on_open_dest_folder
        ).grid(row=0, column=3, padx=(6, 16), pady=12)

        # Quality / Format Picker & Action Frame
        action_card = ctk.CTkFrame(self.single_frame, fg_color=self.WELL_BG, corner_radius=10, border_width=1, border_color=self.BORDER_COLOR)
        action_card.grid(row=2, column=0, padx=20, pady=8, sticky="ew")
        action_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            action_card,
            text="Format & Quality:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.TEXT_CREAM
        ).grid(row=0, column=0, padx=(16, 8), pady=16)

        self.format_dropdown = ctk.CTkOptionMenu(
            action_card,
            values=["Best Video + Audio", "720p HD", "480p", "MP3 Audio (320kbps)"],
            width=320,
            height=36,
            fg_color=self.PANEL_BG,
            button_color=self.ACCENT_SAGE,
            button_hover_color=self.ACCENT_HOVER,
            text_color=self.TEXT_CREAM,
            font=ctk.CTkFont(size=13)
        )
        self.format_dropdown.grid(row=0, column=1, padx=6, pady=16, sticky="w")

        # Download & Cancel Buttons (No Icons)
        self.single_dl_btn = ctk.CTkButton(
            action_card,
            text="Download",
            width=130,
            height=36,
            fg_color=self.ACCENT_SAGE,
            hover_color=self.ACCENT_HOVER,
            text_color=self.TEXT_CREAM,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_single_download_clicked
        )
        self.single_dl_btn.grid(row=0, column=2, padx=6, pady=16)

        self.single_stop_btn = ctk.CTkButton(
            action_card,
            text="Cancel",
            width=80,
            height=36,
            fg_color=self.BTN_SEC_BG,
            hover_color=self.BTN_SEC_HOVER,
            text_color=self.TEXT_CREAM_MUTED,
            font=ctk.CTkFont(size=13),
            state="disabled",
            command=self._on_single_stop_clicked
        )
        self.single_stop_btn.grid(row=0, column=3, padx=(6, 16), pady=16)

        # Progress Display
        prog_card = ctk.CTkFrame(self.single_frame, fg_color=self.WELL_BG, corner_radius=10, border_width=1, border_color=self.BORDER_COLOR)
        prog_card.grid(row=3, column=0, padx=20, pady=16, sticky="ew")
        prog_card.grid_columnconfigure(0, weight=1)

        self.single_progress_label = ctk.CTkLabel(
            prog_card,
            text="Ready to download.",
            font=ctk.CTkFont(size=13),
            text_color=self.TEXT_CREAM_MUTED,
            anchor="w"
        )
        self.single_progress_label.grid(row=0, column=0, padx=16, pady=(12, 4), sticky="w")

        self.single_speed_label = ctk.CTkLabel(
            prog_card,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=self.TEXT_CREAM_SUBTLE,
            anchor="e"
        )
        self.single_speed_label.grid(row=0, column=1, padx=16, pady=(12, 4), sticky="e")

        self.single_progress_bar = ctk.CTkProgressBar(prog_card, height=10, progress_color=self.ACCENT_SAGE, fg_color=self.PANEL_BG)
        self.single_progress_bar.grid(row=1, column=0, columnspan=2, padx=16, pady=(4, 16), sticky="ew")
        self.single_progress_bar.set(0)

    def _build_batch_drama_view(self):
        """Multi-episode batch download manager for TikTok Short Dramas & Playlists."""
        self.batch_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.batch_frame.grid_columnconfigure(0, weight=1)
        self.batch_frame.grid_rowconfigure(2, weight=1)

        # Drama / Playlist Header Info
        top_meta = ctk.CTkFrame(self.batch_frame, fg_color=self.WELL_BG, corner_radius=10, border_width=1, border_color=self.BORDER_COLOR)
        top_meta.grid(row=0, column=0, padx=20, pady=(12, 6), sticky="ew")
        top_meta.grid_columnconfigure(1, weight=1)

        self.drama_title_label = ctk.CTkLabel(
            top_meta,
            text="Short Drama Series Title",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.TEXT_CREAM,
            anchor="w"
        )
        self.drama_title_label.grid(row=0, column=0, columnspan=2, padx=16, pady=(10, 2), sticky="w")

        self.drama_stats_label = ctk.CTkLabel(
            top_meta,
            text="Found 0 Episodes • Ready to download",
            font=ctk.CTkFont(size=12),
            text_color=self.TEXT_CREAM_MUTED,
            anchor="w"
        )
        self.drama_stats_label.grid(row=1, column=0, padx=16, pady=(0, 10), sticky="w")

        # Destination Folder Selector for Drama
        dest_card = ctk.CTkFrame(top_meta, fg_color="transparent")
        dest_card.grid(row=2, column=0, columnspan=2, padx=16, pady=(0, 10), sticky="ew")
        dest_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(dest_card, text="Save To:", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.TEXT_CREAM).grid(row=0, column=0, padx=(0, 8), pady=4)
        self.batch_dest_entry = ctk.CTkEntry(dest_card, height=30, font=ctk.CTkFont(size=12), fg_color=self.PANEL_BG, border_color=self.BORDER_COLOR, text_color=self.TEXT_CREAM)
        self.batch_dest_entry.grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        self.batch_dest_entry.insert(0, self.base_download_dir)

        ctk.CTkButton(
            dest_card,
            text="Browse...",
            width=76,
            height=30,
            fg_color=self.BTN_SEC_BG,
            hover_color=self.BTN_SEC_HOVER,
            text_color=self.TEXT_CREAM,
            command=self._on_browse_dest_batch
        ).grid(row=0, column=2, padx=4, pady=4)

        ctk.CTkButton(
            dest_card,
            text="Open Folder",
            width=86,
            height=30,
            fg_color=self.BTN_SEC_BG,
            hover_color=self.BTN_SEC_HOVER,
            text_color=self.TEXT_CREAM,
            command=self._on_open_dest_folder
        ).grid(row=0, column=3, padx=(4, 0), pady=4)

        # Batch Selection Toolbar (No Icons)
        toolbar = ctk.CTkFrame(self.batch_frame, fg_color=self.WELL_BG, corner_radius=10, border_width=1, border_color=self.BORDER_COLOR)
        toolbar.grid(row=1, column=0, padx=20, pady=6, sticky="ew")
        toolbar.grid_columnconfigure(8, weight=1)

        ctk.CTkButton(
            toolbar,
            text="Select All",
            width=80,
            height=30,
            fg_color=self.BTN_SEC_BG,
            hover_color=self.BTN_SEC_HOVER,
            text_color=self.TEXT_CREAM,
            command=self._select_all_episodes
        ).grid(row=0, column=0, padx=(12, 4), pady=8)

        ctk.CTkButton(
            toolbar,
            text="Deselect All",
            width=90,
            height=30,
            fg_color=self.BTN_SEC_BG,
            hover_color=self.BTN_SEC_HOVER,
            text_color=self.TEXT_CREAM,
            command=self._deselect_all_episodes
        ).grid(row=0, column=1, padx=4, pady=8)

        ctk.CTkLabel(toolbar, text="Range:", font=ctk.CTkFont(size=12), text_color=self.TEXT_CREAM).grid(row=0, column=2, padx=(10, 4), pady=8)

        self.range_entry = ctk.CTkEntry(toolbar, placeholder_text="e.g. 1-20", width=85, height=30, fg_color=self.PANEL_BG, border_color=self.BORDER_COLOR, text_color=self.TEXT_CREAM)
        self.range_entry.grid(row=0, column=3, padx=4, pady=8)

        ctk.CTkButton(
            toolbar,
            text="Apply",
            width=60,
            height=30,
            fg_color=self.BTN_SEC_BG,
            hover_color=self.BTN_SEC_HOVER,
            text_color=self.TEXT_CREAM,
            command=self._apply_range
        ).grid(row=0, column=4, padx=4, pady=8)

        ctk.CTkLabel(toolbar, text="Delay (s):", font=ctk.CTkFont(size=12), text_color=self.TEXT_CREAM).grid(row=0, column=5, padx=(10, 4), pady=8)
        self.delay_slider = ctk.CTkSlider(toolbar, from_=0.5, to=5.0, number_of_steps=9, width=80, progress_color=self.ACCENT_SAGE)
        self.delay_slider.set(1.5)
        self.delay_slider.grid(row=0, column=6, padx=4, pady=8)

        # Retry Failed Episodes Button (No Icons)
        self.retry_failed_btn = ctk.CTkButton(
            toolbar,
            text="Retry Failed",
            width=100,
            height=30,
            fg_color=self.BTN_SEC_BG,
            hover_color=self.BTN_SEC_HOVER,
            text_color=self.TEXT_CREAM,
            command=self._on_retry_failed_clicked
        )
        self.retry_failed_btn.grid(row=0, column=7, padx=(8, 4), pady=8)

        # Batch Download Action Buttons
        self.batch_pause_btn = ctk.CTkButton(
            toolbar,
            text="Pause",
            width=70,
            height=30,
            fg_color=self.BTN_SEC_BG,
            hover_color=self.BTN_SEC_HOVER,
            text_color=self.TEXT_CREAM,
            state="disabled",
            command=self._on_batch_pause_clicked
        )
        self.batch_pause_btn.grid(row=0, column=9, padx=4, pady=8)

        self.batch_stop_btn = ctk.CTkButton(
            toolbar,
            text="Stop",
            width=70,
            height=30,
            fg_color=self.BTN_SEC_BG,
            hover_color=self.BTN_SEC_HOVER,
            text_color=self.TEXT_CREAM,
            state="disabled",
            command=self._on_batch_stop_clicked
        )
        self.batch_stop_btn.grid(row=0, column=10, padx=4, pady=8)

        self.batch_start_btn = ctk.CTkButton(
            toolbar,
            text="Start Batch",
            width=100,
            height=30,
            fg_color=self.ACCENT_SAGE,
            hover_color=self.ACCENT_HOVER,
            text_color=self.TEXT_CREAM,
            font=ctk.CTkFont(weight="bold"),
            command=self._on_batch_start_clicked
        )
        self.batch_start_btn.grid(row=0, column=11, padx=(4, 12), pady=8)

        # Episode Scrollable Table
        self.episode_scroll = ctk.CTkScrollableFrame(self.batch_frame, fg_color=self.WELL_BG, corner_radius=10)
        self.episode_scroll.grid(row=2, column=0, padx=20, pady=6, sticky="nsew")
        self.episode_scroll.grid_columnconfigure(1, weight=1)

        # Dual Progress Bars
        progress_box = ctk.CTkFrame(self.batch_frame, fg_color=self.WELL_BG, corner_radius=10, border_width=1, border_color=self.BORDER_COLOR)
        progress_box.grid(row=3, column=0, padx=20, pady=(6, 12), sticky="ew")
        progress_box.grid_columnconfigure(1, weight=1)

        self.overall_prog_label = ctk.CTkLabel(
            progress_box,
            text="Overall: 0 / 0 (0%)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.TEXT_CREAM,
            width=150,
            anchor="w"
        )
        self.overall_prog_label.grid(row=0, column=0, padx=(16, 8), pady=(8, 2), sticky="w")

        self.overall_prog_bar = ctk.CTkProgressBar(progress_box, height=10, progress_color=self.ACCENT_SAGE, fg_color=self.PANEL_BG)
        self.overall_prog_bar.grid(row=0, column=1, padx=(8, 16), pady=(8, 2), sticky="ew")
        self.overall_prog_bar.set(0)

        self.active_item_label = ctk.CTkLabel(
            progress_box,
            text="Active: Idle",
            font=ctk.CTkFont(size=11),
            text_color=self.TEXT_CREAM_MUTED,
            width=150,
            anchor="w"
        )
        self.active_item_label.grid(row=1, column=0, padx=(16, 8), pady=(2, 8), sticky="w")

        self.active_prog_bar = ctk.CTkProgressBar(progress_box, height=6, progress_color=self.ACCENT_HOVER, fg_color=self.PANEL_BG)
        self.active_prog_bar.grid(row=1, column=1, padx=(8, 16), pady=(2, 8), sticky="ew")
        self.active_prog_bar.set(0)

    # =========================================================================
    # REAL-TIME URL AUTO-DETECTION (No Icons)
    # =========================================================================

    def _on_url_text_changed(self, *args):
        url = self.url_var.get().strip()
        detection = PlatformDetector.detect(url)

        if detection["is_empty"]:
            self.platform_badge.configure(
                text="Auto-Detect",
                fg_color=self.BTN_SEC_BG
            )
            self.global_status_label.configure(text="Ready. Paste a video or drama link.")
            return

        name = detection["name"]
        hint = detection.get("content_hint", "Video")
        badge_text = f"{name}: {hint}" if hint else name

        self.platform_badge.configure(
            text=badge_text,
            fg_color=self.ACCENT_SAGE
        )
        self.global_status_label.configure(
            text=f"Detected {name} ({hint}). Click Analyze or press Enter."
        )

    def _on_paste_clicked(self):
        try:
            clipboard_text = self.clipboard_get()
            if clipboard_text:
                self.url_var.set(clipboard_text.strip())
        except Exception:
            pass

    def _on_clear_clicked(self):
        self.url_var.set("")
        self.platform_badge.configure(text="Auto-Detect")
        self.global_status_label.configure(text="Ready")
        self.current_metadata = None
        self._switch_mode("empty")
        self.url_entry.focus()

    # =========================================================================
    # LINK EXTRACTION & ADAPTIVE SWITCHING
    # =========================================================================

    def _switch_mode(self, mode: str):
        self.active_mode = mode
        self.empty_frame.grid_remove()
        self.single_frame.grid_remove()
        self.batch_frame.grid_remove()

        if mode == "empty":
            self.empty_frame.grid()
        elif mode == "single":
            self.single_frame.grid(row=0, column=0, sticky="nsew")
        elif mode == "batch":
            self.batch_frame.grid(row=0, column=0, sticky="nsew")

    def _on_fetch_clicked(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Empty URL", "Please enter or paste a valid link first.")
            return

        self.fetch_btn.configure(state="disabled", text="Analyzing...")
        self.global_status_label.configure(text=f"Extracting metadata from {url}...")

        threading.Thread(target=self._run_extract_worker, args=(url,), daemon=True).start()

    def _run_extract_worker(self, url: str):
        result = self.extractor.extract(url)
        self.after(0, self._handle_extract_result, result)

    def _handle_extract_result(self, result: Dict[str, Any]):
        self.fetch_btn.configure(state="normal", text="Analyze")

        if not result.get("success"):
            err = result.get("error", "Unknown error while parsing link.")
            self.global_status_label.configure(text=f"Error: {err}")
            messagebox.showerror("Extraction Failed", f"Could not analyze link:\n\n{err}")
            return

        self.current_metadata = result
        is_batch = result.get("is_drama_series", False) or result.get("is_playlist", False)

        if is_batch:
            self._display_batch_drama(result)
        else:
            self._display_single_video(result)

    # =========================================================================
    # SINGLE VIDEO WORKFLOW
    # =========================================================================

    def _display_single_video(self, meta: Dict[str, Any]):
        self._switch_mode("single")
        detection = meta.get("detection", {})

        title = meta.get("title", "Untitled Video")
        author = meta.get("author", "Creator")
        dur_str = meta.get("duration_str", "")

        self.single_title_lbl.configure(text=title)
        self.single_author_lbl.configure(text=f"By: {author} • Duration: {dur_str}")

        # Update formats dropdown
        formats = meta.get("formats", [])
        if formats:
            display_opts = [f["label"] for f in formats]
            self.format_dropdown.configure(values=display_opts)
            self.format_dropdown.set(display_opts[0])
        else:
            self.format_dropdown.configure(values=["Best Video + Audio", "MP3 Audio (320kbps)"])
            self.format_dropdown.set("Best Video + Audio")

        self.single_progress_label.configure(text="Ready to download.")
        self.single_speed_label.configure(text="")
        self.single_progress_bar.set(0)
        self.single_dl_btn.configure(state="normal")
        self.single_stop_btn.configure(state="disabled")

        self.global_status_label.configure(text=f"Ready: '{title}' ({detection.get('name', 'Video')})")

    def _on_single_download_clicked(self):
        if not self.current_metadata:
            return

        url = self.url_var.get().strip()
        dest_folder = self.single_dest_entry.get().strip()
        if not dest_folder:
            dest_folder = self.base_download_dir

        chosen_label = self.format_dropdown.get()
        formats = self.current_metadata.get("formats", [])
        matched = next((f for f in formats if f["label"] == chosen_label), None)

        format_id = matched["format_id"] if matched else "bestvideo+bestaudio/best"
        target_ext = matched.get("ext", "mp4") if matched else "mp4"

        self.single_dl_btn.configure(state="disabled")
        self.single_stop_btn.configure(state="normal")
        self.single_progress_label.configure(text="Starting download...")

        self.universal_downloader.download(
            url=url,
            dest_folder=dest_folder,
            format_id=format_id,
            target_ext=target_ext,
            progress_callback=self._on_single_download_progress,
            completion_callback=self._on_single_download_complete
        )

    def _on_single_stop_clicked(self):
        self.universal_downloader.stop()
        self.single_stop_btn.configure(state="disabled")
        self.single_progress_label.configure(text="Cancelling download...")

    def _on_single_download_progress(self, percent: float, dl_str: str, speed_str: str, eta_str: str):
        self.after(0, self._update_single_progress_ui, percent, dl_str, speed_str, eta_str)

    def _update_single_progress_ui(self, percent: float, dl_str: str, speed_str: str, eta_str: str):
        self.single_progress_bar.set(percent / 100.0)
        self.single_progress_label.configure(text=f"Downloading: {percent:.1f}% ({dl_str})")
        extra = f"{speed_str}  {eta_str}".strip()
        self.single_speed_label.configure(text=extra)

    def _on_single_download_complete(self, success: bool, message: str, filepath: str):
        self.after(0, self._handle_single_complete_ui, success, message, filepath)

    def _handle_single_complete_ui(self, success: bool, message: str, filepath: str):
        self.single_dl_btn.configure(state="normal")
        self.single_stop_btn.configure(state="disabled")

        if success:
            self.single_progress_bar.set(1.0)
            self.single_progress_label.configure(text="Download Complete")
            self.single_speed_label.configure(text="")
            self.global_status_label.configure(text=f"Saved to: {filepath}")
            messagebox.showinfo("Download Succeeded", f"Video saved successfully:\n{filepath}")
        else:
            self.single_progress_label.configure(text=f"Failed: {message}")
            self.global_status_label.configure(text=f"Download failed: {message}")
            if "cancelled" not in message.lower():
                messagebox.showerror("Download Error", message)

    # =========================================================================
    # BATCH & DRAMA WORKFLOW
    # =========================================================================

    def _display_batch_drama(self, meta: Dict[str, Any]):
        self._switch_mode("batch")

        title = meta.get("title", "Drama Series")
        author = meta.get("author", "Creator")
        total = meta.get("total_episodes", len(meta.get("episodes", [])))

        self.drama_title_label.configure(text=title)
        self.drama_stats_label.configure(text=f"Found {total} Episodes • By: {author} • Ready to download")

        safe_title = UniversalDownloader.sanitize_filename(title)
        drama_dest = os.path.join(self.base_download_dir, safe_title)
        self.current_dest_folder = drama_dest
        self.batch_dest_entry.delete(0, "end")
        self.batch_dest_entry.insert(0, drama_dest)

        for widget in self.episode_scroll.winfo_children():
            widget.destroy()
        self.episode_checkboxes.clear()

        episodes = meta.get("episodes", [])
        for idx, ep in enumerate(episodes):
            ep_num = ep.get("episodeNumber", idx + 1)
            ep_title = ep.get("title") or ep.get("itemTitle") or f"Episode {ep_num}"
            dur = ep.get("duration", 0)
            dur_str = f"{dur // 60}m {dur % 60}s" if dur else ""

            row_frame = ctk.CTkFrame(self.episode_scroll, fg_color="transparent")
            row_frame.pack(fill="x", padx=4, pady=2)
            row_frame.grid_columnconfigure(1, weight=1)

            chk_var = ctk.BooleanVar(value=True)
            chk = ctk.CTkCheckBox(row_frame, text="", variable=chk_var, width=24, fg_color=self.ACCENT_SAGE, hover_color=self.ACCENT_HOVER)
            chk.grid(row=0, column=0, padx=(4, 8), pady=4)

            name_lbl = ctk.CTkLabel(
                row_frame,
                text=f"EP {ep_num:02d}: {ep_title}",
                font=ctk.CTkFont(size=12),
                text_color=self.TEXT_CREAM,
                anchor="w"
            )
            name_lbl.grid(row=0, column=1, sticky="w", pady=4)

            dur_lbl = ctk.CTkLabel(
                row_frame,
                text=dur_str,
                font=ctk.CTkFont(size=11),
                text_color=self.TEXT_CREAM_SUBTLE,
                width=60,
                anchor="e"
            )
            dur_lbl.grid(row=0, column=2, padx=8, pady=4)

            status_lbl = ctk.CTkLabel(
                row_frame,
                text="Ready",
                font=ctk.CTkFont(size=11),
                text_color=self.TEXT_CREAM_MUTED,
                width=110,
                anchor="e"
            )
            status_lbl.grid(row=0, column=3, padx=(4, 8), pady=4)

            self.episode_checkboxes.append({
                "episode": ep,
                "var": chk_var,
                "checkbox": chk,
                "status_lbl": status_lbl,
                "ep_num": ep_num
            })

        self.overall_prog_label.configure(text=f"Overall: 0 / {len(self.episode_checkboxes)} (0%)")
        self.overall_prog_bar.set(0)
        self.active_item_label.configure(text="Active: Idle")
        self.active_prog_bar.set(0)

        self.global_status_label.configure(text=f"Loaded {total} episodes. Choose episodes and click Start Batch.")

    def _select_all_episodes(self):
        for item in self.episode_checkboxes:
            item["var"].set(True)

    def _deselect_all_episodes(self):
        for item in self.episode_checkboxes:
            item["var"].set(False)

    def _apply_range(self):
        val = self.range_entry.get().strip()
        match = re.match(r"^(\d+)\s*-\s*(\d+)$", val)
        if not match:
            messagebox.showinfo("Invalid Range", "Please enter a range like '1-20' or '5-15'")
            return
        start, end = int(match.group(1)), int(match.group(2))
        for item in self.episode_checkboxes:
            num = item["ep_num"]
            item["var"].set(start <= num <= end)

    def _on_retry_failed_clicked(self):
        failed_count = 0
        for item in self.episode_checkboxes:
            current_status = item["status_lbl"].cget("text")
            if "fail" in current_status.lower():
                item["var"].set(True)
                item["status_lbl"].configure(text="Retry Ready", text_color=self.TEXT_CREAM)
                failed_count += 1
            else:
                item["var"].set(False)

        if failed_count > 0:
            self.global_status_label.configure(text=f"Selected {failed_count} failed episode(s) to retry.")
        else:
            messagebox.showinfo("No Failed Episodes", "There are currently no failed episodes to retry.")

    def _on_batch_start_clicked(self):
        selected = [item["episode"] for item in self.episode_checkboxes if item["var"].get()]
        if not selected:
            messagebox.showwarning("No Episodes", "Please select at least one episode to download.")
            return

        dest = self.batch_dest_entry.get().strip() or self.base_download_dir
        self.queue_manager.delay_between_downloads = float(self.delay_slider.get())

        self.batch_start_btn.configure(state="disabled")
        self.batch_pause_btn.configure(state="normal", text="Pause")
        self.batch_stop_btn.configure(state="normal")

        series_title = self.current_metadata.get("title", "TikTok Drama") if self.current_metadata else "TikTok Drama"
        self.queue_manager.start_queue(selected, dest, series_title)

    def _on_batch_pause_clicked(self):
        if self.queue_manager.is_paused:
            self.queue_manager.resume()
            self.batch_pause_btn.configure(text="Pause")
        else:
            self.queue_manager.pause()
            self.batch_pause_btn.configure(text="Resume")

    def _on_batch_stop_clicked(self):
        self.queue_manager.stop()
        self.batch_start_btn.configure(state="normal")
        self.batch_pause_btn.configure(state="disabled", text="Pause")
        self.batch_stop_btn.configure(state="disabled")
        self.active_item_label.configure(text="Stopped.")

    # =========================================================================
    # QUEUE MANAGER CALLBACKS
    # =========================================================================

    def _setup_queue_callbacks(self):
        self.queue_manager.on_log = lambda msg: self.after(0, self._on_log, msg)
        self.queue_manager.on_episode_start = lambda ep, idx, tot: self.after(0, self._on_ep_start, ep, idx, tot)
        self.queue_manager.on_episode_progress = lambda ep, pct, spd: self.after(0, self._on_ep_prog, ep, pct, spd)
        self.queue_manager.on_episode_complete = lambda ep, succ, err: self.after(0, self._on_ep_done, ep, succ, err)
        self.queue_manager.on_overall_progress = lambda comp, tot: self.after(0, self._on_batch_overall, comp, tot)
        self.queue_manager.on_all_finished = lambda succ, fail: self.after(0, self._on_batch_all_finished, succ, fail)

    def _on_log(self, msg: str):
        self.global_status_label.configure(text=msg)

    def _on_ep_start(self, ep: Dict[str, Any], idx: int, tot: int):
        ep_num = ep.get("episodeNumber", idx + 1)
        self.active_item_label.configure(text=f"Downloading EP {ep_num}...")
        self.active_prog_bar.set(0)
        for item in self.episode_checkboxes:
            if item["ep_num"] == ep_num:
                item["status_lbl"].configure(text="Downloading...", text_color=self.ACCENT_SAGE)

    def _on_ep_prog(self, ep: Dict[str, Any], pct: float, spd: str):
        self.active_prog_bar.set(pct / 100.0)
        ep_num = ep.get("episodeNumber", 1)
        self.active_item_label.configure(text=f"EP {ep_num}: {pct:.1f}% ({spd})")

    def _on_ep_done(self, ep: Dict[str, Any], succ: bool, err: str):
        ep_num = ep.get("episodeNumber", 1)
        for item in self.episode_checkboxes:
            if item["ep_num"] == ep_num:
                if succ:
                    item["status_lbl"].configure(text="Completed", text_color=self.ACCENT_SAGE)
                else:
                    item["status_lbl"].configure(text="Failed", text_color="#B95C50")

    def _on_batch_overall(self, completed: int, total: int):
        pct = (completed / total) if total > 0 else 0
        self.overall_prog_bar.set(pct)
        self.overall_prog_label.configure(text=f"Overall: {completed} / {total} ({pct * 100:.0f}%)")

    def _on_batch_all_finished(self, succ_count: int, fail_count: int):
        self.batch_start_btn.configure(state="normal")
        self.batch_pause_btn.configure(state="disabled", text="Pause")
        self.batch_stop_btn.configure(state="disabled")
        self.active_item_label.configure(text="All tasks finished.")

        msg = f"Batch download completed.\n\nSuccessfully downloaded: {succ_count}\nFailed: {fail_count}"
        if fail_count > 0:
            msg += "\n\nTip: Click 'Retry Failed' to retry only the failed episodes."
            messagebox.showwarning("Finished with Warnings", msg)
        else:
            messagebox.showinfo("Completed", msg)

    # =========================================================================
    # FOLDER SELECTORS & UTILITIES
    # =========================================================================

    def _on_browse_dest_single(self):
        path = filedialog.askdirectory(initialdir=self.base_download_dir)
        if path:
            self.single_dest_entry.delete(0, "end")
            self.single_dest_entry.insert(0, path)

    def _on_browse_dest_batch(self):
        path = filedialog.askdirectory(initialdir=self.base_download_dir)
        if path:
            self.batch_dest_entry.delete(0, "end")
            self.batch_dest_entry.insert(0, path)

    def _on_open_dest_folder(self):
        if self.active_mode == "batch":
            folder = self.batch_dest_entry.get().strip() or self.base_download_dir
        else:
            folder = self.single_dest_entry.get().strip() or self.base_download_dir

        os.makedirs(folder, exist_ok=True)
        try:
            subprocess.Popen(f'explorer "{os.path.abspath(folder)}"')
        except Exception as e:
            messagebox.showerror("Error", f"Could not open directory:\n{e}")


# Backwards compatibility alias
DramaDownloaderApp = UniversalDownloaderApp
