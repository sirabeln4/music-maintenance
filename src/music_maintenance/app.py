"""Application entry point for the read-only catalog prototype."""
from __future__ import annotations
import sys
import json
import time
import certifi
import ssl
import shutil
import time as time_module
import re
from datetime import datetime, timezone
from threading import Event
from pathlib import Path
from urllib.request import urlopen
from PySide6.QtCore import QObject, QSettings, QThread, Qt, QUrl, QSize, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QProgressDialog, QSpinBox, QSplitter, QPushButton, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget
from mutagen import File
from mutagen.id3 import ID3, APIC
import acoustid
from .catalog_db import CatalogDatabase
from .musicbrainz import recordings_by_ids, search_recordings
from .coverart import itunes_images, release_images
from .scanner import artwork_bytes, scan_paths
from .converter import convert_wma_to_mp3
from . import __version__

def safe_filename(value: str, fallback: str = "Unknown") -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value or "")).strip().rstrip(".")
    return value or fallback

def organization_destination(path: Path, row, proposal: dict, root: Path) -> Path:
    artist = proposal.get("artist", row["artist"] if row else "") or "Unknown Artist"; album_artist = proposal.get("album_artist", row["album_artist"] if row else "") or artist; album = proposal.get("album", row["album"] if row else "") or "Singles & Rarities"; title = proposal.get("title", row["title"] if row else "") or path.stem; track = str(proposal.get("track", row["track"] if row else "") or ""); parts = re.split(r"[/\\]", track); number = parts[0] if parts else ""; disc = parts[1] if len(parts) > 1 else ""; prefix = f"D{int(disc):02d}-{int(number):02d}" if disc.isdigit() and number.isdigit() else (f"{int(number):02d}" if number.isdigit() else "00"); filename = safe_filename(f"{artist} - {album} - {prefix} - {title}") + path.suffix.lower(); return root / safe_filename(album_artist, "Unknown Artist") / safe_filename(album, "Singles & Rarities") / filename

class ScanWorker(QObject):
    progress = Signal(str, int, int)
    finished = Signal(int, int, bool)
    def __init__(self, paths, recursive, database, cancel):
        super().__init__(); self.paths, self.recursive, self.database, self.cancel = paths, recursive, database, cancel
    def run(self): self.finished.emit(*scan_paths(self.paths, self.recursive, self.database, self.progress.emit, self.cancel))

class LookupWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    def __init__(self, artist, title, album):
        super().__init__(); self.artist, self.title, self.album = artist, title, album
    def run(self):
        try: self.finished.emit(search_recordings(self.artist, self.title, self.album))
        except Exception as exc: self.failed.emit(str(exc))

class BatchLookupWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)
    def __init__(self, paths, database, retries, cancel):
        super().__init__(); self.paths, self.database, self.retries, self.cancel = paths, database, retries, cancel
    def run(self):
        results = {"review": 0, "error": 0, "canceled": False}; last_request = 0.0
        for index, path in enumerate(self.paths, 1):
            if self.cancel.is_set(): results["canceled"] = True; break
            self.database.set_status([path], "MB Lookup"); self.progress.emit(f"Looking up {index}/{len(self.paths)}: {path}")
            success = False; candidates = []
            for attempt in range(max(1, self.retries)):
                if self.cancel.is_set(): results["canceled"] = True; break
                wait = 1.0 - (time.monotonic() - last_request)
                if wait > 0:
                    self.progress.emit(f"Waiting {wait:.1f}s before lookup: {Path(path).name}")
                    if self.cancel.wait(wait): results["canceled"] = True; break
                try:
                    row = self.database.row_for_path(path); candidates = search_recordings(row["artist"], row["title"], row["album"]); last_request = time.monotonic(); success = True; break
                except Exception as exc:
                    last_request = time.monotonic(); self.progress.emit(f"Retry {attempt + 1}/{max(1, self.retries)} for {Path(path).name}: {exc}")
                    if attempt + 1 < max(1, self.retries) and self.cancel.wait(min(8.0, 2.0 ** attempt)): results["canceled"] = True; break
            if results["canceled"]: break
            if success:
                self.database.save_lookup_results(path, candidates, datetime.now(timezone.utc).isoformat()); self.database.set_status([path], "MB review"); results["review"] += 1
            else:
                self.database.set_status([path], "MB error"); results["error"] += 1
        self.finished.emit(results)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(f"Music Maintenance v{__version__} — Catalog"); self.resize(1200, 720)
        self.default_library = Path("G:/My Drive/Music")
        self.settings = QSettings("MusicMaintenance", "MusicMaintenance")
        remembered_value = self.settings.value("selected_folders", [])
        if isinstance(remembered_value, str):
            remembered_value = [remembered_value]
        remembered = [Path(value) for value in remembered_value]
        self.selected_paths = remembered or [self.default_library]
        self.active_plan_id = None
        self.active_plan_name = "No plan selected"
        self.database = CatalogDatabase(Path.home() / ".tempMp3Maint" / "catalog.sqlite3"); self.thread = None; self.cancel_event = None; self.lookup_thread = None; self.lookup_worker = None; self.batch_thread = None; self.batch_worker = None; self.batch_cancel = None; self.scan_history = []; self.audio_output = QAudioOutput(self); self.player = QMediaPlayer(self); self.player.setAudioOutput(self.audio_output)
        self.cleanup_expired_backups()
        root, layout = QWidget(), QVBoxLayout(); root.setLayout(layout)
        plan_row = QHBoxLayout(); self.plan_label = QLabel("Active plan: No plan selected")
        choose = QPushButton("Add folder…"); choose.clicked.connect(self.choose_folder)
        self.recursive = QCheckBox("Scan subfolders recursively"); self.recursive.setChecked(True)
        self.scan_button = QPushButton("Scan"); self.scan_button.clicked.connect(self.start_scan)
        self.cancel_button = QPushButton("Cancel scan"); self.cancel_button.setEnabled(False); self.cancel_button.clicked.connect(self.cancel_scan)
        self.history_button = QPushButton("History"); self.history_button.clicked.connect(self.show_history)
        settings_button = QPushButton("Settings"); settings_button.clicked.connect(self.show_settings)
        plans_button = QPushButton("Select plan"); plans_button.clicked.connect(self.show_saved_plans)
        self.review_plan_button = QPushButton("Review active plan"); self.review_plan_button.setEnabled(False); self.review_plan_button.clicked.connect(self.review_active_plan); add_plan_button = QPushButton("Add plan"); add_plan_button.clicked.connect(self.add_plan)
        plan_row.addWidget(self.plan_label, 1); plan_row.addWidget(plans_button); plan_row.addWidget(add_plan_button); plan_row.addWidget(self.review_plan_button); plan_row.addStretch(); layout.addLayout(plan_row)
        top = QHBoxLayout(); self.status = QLabel(f"● Drive status: {'available' if self.default_library.exists() else 'unavailable'}"); self.path_label = QLabel("Folders selected: 0")
        for item in (self.status, self.path_label): top.addWidget(item, 1 if item is self.path_label else 0)
        top.addWidget(self.recursive); top.addWidget(self.scan_button); top.addWidget(self.cancel_button); top.addWidget(self.history_button); top.addWidget(settings_button); layout.addLayout(top)
        group_row = QHBoxLayout(); group_row.addWidget(QLabel("Select library folders by:")); self.folder_group = QComboBox(); self.folder_group.addItems(["All", "0-9"] + [chr(code) for code in range(ord("A"), ord("Z") + 1)] + ["Symbols / other"]); self.folder_group.currentTextChanged.connect(self.update_remove_enabled); group_row.addWidget(self.folder_group); select_group = QPushButton("Select group"); select_group.clicked.connect(self.select_folder_group); group_row.addWidget(select_group); group_row.addWidget(choose); self.remove_button = QPushButton("Remove selected folders"); self.remove_button.setEnabled(False); self.remove_button.clicked.connect(self.remove_folder); group_row.addWidget(self.remove_button); group_row.addStretch(); layout.addLayout(group_row)
        layout.addWidget(QLabel("Browse folders (select a folder to view its catalog files):")); self.folder_tree = QTreeWidget(); self.folder_tree.setHeaderLabel("Library folders"); self.folder_tree.itemSelectionChanged.connect(self.folder_selection_changed); layout.addWidget(self.folder_tree)
        self.folder_list = QListWidget(); self.folder_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection); self.folder_list.itemSelectionChanged.connect(self.update_remove_enabled); layout.addWidget(self.folder_list)
        self.refresh_folder_list()
        filters = QHBoxLayout(); self.select_all = QCheckBox("Select all visible"); self.select_all.stateChanged.connect(self.toggle_all_visible); self.search_history = QComboBox(); self.search_history.setEditable(True); self.search_history.addItem(""); self.search_history.currentTextChanged.connect(self.search_from_history); self.search = self.search_history.lineEdit(); self.search.setPlaceholderText("Exact search; use * as wildcard"); self.search.textChanged.connect(self.refresh_table); self.search.returnPressed.connect(self.remember_search); self.search_field = QComboBox(); self.search_field.addItems(["All", "Album artist", "Artist", "Album", "Title", "Filename"]); self.search_field.currentTextChanged.connect(self.refresh_table); self.issues = QCheckBox("Issues only"); self.issues.stateChanged.connect(self.refresh_table); clear_search = QPushButton("Clear history"); clear_search.clicked.connect(self.clear_search_history); filters.addWidget(self.select_all); filters.addWidget(self.search_history, 1); filters.addWidget(self.search_field); filters.addWidget(self.issues); filters.addWidget(clear_search); layout.addLayout(filters)
        action_row = QHBoxLayout(); self.action_count = QLabel("Available rows: 0 | Checked rows: 0"); self.review_button = QPushButton("Review selected"); self.review_button.clicked.connect(self.review_selected); self.process_button = QPushButton("Process selected"); self.process_button.clicked.connect(self.process_selected); self.clear_work_button = QPushButton("Clear work"); self.clear_work_button.clicked.connect(self.clear_selected_work); action_row.addWidget(self.action_count, 1); action_row.addWidget(self.review_button); action_row.addWidget(self.process_button); action_row.addWidget(self.clear_work_button); layout.addLayout(action_row); self.progress = QLabel("Ready. No files have been scanned yet."); layout.addWidget(self.progress)
        self.column_names = ["Select", "Status", "Album artist", "Artist", "Album", "Track", "Title", "Format", "Directory", "Directory (relative)", "Filename", "Duration", "Artwork", "Last scan"]; self.table = QTableWidget(0, len(self.column_names)); self.table.setHorizontalHeaderLabels(self.column_names); self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection); self.table.setSortingEnabled(True); self.table.itemSelectionChanged.connect(self.show_details); self.table.itemChanged.connect(lambda item: self.update_action_count()); self.table.setStyleSheet("QTableWidget::item:selected { background-color: #87CEFA; color: #000000; }")
        details = QWidget(); details_layout = QVBoxLayout(details); self.artwork = QLabel("No artwork loaded"); self.artwork.setAlignment(Qt.AlignmentFlag.AlignCenter); self.artwork.setMinimumHeight(180); self.artwork.setStyleSheet("background: #202020; color: #d0d0d0;"); details_layout.addWidget(self.artwork)
        controls = QHBoxLayout(); play = QPushButton("Play"); play.clicked.connect(self.play_selected); pause = QPushButton("Pause"); pause.clicked.connect(self.player.pause); stop = QPushButton("Stop"); stop.clicked.connect(self.player.stop); controls.addWidget(play); controls.addWidget(pause); controls.addWidget(stop); details_layout.addLayout(controls)
        form = QWidget(); form_layout = QFormLayout(form); details_layout.addWidget(form, 1); self.detail_labels = {}
        for name in ("Path", "Album artist", "Artist", "Album", "Title", "Track/disc", "Year", "Genre", "Format", "Duration", "Bitrate", "Sample rate", "Artwork", "Last scan", "Issue"):
            label = QLabel("—"); label.setWordWrap(True); self.detail_labels[name] = label; form_layout.addRow(f"{name}:", label)
        self.lookup_button = QPushButton("MusicBrainz lookup"); self.lookup_button.clicked.connect(self.lookup_selected); self.fingerprint_button = QPushButton("AcoustID fingerprint lookup"); self.fingerprint_button.clicked.connect(self.fingerprint_selected); self.artwork_lookup_button = QPushButton("Artwork lookup"); self.artwork_lookup_button.clicked.connect(self.artwork_selected); self.convert_button = QPushButton("Convert WMA to MP3"); self.convert_button.clicked.connect(self.convert_selected_wma); details_layout.insertWidget(1, self.lookup_button); details_layout.insertWidget(2, self.fingerprint_button); details_layout.insertWidget(3, self.artwork_lookup_button); details_layout.insertWidget(4, self.convert_button)
        splitter = QSplitter(); splitter.addWidget(self.table); splitter.addWidget(details); splitter.setStretchFactor(0, 3); splitter.setStretchFactor(1, 2); layout.addWidget(splitter, 1); self.setCentralWidget(root); self.apply_table_settings(); self.refresh_table()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Add a music folder", str(self.default_library))
        if folder:
            path = Path(folder)
            if path not in self.selected_paths:
                self.selected_paths.append(path)
                self.settings.setValue("selected_folders", [str(item) for item in self.selected_paths])
                self.refresh_folder_list()
            self.status.setText(f"● Drive status: {'available' if path.exists() else 'unavailable'}")

    def remove_folder(self):
        selected = {item.row() for item in self.folder_list.selectedIndexes()}
        self.selected_paths = [path for index, path in enumerate(self.selected_paths) if index not in selected]
        self.settings.setValue("selected_folders", [str(item) for item in self.selected_paths])
        self.refresh_folder_list()

    def update_remove_enabled(self):
        self.remove_button.setEnabled(self.folder_group.currentText() != "All" or len(self.folder_list.selectedItems()) > 1)

    def refresh_folder_list(self):
        self.folder_list.clear()
        self.folder_list.addItems([str(path) for path in self.selected_paths])
        self.path_label.setText(f"Folders selected: {len(self.selected_paths)}")
        self.refresh_folder_tree()

    def refresh_folder_tree(self):
        self.folder_tree.clear()
        for root in self.selected_paths:
            item = QTreeWidgetItem([root.name or str(root)]); item.setData(0, Qt.ItemDataRole.UserRole, str(root)); self.folder_tree.addTopLevelItem(item); self.add_folder_tree_children(item, root, 0)

    def add_folder_tree_children(self, parent_item, path, depth):
        if depth >= 4 or not path.is_dir(): return
        try: children = sorted((child for child in path.iterdir() if child.is_dir() and not child.is_symlink()), key=lambda value: value.name.casefold())
        except OSError: return
        for child in children:
            item = QTreeWidgetItem([child.name]); item.setData(0, Qt.ItemDataRole.UserRole, str(child)); parent_item.addChild(item); self.add_folder_tree_children(item, child, depth + 1)

    def folder_selection_changed(self):
        self.refresh_table()

    def select_folder_group(self):
        root = self.default_library
        if not root.exists():
            QMessageBox.information(self, "Library unavailable", f"The library folder is not currently available:\n{root}")
            return
        choice = self.folder_group.currentText()
        children = [path for path in root.iterdir() if path.is_dir() and not path.is_symlink()]
        if choice == "All":
            selected = children
        elif choice == "0-9":
            selected = [path for path in children if path.name[:1].isdigit()]
        elif choice == "Symbols / other":
            selected = [path for path in children if not path.name[:1].isalnum()]
        else:
            selected = [path for path in children if path.name[:1].upper() == choice]
        self.selected_paths = sorted(selected, key=lambda path: path.name.casefold())
        self.settings.setValue("selected_folders", [str(item) for item in self.selected_paths])
        self.refresh_folder_list()

    def start_scan(self):
        if not self.selected_paths: QMessageBox.information(self, "Select folders", "Select at least one folder before scanning."); return
        self.scan_button.setEnabled(False); self.cancel_button.setEnabled(True); self.progress.setText("Starting scan…"); self.scan_history = []; self.cancel_event = Event(); self.thread = QThread(self); self.worker = ScanWorker(self.selected_paths, self.recursive.isChecked(), self.database, self.cancel_event); self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run); self.worker.progress.connect(self.scan_progress); self.worker.finished.connect(self.scan_finished); self.worker.finished.connect(self.thread.quit); self.thread.finished.connect(self.scan_thread_finished); self.thread.finished.connect(self.thread.deleteLater); self.thread.start()

    def scan_progress(self, path, done, total):
        if path:
            self.scan_history.append(path)
            self.progress.setText(f"{done}/{total}: {path}")

    def show_history(self):
        dialog = QDialog(self); dialog.setWindowTitle("Scan history"); dialog.resize(800, 500)
        layout = QVBoxLayout(dialog); label = QLabel(f"{len(self.scan_history)} files recorded for the current scan"); layout.addWidget(label)
        history = QListWidget(); history.addItems(self.scan_history or ["No scan activity recorded."]); layout.addWidget(history); close = QPushButton("Close"); close.clicked.connect(dialog.accept); layout.addWidget(close); dialog.exec()

    def show_settings(self):
        dialog = QDialog(self); dialog.setWindowTitle("Settings"); dialog.resize(760, 620)
        layout = QVBoxLayout(dialog); form = QFormLayout(); layout.addLayout(form)
        library = QLineEdit(str(self.settings.value("library_root", self.default_library))); database = QLineEdit(str(self.settings.value("database_path", Path.home() / ".tempMp3Maint" / "catalog.sqlite3"))); workspace = QLineEdit(str(self.settings.value("workspace_path", Path.home() / ".tempMp3Maint"))); theme = QComboBox(); theme.addItems(["Follow Windows", "Light", "Dark"]); theme.setCurrentText(str(self.settings.value("theme", "Follow Windows"))); case_sensitive = QCheckBox("Require capitalization in searches"); case_sensitive.setChecked(self.settings.value("case_sensitive_search", False, type=bool)); retries = QSpinBox(); retries.setRange(0, 10); retries.setValue(int(self.settings.value("retry_count", 3))); retention = QSpinBox(); retention.setRange(1, 8760); retention.setValue(int(self.settings.value("backup_retention_hours", 48))); ffmpeg_path = QLineEdit(str(self.settings.value("ffmpeg_path", "ffmpeg")))
        form.addRow("Music library:", library); form.addRow("Catalog database:", database); form.addRow("Temporary workspace:", workspace); form.addRow("Theme:", theme); form.addRow("Search:", case_sensitive); form.addRow("Automatic retries:", retries); form.addRow("Backup retention (hours):", retention); form.addRow("FFmpeg executable:", ffmpeg_path)
        visible_default = self.settings.value("visible_columns", self.column_names); visible_default = [visible_default] if isinstance(visible_default, str) else visible_default; column_checks = {}; columns_widget = QWidget(); columns_layout = QHBoxLayout(columns_widget)
        for name in self.column_names:
            check = QCheckBox(name); check.setChecked(name in visible_default); column_checks[name] = check; columns_layout.addWidget(check)
        order_default = self.settings.value("display_order", self.column_names); order_default = [order_default] if isinstance(order_default, str) else order_default; selected_default = [name for name in order_default if name in self.column_names]; available_default = [name for name in self.column_names if name not in selected_default]; available_list = QListWidget(); available_list.addItems(available_default); selected_list = QListWidget(); selected_list.addItems(selected_default); add_col = QPushButton("→"); remove_col = QPushButton("←"); move_up = QPushButton("↑"); move_down = QPushButton("↓"); arrows = QVBoxLayout(); arrows.addWidget(add_col); arrows.addWidget(remove_col); arrows.addWidget(move_up); arrows.addWidget(move_down); lists = QHBoxLayout(); left = QVBoxLayout(); left.addWidget(QLabel("Available")); left.addWidget(available_list); right = QVBoxLayout(); right.addWidget(QLabel("Selected / screen order")); right.addWidget(selected_list); lists.addLayout(left); lists.addLayout(arrows); lists.addLayout(right); order_widget = QWidget(); order_widget.setLayout(lists); form.addRow("Columns:", order_widget)
        add_col.clicked.connect(lambda: self.transfer_column(available_list, selected_list)); remove_col.clicked.connect(lambda: self.transfer_column(selected_list, available_list)); move_up.clicked.connect(lambda: self.move_column(selected_list, -1)); move_down.clicked.connect(lambda: self.move_column(selected_list, 1))
        sort_levels = QListWidget(); saved_levels = self.settings.value("sort_levels", ["Album artist|Ascending"]); saved_levels = [saved_levels] if isinstance(saved_levels, str) else saved_levels; sort_levels.addItems(saved_levels); sort_available = QComboBox(); sort_available.addItems(self.column_names); add_sort = QPushButton("Add level"); remove_sort = QPushButton("Remove level"); sort_up = QPushButton("↑"); sort_down = QPushButton("↓"); sort_dir = QPushButton("Toggle direction"); sort_controls = QHBoxLayout(); sort_controls.addWidget(sort_available); sort_controls.addWidget(add_sort); sort_controls.addWidget(remove_sort); sort_controls.addWidget(sort_up); sort_controls.addWidget(sort_down); sort_controls.addWidget(sort_dir); sort_widget = QWidget(); sort_layout = QVBoxLayout(sort_widget); sort_layout.addWidget(sort_levels); sort_layout.addLayout(sort_controls); form.addRow("Sort levels (top first):", sort_widget)
        def add_sort_level():
            value = sort_available.currentText() + "|Ascending"; sort_levels.addItem(value)
        def remove_sort_level():
            if sort_levels.currentRow() >= 0: sort_levels.takeItem(sort_levels.currentRow())
        def move_sort(delta):
            row = sort_levels.currentRow(); target = row + delta
            if 0 <= row < sort_levels.count() and 0 <= target < sort_levels.count(): item = sort_levels.takeItem(row); sort_levels.insertItem(target, item); sort_levels.setCurrentRow(target)
        def toggle_sort():
            row = sort_levels.currentRow()
            if row >= 0:
                item = sort_levels.item(row); item.setText(item.text().replace("|Ascending", "|Descending") if "|Ascending" in item.text() else item.text().replace("|Descending", "|Ascending"))
        add_sort.clicked.connect(add_sort_level); remove_sort.clicked.connect(remove_sort_level); sort_up.clicked.connect(lambda: move_sort(-1)); sort_down.clicked.connect(lambda: move_sort(1)); sort_dir.clicked.connect(toggle_sort)
        mb_user = QLineEdit(str(self.settings.value("musicbrainz_user_agent", ""))); mb_user.setPlaceholderText("Application name and contact URL/email"); form.addRow("MusicBrainz User-Agent:", mb_user); acoustid_key = QLineEdit(str(self.settings.value("acoustid_client_key", ""))); acoustid_key.setEchoMode(QLineEdit.EchoMode.Password); fpcalc_path = QLineEdit(str(self.settings.value("fpcalc_path", Path.cwd() / "tools" / "fpcalc.exe"))); form.addRow("AcoustID client key:", acoustid_key); form.addRow("fpcalc.exe path:", fpcalc_path)
        actions = QHBoxLayout(); save = QPushButton("Save"); cancel = QPushButton("Cancel"); actions.addStretch(); actions.addWidget(save); actions.addWidget(cancel); layout.addLayout(actions); cancel.clicked.connect(dialog.reject)
        def save_settings():
            library_path, database_path, workspace_path = Path(library.text()), Path(database.text()), Path(workspace.text())
            if not library_path.is_absolute() or not database_path.is_absolute() or not workspace_path.is_absolute(): QMessageBox.warning(dialog, "Invalid paths", "Library, database, and workspace paths must be absolute."); return
            if database_path.parent.exists() and not database_path.parent.is_dir(): QMessageBox.warning(dialog, "Invalid database path", "The database parent path is not a folder."); return
            visible = [name for name, check in column_checks.items() if check.isChecked()]
            if not visible: QMessageBox.warning(dialog, "Visible columns", "Keep at least one catalog column visible."); return
            display_order = [selected_list.item(i).text() for i in range(selected_list.count())]; levels = [sort_levels.item(i).text() for i in range(sort_levels.count())]; self.settings.setValue("library_root", str(library_path)); self.settings.setValue("database_path", str(database_path)); self.settings.setValue("workspace_path", str(workspace_path)); self.settings.setValue("theme", theme.currentText()); self.settings.setValue("case_sensitive_search", case_sensitive.isChecked()); self.settings.setValue("retry_count", retries.value()); self.settings.setValue("backup_retention_hours", retention.value()); self.settings.setValue("ffmpeg_path", ffmpeg_path.text().strip()); self.settings.setValue("musicbrainz_user_agent", mb_user.text().strip()); self.settings.setValue("acoustid_client_key", acoustid_key.text().strip()); self.settings.setValue("fpcalc_path", fpcalc_path.text().strip()); self.settings.setValue("visible_columns", display_order); self.settings.setValue("display_order", display_order); self.settings.setValue("sort_levels", levels); self.default_library = library_path; self.apply_table_settings(); self.refresh_folder_list(); self.cleanup_expired_backups(); dialog.accept()
        save.clicked.connect(save_settings); dialog.exec()

    def apply_table_settings(self):
        visible = self.settings.value("visible_columns", self.column_names); visible = [visible] if isinstance(visible, str) else visible
        visible = list(dict.fromkeys(["Select", "Status"] + [name for name in visible if name in self.column_names]))
        self.settings.setValue("visible_columns", visible)
        for index, name in enumerate(self.column_names): self.table.setColumnHidden(index, name not in visible)
        order = self.settings.value("display_order", self.column_names); order = [order] if isinstance(order, str) else order; order = list(dict.fromkeys(["Select", "Status"] + [name for name in order if name in self.column_names]))
        for target, name in enumerate(order):
            if name in self.column_names:
                current = self.table.horizontalHeader().visualIndex(self.column_names.index(name)); self.table.horizontalHeader().moveSection(current, target)
        levels = self.settings.value("sort_levels", ["Album artist|Ascending"]); levels = [levels] if isinstance(levels, str) else levels; first = levels[0].split("|", 1) if levels else ["Album artist", "Ascending"]; sort_index = self.column_names.index(first[0]) if first[0] in self.column_names else 0; order = Qt.SortOrder.DescendingOrder if len(first) > 1 and first[1] == "Descending" else Qt.SortOrder.AscendingOrder; self.table.sortItems(sort_index, order)

    def process_selected(self):
        selected = [self.table.item(row, 2).data(32) for row in range(self.table.rowCount()) if self.table.item(row, 0) and self.table.item(row, 0).checkState() == Qt.CheckState.Checked]
        if not selected:
            QMessageBox.information(self, "Select files", "Check one or more rows before processing."); return
        counts = {}
        for path in selected:
            row = self.database.row_for_path(path); status = row["status"] if row and row["status"] else "DB"; counts[status] = counts.get(status, 0) + 1
        summary = "\n".join(f"{status}: {count}" for status, count in sorted(counts.items())); file_paths = [path for path in selected if (self.database.row_for_path(path)["status"] if self.database.row_for_path(path) else "DB") in {"DB", "File", "MB error"}]
        if file_paths:
            self.process_summary = summary; self.process_selected_paths = selected; self.batch_cancel = Event(); self.batch_thread = QThread(self); self.batch_worker = BatchLookupWorker(file_paths, self.database, int(self.settings.value("retry_count", 3)), self.batch_cancel); self.batch_worker.moveToThread(self.batch_thread); self.batch_thread.started.connect(self.batch_worker.run); self.batch_worker.progress.connect(self.batch_progress); self.batch_worker.finished.connect(self.batch_finished); self.batch_worker.finished.connect(self.batch_thread.quit); self.batch_thread.finished.connect(self.batch_done); self.batch_thread.finished.connect(self.batch_thread.deleteLater); self.process_button.setEnabled(False); self.clear_work_button.setEnabled(False); self.batch_progress_dialog = QProgressDialog("Starting MusicBrainz processing…", "Cancel", 0, 0, self); self.batch_progress_dialog.setWindowTitle("MusicBrainz processing"); self.batch_progress_dialog.setAutoClose(False); self.batch_progress_dialog.setMinimumDuration(0); self.batch_progress_dialog.canceled.connect(self.cancel_batch); self.batch_progress_dialog.show(); self.batch_thread.start(); return
        self.finish_selected_processing(selected, 0, 0, summary, False)

    def batch_progress(self, message):
        self.progress.setText(message)
        if getattr(self, "batch_progress_dialog", None): self.batch_progress_dialog.setLabelText(message); QApplication.processEvents()

    def cancel_batch(self):
        if self.batch_cancel: self.batch_cancel.set(); self.batch_progress("Canceling after the current request…")

    def batch_finished(self, results):
        self.finish_selected_processing(self.process_selected_paths, results["review"], results["error"], self.process_summary, results["canceled"])

    def batch_done(self):
        self.batch_thread = None; self.batch_worker = None; self.batch_cancel = None

    def finish_selected_processing(self, selected, mb_review, mb_error, summary, canceled):
        if getattr(self, "batch_progress_dialog", None): self.batch_progress_dialog.close(); self.batch_progress_dialog = None
        self.review_canceled = False
        review_paths = [] if canceled else [path for path in selected if (self.database.row_for_path(path)["status"] if self.database.row_for_path(path) else "") == "MB review"]
        review_missing = []
        for path in review_paths:
            if self.review_canceled: break
            candidates = self.database.lookup_candidates(path)
            if candidates:
                self.lookup_path = path; self.lookup_finished(candidates)
                if self.review_canceled: break
                if self.active_plan_id and any(item["file_path"] == path for item in self.database.plan_items(self.active_plan_id)): self.database.set_status([path], "Plan - Pending"); self.database.set_plan_item_status(self.active_plan_id, path, "Plan - Pending")
            else:
                self.database.set_status([path], "DB")
                review_missing.append(path)
        self.refresh_table(); self.process_button.setEnabled(True); self.clear_work_button.setEnabled(True); message = f"Processed selected rows.\n\nAction groups before processing:\n{summary}\n\nMusicBrainz review candidates opened: {mb_review}\nMusicBrainz errors: {mb_error}"
        if canceled: message = "Processing canceled. Completed results were saved.\n\n" + message
        if review_missing:
            message += f"\n\n{len(review_missing)} MB review row(s) had no saved candidates and were reset to DB."
        QMessageBox.information(self, "Process selected", message)

    def clear_selected_work(self):
        paths = [self.table.item(row, 2).data(32) for row in range(self.table.rowCount()) if self.table.item(row, 0) and self.table.item(row, 0).checkState() == Qt.CheckState.Checked]
        if not paths:
            QMessageBox.information(self, "Select files", "Check one or more rows before clearing work."); return
        answer = QMessageBox.question(self, "Clear lookup work", f"Clear saved lookup candidates, remove {len(paths)} selected row(s) from saved plans, and reset them to DB status?\n\nThis does not delete music files or delete the plans themselves.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes: return
        self.database.clear_lookup_work(paths); self.refresh_table(); QMessageBox.information(self, "Work cleared", f"Cleared lookup work for {len(paths)} row(s). They are now DB status.")

    def cleanup_expired_backups(self):
        root = Path.home() / ".tempMp3Maint" / "backups"; hours = int(self.settings.value("backup_retention_hours", 48))
        if not root.is_dir(): return
        cutoff = time_module.time() - hours * 3600
        for folder in root.iterdir():
            if folder.is_dir() and folder.stat().st_mtime < cutoff:
                try: shutil.rmtree(folder)
                except OSError as exc: print(f"[Backup cleanup] {folder}: {exc}", flush=True)

    def cancel_scan(self):
        if self.cancel_event:
            self.cancel_event.set(); self.cancel_button.setEnabled(False); self.progress.setText("Canceling after the current file…")

    def scan_finished(self, scanned, failed, canceled):
        self.scan_button.setEnabled(True); self.cancel_button.setEnabled(False); state = "canceled" if canceled else "complete"; self.progress.setText(f"Scan {state}: {scanned} MP3/WMA files, {failed} read failures."); self.refresh_table(); QMessageBox.information(self, "Scan summary", f"Scan {state}.\n\nMP3/WMA files processed: {scanned}\nRead failures: {failed}\nHistory entries: {len(self.scan_history)}")

    def scan_thread_finished(self):
        self.thread = None
        self.worker = None

    def refresh_table(self):
        rows = self.database.rows(self.issues.isChecked(), self.search.text().strip(), self.search_field.currentText(), self.settings.value("case_sensitive_search", False, type=bool)); selected_folders = [Path(item.data(0, Qt.ItemDataRole.UserRole)) for item in self.folder_tree.selectedItems() if item.data(0, Qt.ItemDataRole.UserRole)]
        if selected_folders:
            rows = [row for row in rows if any(Path(row["path"]) == folder or folder in Path(row["path"]).parents for folder in selected_folders)]
        self.table.setSortingEnabled(False); self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            try: relative_directory = str(Path(row["path"]).parent.relative_to(self.default_library))
            except ValueError: relative_directory = str(Path(row["path"]).parent)
            for j, value in enumerate([None, row["status"], row["album_artist"], row["artist"], row["album"], row["track"], row["title"], row["extension"], str(Path(row["path"]).parent), relative_directory, row["filename"], row["duration"], row["artwork_state"], row["scan_time"]]):
                item = QTableWidgetItem("" if value is None else str(value))
                if j == 0:
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable); item.setCheckState(Qt.CheckState.Unchecked); item.setData(32, row["path"])
                elif j == 2: item.setData(32, row["path"])
                self.table.setItem(i, j, item)
        self.table.setSortingEnabled(True); self.update_action_count()

    def update_action_count(self):
        available = self.table.rowCount(); checked = sum(1 for row in range(available) if self.table.item(row, 0) and self.table.item(row, 0).checkState() == Qt.CheckState.Checked); self.action_count.setText(f"Available rows: {available} | Checked rows: {checked}")

    def toggle_all_visible(self, state):
        checked = Qt.CheckState.Checked if state == Qt.CheckState.Checked.value else Qt.CheckState.Unchecked
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0): self.table.item(row, 0).setCheckState(checked)
        self.table.blockSignals(False); self.update_action_count()

    def transfer_column(self, source, target):
        for item in source.selectedItems():
            target.addItem(source.takeItem(source.row(item)))

    def move_column(self, widget, delta):
        row = widget.currentRow(); target = row + delta
        if 0 <= row < widget.count() and 0 <= target < widget.count():
            item = widget.takeItem(row); widget.insertItem(target, item); widget.setCurrentRow(target)

    def search_from_history(self, value):
        if value != self.search.text():
            self.search.setText(value)

    def remember_search(self):
        value = self.search.text().strip()
        if not value:
            return
        values = [self.search_history.itemText(i) for i in range(self.search_history.count()) if self.search_history.itemText(i)]
        values = [value] + [item for item in values if item != value]
        self.search_history.blockSignals(True); self.search_history.clear(); self.search_history.addItem(""); self.search_history.addItems(values[:10]); self.search_history.setCurrentText(value); self.search_history.blockSignals(False)

    def clear_search_history(self):
        self.search_history.blockSignals(True); self.search_history.clear(); self.search_history.addItem(""); self.search_history.setCurrentIndex(0); self.search_history.blockSignals(False)

    def show_details(self):
        selected = self.table.currentRow()
        if selected < 0:
            self.artwork.setText("Select one row to view details."); self.artwork.setPixmap(QPixmap()); return
        if selected < 0:
            return
        path_item = self.table.item(selected, 2)
        path = path_item.data(32) if path_item else None
        row = self.database.row_for_path(path) if path else None
        if row is None:
            return
        values = {"Path": row["path"], "Album artist": row["album_artist"], "Artist": row["artist"], "Album": row["album"], "Title": row["title"], "Track/disc": row["track"], "Year": row["year"], "Genre": row["genre"], "Format": row["extension"], "Duration": row["duration"], "Bitrate": row["bitrate"], "Sample rate": row["sample_rate"], "Artwork": row["artwork_state"], "Last scan": row["scan_time"], "Issue": row["issue"]}
        for name, value in values.items():
            self.detail_labels[name].setText("—" if value is None or value == "" else str(value))
        image_data = artwork_bytes(Path(row["path"]))
        if image_data:
            pixmap = QPixmap(); pixmap.loadFromData(image_data); self.artwork.setPixmap(pixmap.scaled(220, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.artwork.setPixmap(QPixmap()); self.artwork.setText("No embedded artwork")
        self.current_media_path = row["path"]

    def review_selected(self):
        paths = [self.table.item(row, 2).data(32) for row in range(self.table.rowCount()) if self.table.item(row, 0) and self.table.item(row, 0).checkState() == Qt.CheckState.Checked]
        if not paths:
            QMessageBox.information(self, "Select files", "Select one or more catalog rows before opening batch review."); return
        dialog = QDialog(self); dialog.setWindowTitle("Batch review — no file changes"); dialog.resize(820, 520); layout = QVBoxLayout(dialog); layout.addWidget(QLabel("Check the files to include in this pending review plan. Applying changes will be added in a later step.")); items = QListWidget(); items.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        for path in paths:
            row = self.database.row_for_path(path); label = f"{row['album_artist'] or 'Unknown artist'} — {row['album'] or 'Unknown album'} — {row['title'] or Path(path).stem} [{path}]"; item = QListWidgetItem(label); item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable); item.setCheckState(Qt.CheckState.Checked); items.addItem(item)
        layout.addWidget(items); actions = QHBoxLayout(); save = QPushButton("Save pending plan"); close = QPushButton("Close"); actions.addWidget(save); actions.addWidget(close); layout.addLayout(actions); close.clicked.connect(dialog.reject)
        def save_plan():
            checked = [paths[i] for i in range(items.count()) if items.item(i).checkState() == Qt.CheckState.Checked]
            if not checked:
                QMessageBox.information(dialog, "No files selected", "Check at least one file before saving a plan."); return
            name, accepted = QInputDialog.getText(dialog, "Name review plan", "Plan name:", text=f"Review {datetime.now().strftime('%Y-%m-%d %H%M')}")
            if accepted and name.strip():
                proposals = {}
                for path in checked:
                    row = self.database.row_for_path(path)
                    proposals[path] = {"artist": row["artist"], "album_artist": row["album_artist"], "album": row["album"], "title": row["title"], "track": row["track"], "year": row["year"], "genre": row["genre"]} if row else {}
                plan_id = self.database.create_plan(name.strip(), checked, datetime.now(timezone.utc).isoformat(), proposals)
                QMessageBox.information(dialog, "Plan saved", f"Saved review plan #{plan_id} for {len(checked)} file(s). No files were changed.")
        save.clicked.connect(save_plan); dialog.exec()

    def show_saved_plans(self):
        dialog = QDialog(self); dialog.setWindowTitle("Saved review plans"); dialog.resize(760, 420); layout = QVBoxLayout(dialog); show_archived = QCheckBox("Show archived plans"); layout.addWidget(show_archived); plans = QListWidget(); all_records = self.database.list_plans(); records = []
        def refresh_plans():
            nonlocal records
            records = all_records if show_archived.isChecked() else [row for row in all_records if row["status"] != "Archived"]; plans.clear(); plans.addItems([f"#{row['id']} — {row['name']} — {row['item_count']} file(s) — {row['status']} — {row['created_at']}" for row in records] or ["No saved plans."])
        refresh_plans(); show_archived.stateChanged.connect(refresh_plans); layout.addWidget(plans)
        inspect = QPushButton("Inspect selected plan"); activate = QPushButton("Use selected plan"); archive = QPushButton("Archive / restore plan"); remove = QPushButton("Delete selected plan"); close = QPushButton("Close"); actions = QHBoxLayout(); actions.addWidget(inspect); actions.addWidget(activate); actions.addWidget(archive); actions.addWidget(remove); actions.addWidget(close); layout.addLayout(actions); close.clicked.connect(dialog.accept)
        def activate_plan():
            index = plans.currentRow()
            if 0 <= index < len(records):
                self.active_plan_id = records[index]["id"]; self.active_plan_name = records[index]["name"]; self.plan_label.setText(f"Active plan: {self.active_plan_name} (#{self.active_plan_id})"); self.review_plan_button.setEnabled(True); dialog.accept()
        activate.clicked.connect(activate_plan)
        def archive_plan():
            index = plans.currentRow()
            if index < 0 or index >= len(records): return
            row = records[index]; target = "Pending" if row["status"] == "Archived" else "Archived"
            if target == "Archived" and row["status"] == "Pending": QMessageBox.information(dialog, "Plan still pending", "Apply or finish the plan before archiving it."); return
            if QMessageBox.question(dialog, f"{target} plan", f"Set plan '{row['name']}' to {target}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes: return
            self.database.set_plan_status(row["id"], target); all_records[:] = self.database.list_plans(); refresh_plans()
        archive.clicked.connect(archive_plan)
        def inspect_plan():
            index = plans.currentRow()
            if index < 0 or index >= len(records): return
            record = records[index]; detail = QDialog(dialog); detail.setWindowTitle(f"Plan #{record['id']} — {record['name']}"); detail.resize(900, 450); detail_layout = QVBoxLayout(detail); items = QListWidget(); plan_items = self.database.plan_items(record["id"])
            for item in plan_items:
                path = Path(item["file_path"]); state = "Missing" if not path.exists() else "Available"
                if path.exists() and item["planned_size"] is not None:
                    stat = path.stat()
                    if stat.st_size != item["planned_size"] or stat.st_mtime_ns != item["planned_modified_ns"]: state = "Changed — revalidation required"
                items.addItem(f"{state} — {item['file_path']}")
            detail_layout.addWidget(QLabel("Plans must be revalidated before any future apply operation.")); detail_layout.addWidget(items); edit = QPushButton("Edit selected proposal"); done = QPushButton("Close"); actions2 = QHBoxLayout(); actions2.addWidget(edit); actions2.addWidget(done); detail_layout.addLayout(actions2); done.clicked.connect(detail.accept)
            def edit_proposal():
                if self.active_plan_id is None:
                    if not self.ensure_active_plan(item["file_path"]): return
                row_index = items.currentRow()
                if row_index < 0 or row_index >= len(plan_items): return
                item = plan_items[row_index]; current = self.database.row_for_path(item["file_path"]); proposal = json.loads(item["proposal_json"] or "{}")
                editor = QDialog(detail); editor.setWindowTitle("Edit proposal"); editor.resize(760, 420); form = QFormLayout(editor); fields = ["artist", "album_artist", "album", "title", "track", "year", "genre"]; edits = {}
                for field in fields:
                    edit_field = QLineEdit(str(proposal.get(field, current[field] if current else "") or "")); edits[field] = edit_field; form.addRow(field.replace("_", " ").title() + ":", edit_field)
                save_edit = QPushButton("Save proposal"); form.addRow(save_edit)
                def save_proposal():
                    self.database.update_plan_proposal(record["id"], item["file_path"], {field: edits[field].text() for field in fields}); editor.accept(); QMessageBox.information(detail, "Proposal saved", "The proposal was updated in the saved plan.")
                save_edit.clicked.connect(save_proposal); editor.exec()
            edit.clicked.connect(edit_proposal); detail.exec()
        inspect.clicked.connect(inspect_plan)
        def delete_selected():
            index = plans.currentRow()
            if index < 0 or index >= len(records): return
            row = records[index]
            if QMessageBox.question(dialog, "Delete plan", f"Delete plan '{row['name']}'?") == QMessageBox.StandardButton.Yes:
                self.database.delete_plan(row["id"]); plans.takeItem(index); records.pop(index)
                if self.active_plan_id == row["id"]:
                    self.active_plan_id = None; self.active_plan_name = "No plan selected"; self.plan_label.setText("Active plan: No plan selected"); self.review_plan_button.setEnabled(False)
        remove.clicked.connect(delete_selected); dialog.exec()

    def add_plan(self):
        name, accepted = QInputDialog.getText(self, "Add plan", "Plan name:")
        if not accepted or not name.strip(): return
        plan_id = self.database.create_plan(name.strip(), [], datetime.now(timezone.utc).isoformat())
        self.active_plan_id, self.active_plan_name = plan_id, name.strip(); self.plan_label.setText(f"Active plan: {self.active_plan_name} (#{plan_id})"); self.review_plan_button.setEnabled(True)

    def review_active_plan(self):
        if self.active_plan_id is None:
            QMessageBox.information(self, "No active plan", "Select or create a plan before reviewing it."); return
        records = self.database.plan_items(self.active_plan_id)
        dialog = QDialog(self); dialog.setWindowTitle(f"Review active plan — {self.active_plan_name}"); dialog.resize(1400, 520); layout = QVBoxLayout(dialog); layout.addWidget(QLabel("Approve or reject individual items. Applying changes will be added after review is complete.")); table = QTableWidget(len(records), 6); table.setHorizontalHeaderLabels(["Approve", "Status", "File", "Current", "Proposed", "Proposed path"]); table.setWordWrap(False); table.setColumnWidth(2, 480); table.setColumnWidth(5, 560); layout.addWidget(table)
        for i, item in enumerate(records):
            path = Path(item["file_path"]); status = "Missing" if not path.exists() else "Available"; current = self.database.row_for_path(item["file_path"]); proposal = json.loads(item["proposal_json"] or "{}")
            reason = ""
            if not path.exists():
                status = "Missing"; reason = "file is unavailable"
            elif item["planned_size"] is not None:
                stat = path.stat()
                size_changed = stat.st_size != item["planned_size"]; time_changed = stat.st_mtime_ns != item["planned_modified_ns"]
                if size_changed or time_changed:
                    status = "Changed — revalidate"; reason = ", ".join(filter(None, ["size changed" if size_changed else "", "modified time changed" if time_changed else ""]))
            check = QTableWidgetItem(); check.setFlags(check.flags() | Qt.ItemFlag.ItemIsUserCheckable); check.setCheckState(Qt.CheckState.Checked); file_item = QTableWidgetItem(item["file_path"]); file_item.setToolTip(item["file_path"]); proposed_path = organization_destination(path, current, proposal, Path(str(self.settings.value("library_root", self.default_library)))); path_item = QTableWidgetItem(str(proposed_path)); path_item.setToolTip(str(proposed_path)); status_item = QTableWidgetItem(status + (f" ({reason})" if reason else "")); table.setItem(i, 0, check); table.setItem(i, 1, status_item); table.setItem(i, 2, file_item); table.setItem(i, 3, QTableWidgetItem(f"{current['artist'] if current else ''} — {current['title'] if current else ''}")); table.setItem(i, 4, QTableWidgetItem(f"{proposal.get('artist', '')} — {proposal.get('title', '')}")); table.setItem(i, 5, path_item)
        edit = QPushButton("Edit selected proposal"); apply = QPushButton("Apply approved changes"); undo = QPushButton("Undo last apply"); close = QPushButton("Close"); actions = QHBoxLayout(); actions.addWidget(edit); actions.addWidget(apply); actions.addWidget(undo); actions.addWidget(close); layout.addLayout(actions); close.clicked.connect(dialog.accept)
        def edit_selected():
            index = table.currentRow()
            if index < 0 or index >= len(records): return
            item = records[index]; current = self.database.row_for_path(item["file_path"]); proposal = json.loads(item["proposal_json"] or "{}"); editor = QDialog(dialog); editor.setWindowTitle("Edit plan proposal"); editor.resize(760, 420); form = QFormLayout(editor); fields = ["artist", "album_artist", "album", "title", "track", "year", "genre"]; edits = {}
            for field in fields:
                current_value = str(current[field] if current else ""); edit_field = QLineEdit(str(proposal.get(field, current_value) or "")); edits[field] = edit_field; copy_current = QPushButton("Use current"); copy_current.clicked.connect(lambda checked=False, target=edit_field, source=current_value: target.setText(source)); row = QHBoxLayout(); row.addWidget(edit_field, 1); row.addWidget(copy_current); container = QWidget(); container.setLayout(row); form.addRow(field.replace("_", " ").title() + ":", container)
            save = QPushButton("Save proposal"); form.addRow(save)
            def save_edit():
                updated = {field: edits[field].text() for field in fields}; self.database.update_plan_proposal(self.active_plan_id, item["file_path"], updated); table.setItem(index, 4, QTableWidgetItem(f"{updated.get('artist', '')} — {updated.get('title', '')}")); new_path = organization_destination(Path(item["file_path"]), current, updated, Path(str(self.settings.value("library_root", self.default_library)))); table.setItem(index, 5, QTableWidgetItem(str(new_path))); editor.accept(); QMessageBox.information(dialog, "Proposal saved", "The active plan was updated.")
            save.clicked.connect(save_edit); editor.exec()
        def apply_approved():
            approved = [records[i] for i in range(table.rowCount()) if table.item(i, 0) and table.item(i, 0).checkState() == Qt.CheckState.Checked]
            if not approved:
                QMessageBox.information(dialog, "No approved files", "Check at least one row in the Approve column before applying."); return
            if QMessageBox.question(dialog, "Apply approved changes", f"Apply reviewed text tags to {len(approved)} file(s)? A backup will be created before each write.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes: return
            backup_root = Path.home() / ".tempMp3Maint" / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S"); backup_map = {}; failure_details = []; skip_details = []; changed = skipped = failed = 0
            artwork_failed = []
            for item in approved:
                path = Path(item["file_path"]); current = self.database.row_for_path(str(path));
                if not path.exists() or not current or (item["planned_size"] is not None and (path.stat().st_size != item["planned_size"] or path.stat().st_mtime_ns != item["planned_modified_ns"])):
                    skipped += 1; self.database.set_status([str(path)], "Plan - Skipped"); self.database.set_plan_item_status(self.active_plan_id, str(path), "Plan - Skipped")
                    if not path.exists(): skip_details.append(f"{path.name}: file is not available")
                    elif not current: skip_details.append(f"{path.name}: no catalog row")
                    else: skip_details.append(f"{path.name}: file changed (planned {item['planned_size']} bytes/{item['planned_modified_ns']}, current {path.stat().st_size} bytes/{path.stat().st_mtime_ns})")
                    continue
                try:
                    backup_root.mkdir(parents=True, exist_ok=True); backup_file = backup_root / f"{len(backup_map):05d}_{path.name}"; shutil.copy2(path, backup_file); backup_map[str(backup_file)] = str(path); proposal = json.loads(item["proposal_json"] or "{}"); audio = File(path, easy=True)
                    if audio is None: raise ValueError("Unsupported audio format")
                    for field in ("artist", "albumartist", "album", "title", "tracknumber", "date", "genre"):
                        source = "album_artist" if field == "albumartist" else ("track" if field == "tracknumber" else ("year" if field == "date" else field)); value = proposal.get(source)
                        if value is not None: audio[field] = [str(value)]
                    audio.save()
                    artwork = proposal.get("artwork")
                    if artwork and artwork.get("source") not in {"embedded", "placeholder"}:
                        try:
                            if artwork.get("source") == "local":
                                image_data = Path(artwork["path"]).read_bytes()
                            else:
                                context = ssl.create_default_context(cafile=certifi.where())
                                with urlopen(artwork.get("url", ""), timeout=20, context=context) as response: image_data = response.read()
                            if path.suffix.lower() != ".mp3": raise ValueError("Artwork embedding currently supports MP3 files only")
                            tags = ID3(path); tags.delall("APIC"); mime = "image/png" if image_data.startswith(b"\x89PNG") else "image/jpeg"; tags.add(APIC(encoding=3, mime=mime, type=3, desc="", data=image_data)); tags.save(path)
                        except Exception as exc:
                            artwork_failed.append(f"{path.name}: {exc}"); print(f"[Artwork apply] {path}: {exc}", flush=True)
                    check_audio = File(path, easy=True); mismatches = []
                    for field in ("artist", "albumartist", "album", "title", "tracknumber", "date", "genre"):
                        source = "album_artist" if field == "albumartist" else ("track" if field == "tracknumber" else ("year" if field == "date" else field)); expected = str(proposal.get(source) or ""); actual = str((check_audio.get(field) or [""])[0]) if check_audio else ""
                        if source not in proposal: continue
                        if expected != actual: mismatches.append(field)
                    if mismatches: raise ValueError("Verification mismatch: " + ", ".join(mismatches))
                    destination = organization_destination(path, current, proposal, Path(str(self.settings.value("library_root", self.default_library))))
                    if destination != path:
                        destination.parent.mkdir(parents=True, exist_ok=True); candidate_path = destination; suffix = 1
                        while candidate_path.exists(): candidate_path = destination.with_name(f"{destination.stem} ({suffix}){destination.suffix}"); suffix += 1
                        shutil.move(str(path), str(candidate_path)); self.database.move_file_path(str(path), str(candidate_path)); path = candidate_path
                    result_status = "Plan - Partial" if any(detail.startswith(path.name + ":") for detail in artwork_failed) else "Plan - Complete"; self.database.set_status([str(path)], result_status); self.database.set_plan_item_status(self.active_plan_id, str(item["file_path"]), result_status); changed += 1
                except Exception as exc:
                    failed += 1; self.database.set_status([str(path)], "Plan - Error"); self.database.set_plan_item_status(self.active_plan_id, str(path), "Plan - Error"); failure_details.append(f"{path.name}: {exc}"); print(f"[Apply] {path}: {exc}", flush=True)
            if changed:
                (backup_root / "manifest.json").write_text(json.dumps(backup_map, indent=2), encoding="utf-8"); self.settings.setValue("last_apply_backup", str(backup_root))
            overall = "Complete" if changed and not skipped and not failed else ("Partial" if changed else ("Skipped" if skipped and not failed else "Error")); self.database.set_plan_status(self.active_plan_id, overall)
            detail = (("\n\nSkipped details:\n" + "\n".join(skip_details)) if skip_details else "") + (("\n\nFailure details:\n" + "\n".join(failure_details)) if failure_details else "") + (("\n\nArtwork failures:\n" + "\n".join(artwork_failed)) if artwork_failed else ""); QMessageBox.information(dialog, "Apply complete", f"Verified: {changed}\nSkipped: {skipped}\nFailed or mismatched: {failed}\nArtwork failures: {len(artwork_failed)}\n\nBackups: {backup_root if changed else 'None'}{detail}"); self.refresh_table()
        def undo_last_apply():
            backup = Path(str(self.settings.value("last_apply_backup", "")))
            if not backup.is_dir(): QMessageBox.information(dialog, "Nothing to undo", "No retained apply backup was found."); return
            if QMessageBox.question(dialog, "Undo last apply", f"Restore files from this backup?\n{backup}", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes: return
            restored = failed = 0
            try: backup_map = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
            except Exception: backup_map = {}
            for source_name, target_name in backup_map.items():
                source, target = Path(source_name), Path(target_name)
                if target and target.exists():
                    try: shutil.copy2(source, target); restored += 1
                    except Exception as exc: failed += 1; print(f"[Undo] {target}: {exc}", flush=True)
            QMessageBox.information(dialog, "Undo complete", f"Restored: {restored}\nFailed: {failed}"); self.refresh_table()
        edit.clicked.connect(edit_selected); apply.clicked.connect(apply_approved); undo.clicked.connect(undo_last_apply); dialog.exec()

    def play_selected(self):
        if self.current_media_path:
            self.player.setSource(QUrl.fromLocalFile(self.current_media_path)); self.player.play()

    def lookup_selected(self):
        row_index = self.table.currentRow()
        if row_index < 0:
            QMessageBox.information(self, "Select a file", "Select a catalog row before starting a lookup."); return
        item = self.table.item(row_index, 2); path = item.data(32) if item else None; row = self.database.row_for_path(path) if path else None
        if row is None: return
        self.lookup_path = path; self.lookup_button.setEnabled(False); self.progress.setText("MusicBrainz lookup in progress…"); self.lookup_thread = QThread(self); self.lookup_worker = LookupWorker(row["artist"], row["title"], row["album"]); self.lookup_worker.moveToThread(self.lookup_thread); self.lookup_thread.started.connect(self.lookup_worker.run); self.lookup_worker.finished.connect(self.lookup_finished); self.lookup_worker.failed.connect(self.lookup_failed); self.lookup_worker.finished.connect(self.lookup_thread.quit); self.lookup_worker.failed.connect(self.lookup_thread.quit); self.lookup_thread.finished.connect(self.lookup_thread.deleteLater); self.lookup_thread.finished.connect(self.lookup_done); self.lookup_thread.start()

    def lookup_done(self):
        self.lookup_thread = None; self.lookup_worker = None; self.lookup_button.setEnabled(True)

    def lookup_failed(self, message):
        self.progress.setText("MusicBrainz lookup failed."); QMessageBox.warning(self, "MusicBrainz lookup failed", message)

    def fingerprint_selected(self):
        path = getattr(self, "current_media_path", None); key = str(self.settings.value("acoustid_client_key", "")); fpcalc = Path(str(self.settings.value("fpcalc_path", Path.cwd() / "tools" / "fpcalc.exe")))
        if not path: QMessageBox.information(self, "Select a file", "Select a catalog row before fingerprinting."); return
        if not key: QMessageBox.information(self, "AcoustID key required", "Enter the AcoustID client key in Settings first."); return
        if not fpcalc.exists(): QMessageBox.warning(self, "fpcalc not found", f"The configured fpcalc.exe was not found:\n{fpcalc}"); return
        progress = QProgressDialog("Generating audio fingerprint…", None, 0, 0, self); progress.setWindowTitle("AcoustID lookup"); progress.setMinimumDuration(0); progress.setModal(True); progress.show(); QApplication.processEvents()
        try:
            acoustid.FPCALC_COMMAND = str(fpcalc); duration, fingerprint = acoustid.fingerprint_file(path, force_fpcalc=True); progress.setLabelText("Querying AcoustID…"); QApplication.processEvents(); response = acoustid.lookup(key, fingerprint, duration, meta=["recordings", "releases", "releasegroups"]); matches = response.get("results", []) if isinstance(response, dict) else []; ids = [recording.get("id", "") for match in matches for recording in match.get("recordings", []) if isinstance(recording, dict)]; candidates = recordings_by_ids(ids); progress.close(); self.lookup_path = path; self.lookup_finished(candidates); return
            for match in matches:
                recordings = ", ".join(recording.get("id", "") for recording in match.get("recordings", []) if isinstance(recording, dict)); lines.append(f"Score {float(match.get('score', 0)):.3f} — {recordings or 'no MusicBrainz recording ID'}")
            QMessageBox.information(self, "AcoustID results", "\n".join(lines) if lines else "No AcoustID matches were found.")
        except Exception as exc:
            print(f"[AcoustID] {path}: {exc}", flush=True); QMessageBox.warning(self, "AcoustID lookup failed", str(exc))
        finally: progress.close()

    def lookup_finished(self, candidates):
        self.progress.setText(f"MusicBrainz lookup complete: {len(candidates)} candidates.")
        self.database.save_lookup_results(self.lookup_path, candidates, datetime.now(timezone.utc).isoformat())
        current = self.database.row_for_path(self.lookup_path); metadata_match = bool(candidates and current and all(str(candidates[0].get(key) or "").casefold() == str(current[field] or "").casefold() for key, field in (("artist", "artist"), ("album_artist", "album_artist"), ("release", "album"), ("title", "title"))))
        if metadata_match and current:
            self.database.set_status([self.lookup_path], "MB Complete" if str(current["artwork_state"] or "").lower() == "present" else "Artwork Review")
        dialog = QDialog(self); dialog.setWindowTitle("MusicBrainz candidates — review only"); dialog.resize(980, 480); box = QVBoxLayout(dialog); box.addWidget(QLabel(("Top match metadata matches the current file. You may still select it to review or replace missing artwork." if metadata_match else "Select a candidate to create an editable proposal.") + " Select exactly two candidates to compare their differences.")); results = QListWidget(); results.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection); labels = []
        for index, c in enumerate(candidates): labels.append(("[Metadata matches current] " if index == 0 and metadata_match else "") + f"Score {c['score']} | {c['artist']} — {c['title']} | length {c.get('length') or 'unknown'} ms | {c.get('disambiguation') or 'no disambiguation'} | release {c['release']} ({c['date'] or 'unknown'}) | {c.get('country') or 'country?'} / {c.get('status') or 'status?'} | recording {c['recording_id']}")
        results.addItems(labels or ["No candidates found."]); box.addWidget(results); actions = QHBoxLayout(); use = QPushButton("Use selected candidate"); compare = QPushButton("Compare two"); close = QPushButton("Close"); actions.addWidget(use); actions.addWidget(compare); actions.addWidget(close); box.addLayout(actions); close.clicked.connect(dialog.reject)
        close.setText("Cancel"); close.clicked.disconnect(); close.clicked.connect(lambda: (setattr(self, "review_canceled", True), dialog.reject()))
        def use_candidate():
            index = results.currentRow()
            if 0 <= index < len(candidates): dialog.accept(); self.show_proposal(candidates[index])
        def compare_candidates():
            selected = results.selectedIndexes()
            if len(selected) != 2:
                QMessageBox.information(dialog, "Select two candidates", "Select exactly two candidate rows to compare.")
                return
            first, second = candidates[selected[0].row()], candidates[selected[1].row()]
            labels = {"Artist": "artist", "Title": "title", "Length": "length", "Disambiguation": "disambiguation", "Release": "release", "Release group": "release_group", "Date": "date", "Country": "country", "Status": "status", "Genres": "genres", "Label": "label", "Barcode": "barcode", "Media": "media", "Works": "works", "Recording ID": "recording_id", "Release ID": "release_id", "Release group ID": "release_group_id"}
            differences = [f"{label}:\n  Candidate 1: {first.get(key) or 'unknown'}\n  Candidate 2: {second.get(key) or 'unknown'}" for label, key in labels.items() if first.get(key) != second.get(key)]
            QMessageBox.information(dialog, "Candidate differences", "\n\n".join(differences) if differences else "No differences were returned by MusicBrainz for these fields.")
        use.clicked.connect(use_candidate); compare.clicked.connect(compare_candidates); dialog.exec()

    def artwork_selected(self):
        row_index = self.table.currentRow()
        if row_index < 0: QMessageBox.information(self, "Select a file", "Select a catalog row before starting an artwork lookup."); return
        item = self.table.item(row_index, 2); path = item.data(32) if item else None; candidates = self.database.lookup_candidates(path) if path else []
        if not candidates or not candidates[0].get("release_id"): QMessageBox.information(self, "MusicBrainz release required", "Run MusicBrainz or AcoustID lookup first so an artwork release is available."); return
        self.lookup_path = path; selected = self.show_artwork_choices(candidates[0]["release_id"])
        if selected:
            self.preselected_artwork = selected; self.show_proposal(candidates[0])

    def convert_selected_wma(self):
        path = Path(getattr(self, "current_media_path", ""))
        if path.suffix.lower() != ".wma": QMessageBox.information(self, "Select a WMA", "Select a WMA file before converting."); return
        progress = QProgressDialog(f"Converting {path.name} to MP3…", "Cancel", 0, 0, self); progress.setWindowTitle("WMA conversion"); progress.setAutoClose(False); progress.setMinimumDuration(0); progress.setModal(True); progress.canceled.connect(lambda: progress.setLabelText("Cancel requested; finishing current conversion…")); progress.show(); QApplication.processEvents()
        try:
            progress.setLabelText(f"Waiting for Google Drive to make {path.name} available…"); QApplication.processEvents(); available = False
            for _ in range(30):
                try:
                    with path.open("rb") as handle: handle.read(1)
                    available = True; break
                except OSError:
                    if progress.wasCanceled(): break
                    time.sleep(1); QApplication.processEvents()
            if not available: raise FileNotFoundError(f"Google Drive did not make the WMA available locally: {path}")
            progress.setLabelText(f"Converting {path.name} to MP3…"); QApplication.processEvents()
            target = convert_wma_to_mp3(path, str(self.settings.value("ffmpeg_path", "ffmpeg"))); backup_dir = Path.home() / ".tempMp3Maint" / "backups" / "conversions" / datetime.now().strftime("%Y%m%d_%H%M%S"); backup_dir.mkdir(parents=True, exist_ok=True); backup_path = backup_dir / path.name; shutil.move(str(path), str(backup_path)); QMessageBox.information(self, "Conversion complete", f"Created:\n{target}\n\nOriginal WMA backup:\n{backup_path}\n\nSelect the MP3 and run MusicBrainz lookup to confirm its metadata."); self.refresh_table()
        except Exception as exc:
            print(f"[Convert] {path}: {exc}", flush=True); QMessageBox.warning(self, "WMA conversion failed", str(exc))
        finally:
            progress.close()

    def show_proposal(self, candidate):
        if self.active_plan_id is None and not self.ensure_active_plan(self.lookup_path): return
        self.selected_artwork = getattr(self, "preselected_artwork", None); self.preselected_artwork = None
        dialog = QDialog(self); dialog.setWindowTitle("Metadata proposal — review only"); form = QFormLayout(dialog); fields = {"Artist": candidate.get("artist", ""), "Album artist": candidate.get("album_artist", candidate.get("artist", "")), "Title": candidate.get("title", ""), "Album": candidate.get("release", ""), "Date": candidate.get("date", ""), "Genre": ", ".join(candidate.get("genres", [])), "Release group": candidate.get("release_group", ""), "Label": candidate.get("label", ""), "Barcode": candidate.get("barcode", "")}; current = self.database.row_for_path(self.lookup_path); current_values = {"Artist": current["artist"] if current else "", "Album artist": current["album_artist"] if current else "", "Title": current["title"] if current else "", "Album": current["album"] if current else "", "Date": current["year"] if current else "", "Genre": current["genre"] if current else "", "Release group": "", "Label": "", "Barcode": ""}; edits = {}
        form.addRow("", QLabel("Current value                         Proposed value"))
        for name, value in fields.items():
            current_value = str(current_values[name] or ""); current_label = QLabel(current_value or "—"); current_label.setWordWrap(True); edits[name] = QLineEdit(value); copy_current = QPushButton("Use current"); copy_current.clicked.connect(lambda checked=False, field=edits[name], source=current_value: field.setText(source)); row = QHBoxLayout(); row.addWidget(current_label, 1); row.addWidget(edits[name], 1); row.addWidget(copy_current); container = QWidget(); container.setLayout(row); form.addRow(f"{name}:", container)
        form.addRow("Status:", QLabel("User edited if changed; file remains unchanged.")); artwork_button = QPushButton("Find artwork"); local_button = QPushButton("Choose local artwork"); keep_button = QPushButton("Keep current embedded artwork"); placeholder_button = QPushButton("Use Artwork not found placeholder"); add_plan = QPushButton("Add proposal to active plan"); self.proposed_artwork = QLabel("No artwork selected"); cancel = QPushButton("Cancel"); form.addRow(artwork_button); form.addRow(local_button); form.addRow(keep_button); form.addRow(placeholder_button); form.addRow("Artwork proposal:", self.proposed_artwork); form.addRow(add_plan); form.addRow(cancel); artwork_button.clicked.connect(lambda: self.select_artwork_for_proposal(candidate.get("release_id", ""))); local_button.clicked.connect(self.choose_local_artwork); keep_button.clicked.connect(self.keep_current_artwork); placeholder_button.clicked.connect(self.use_artwork_placeholder); add_plan.clicked.connect(lambda: self.add_and_advance_proposal(dialog, candidate, edits)); cancel.clicked.connect(lambda: (setattr(self, "review_canceled", True), dialog.reject())); dialog.exec()

    def add_and_advance_proposal(self, dialog, candidate, edits):
        if self.add_proposal_to_plan(candidate, edits): dialog.accept()

    def add_proposal_to_plan(self, candidate, edits):
        if self.database.plan_status(self.active_plan_id) != "Pending":
            QMessageBox.information(self, "Plan is applied", "This plan has already been applied and cannot accept new tracks. Create or select a pending plan."); return
        proposal = {"artist": edits["Artist"].text(), "album_artist": edits["Album artist"].text(), "title": edits["Title"].text(), "album": edits["Album"].text(), "year": edits["Date"].text(), "genre": edits["Genre"].text(), "release_group": edits["Release group"].text(), "label": edits["Label"].text(), "barcode": edits["Barcode"].text(), "recording_id": candidate.get("recording_id", ""), "release_id": candidate.get("release_id", ""), "release_group_id": candidate.get("release_group_id", ""), "acoustid": candidate.get("acoustid", ""), "artwork": self.selected_artwork}
        self.database.add_plan_item(self.active_plan_id, self.lookup_path, proposal, datetime.now(timezone.utc).isoformat())
        self.database.update_plan_proposal(self.active_plan_id, self.lookup_path, proposal)
        return True

    def select_artwork_for_proposal(self, release_id):
        selected = self.show_artwork_choices(release_id)
        if selected:
            self.selected_artwork = selected
            self.proposed_artwork.setText(f"{selected.get('types') or 'Artwork'} — {selected.get('width') or '?'}×{selected.get('height') or '?'}\n{selected.get('url')}")

    def choose_local_artwork(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose local artwork", str(Path.home()), "Images (*.jpg *.jpeg *.png)")
        if path:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                QMessageBox.warning(self, "Invalid artwork", "The selected image could not be decoded.")
                return
            self.selected_artwork = {"source": "local", "path": path, "width": pixmap.width(), "height": pixmap.height()}; self.proposed_artwork.setText(f"Local artwork — {pixmap.width()}×{pixmap.height()}\n{path}")

    def keep_current_artwork(self):
        current = self.database.row_for_path(self.lookup_path)
        embedded = bool(current and str(current["artwork_state"] or "").lower() == "present")
        if not embedded:
            embedded = artwork_bytes(Path(self.lookup_path)) is not None
        if not embedded:
            QMessageBox.information(self, "No embedded artwork", "This file does not have artwork that can be kept.")
            return
        self.selected_artwork = {"source": "embedded", "action": "keep"}
        self.proposed_artwork.setText("Keep current embedded artwork — no artwork change")

    def use_artwork_placeholder(self):
        self.selected_artwork = {"source": "placeholder", "action": "replace", "unresolved": True}
        self.proposed_artwork.setText("Artwork not found — generic unresolved placeholder")

    def ensure_active_plan(self, file_path):
        prompt = QMessageBox(self); prompt.setWindowTitle("Plan required"); prompt.setText("This edit must belong to a plan."); create = prompt.addButton("Create new plan", QMessageBox.ButtonRole.AcceptRole); select = prompt.addButton("Select existing plan", QMessageBox.ButtonRole.ActionRole); prompt.addButton("Cancel", QMessageBox.ButtonRole.RejectRole); prompt.exec()
        if prompt.clickedButton() is create:
            name, accepted = QInputDialog.getText(self, "Create review plan", "Plan name:")
            if not accepted or not name.strip(): return False
            self.active_plan_id = self.database.create_plan(name.strip(), [file_path], datetime.now(timezone.utc).isoformat(), {file_path: {}}); self.active_plan_name = name.strip(); self.plan_label.setText(f"Active plan: {self.active_plan_name} (#{self.active_plan_id})"); return True
        if prompt.clickedButton() is select:
            self.show_saved_plans(); return self.active_plan_id is not None
        return False

    def show_artwork_choices(self, release_id):
        progress = QProgressDialog("Looking up artwork…", None, 0, 0, self); progress.setWindowTitle("Artwork lookup"); progress.setMinimumDuration(0); progress.setAutoClose(False); progress.setModal(True); progress.show(); QApplication.processEvents()
        lookup_url = f"https://coverartarchive.org/release/{release_id}"
        lookup_error = None
        try:
            images = release_images(release_id)
        except Exception as exc:
            message = f"URL:\n{lookup_url}\n\nError: {exc}"
            print(f"[Artwork lookup] {message}", flush=True)
            lookup_error = f"Online artwork lookup: NOT FOUND/ERROR — {exc}"
            images = []
        if not images and self.lookup_path:
            row = self.database.row_for_path(self.lookup_path)
            try:
                images = itunes_images(row["artist"] if row else "", row["album"] if row else "", row["title"] if row else "")
                if images: lookup_error = "Cover Art Archive returned no artwork; Apple artwork results are shown below."
            except Exception as exc:
                print(f"[Artwork lookup] Apple iTunes fallback failed: {exc}", flush=True)
        progress.setLabelText("Downloading artwork previews…"); QApplication.processEvents()
        dialog = QDialog(self); dialog.setWindowTitle("Cover Art Archive — review only"); dialog.resize(860, 560); layout = QVBoxLayout(dialog); layout.addWidget(QLabel("Prefer Front artwork with the largest clear image. Choose an image for the proposal; no file changes are made.")); choices = QListWidget(); choices.setIconSize(QSize(96, 96)); choices.setMinimumHeight(300)
        choice_images = {}
        embedded_data = artwork_bytes(Path(self.lookup_path)) if self.lookup_path else None
        if embedded_data:
            embedded_pixmap = QPixmap(); embedded_pixmap.loadFromData(embedded_data); embedded = {"source": "embedded", "action": "keep", "types": "Current embedded", "width": embedded_pixmap.width(), "height": embedded_pixmap.height(), "url": "Embedded in file"}; choice_images[choices.count()] = embedded; item = QListWidgetItem(f"Current embedded — {embedded_pixmap.width()}×{embedded_pixmap.height()} — keep unchanged"); item.setIcon(QIcon(embedded_pixmap.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))); choices.addItem(item)
        if not images:
            item = QListWidgetItem(lookup_error or "Online artwork: NOT FOUND — no images were returned"); item.setFlags(Qt.ItemFlag.NoItemFlags); choices.addItem(item)
        for image in images:
            label = f"{'Front' if image['front'] else image['types'] or 'Other'} — {image.get('width') or '?'}×{image.get('height') or '?'} — {image['url']}"
            choice_images[choices.count()] = image; choices.addItem(label)
            if image.get("thumb"):
                try:
                    context = ssl.create_default_context(cafile=certifi.where())
                    with urlopen(image["thumb"], timeout=10, context=context) as response:
                        pixmap = QPixmap(); pixmap.loadFromData(response.read()); actual = f"{pixmap.width()}×{pixmap.height()}"; choices.item(choices.count() - 1).setText(label.replace(f"{image.get('width') or '?'}×{image.get('height') or '?'}", actual)); choices.item(choices.count() - 1).setIcon(QIcon(pixmap.scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
                except Exception as exc:
                    error_text = f"Thumbnail download error: {exc}"
                    choices.item(choices.count() - 1).setText(f"{label} — {error_text}")
                    print(f"[Artwork] {image.get('thumb')}: {error_text}", flush=True)
        layout.addWidget(choices); actions = QHBoxLayout(); select = QPushButton("Use selected artwork"); close = QPushButton("Close"); actions.addWidget(select); actions.addWidget(close); layout.addLayout(actions); selected_image = {"value": None}
        def accept_selection():
            index = choices.currentRow()
            if index in choice_images: selected_image["value"] = choice_images[index]; dialog.accept()
        select.clicked.connect(accept_selection); close.clicked.connect(dialog.reject); progress.close(); dialog.exec(); return selected_image["value"]

    def closeEvent(self, event):
        try:
            running = (self.thread is not None and self.thread.isRunning()) or (self.lookup_thread is not None and self.lookup_thread.isRunning()) or (self.batch_thread is not None and self.batch_thread.isRunning())
        except RuntimeError:
            running = False
        if running: QMessageBox.warning(self, "Scan active", "Wait for the scan to finish before closing."); event.ignore(); return
        self.database.close(); event.accept()

def main():
    app = QApplication(sys.argv); window = MainWindow(); window.show(); return app.exec()

if __name__ == "__main__": raise SystemExit(main())
