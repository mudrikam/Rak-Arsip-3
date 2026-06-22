from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel, QPushButton, QListWidget,
    QAbstractItemView, QHBoxLayout, QMessageBox, QDialog, QProgressBar,
    QFileDialog, QListWidgetItem, QComboBox, QFrame, QSizePolicy
)
from PySide6.QtCore import QCoreApplication, QThread, Signal, Qt
import qtawesome as qta
import os
import csv
from datetime import datetime, date


class _BackupWorker(QThread):
    """Background worker that runs backup or restore without freezing the UI.

    Emits:
      - progress(stage:str, processed:int, total:int|None)  for progress updates
      - finished_ok(message:str)  on success
      - failed(error:str)  on error
    """
    progress = Signal(str, int, object)   # stage, processed, total (None when unknown)
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, helper, mode, **kwargs):
        super().__init__()
        self.helper = helper
        self.mode = mode  # 'export_csv' | 'import_csv' | 'export_sql' | 'import_sql'
        self.kwargs = kwargs

    def run(self):
        try:
            if self.mode == 'export_csv':
                self.helper.export_to_csv(
                    self.kwargs['path'],
                    progress_callback=lambda p, t: self.progress.emit('csv', p, t),
                )
            elif self.mode == 'import_csv':
                self.helper.import_from_csv(
                    self.kwargs['path'],
                    progress_callback=lambda p, t: self.progress.emit('csv', p, t),
                    resolution_mode=self.kwargs.get('resolution_mode', 'skip'),
                )
            elif self.mode == 'export_sql':
                self.helper.export_database(
                    self.kwargs['path'],
                    use_pg_dump=self.kwargs.get('use_pg_dump', True),
                    progress_callback=lambda stage, p, t: self.progress.emit(stage, p, t),
                )
            elif self.mode == 'import_sql':
                self.helper.import_database(
                    self.kwargs['path'],
                    progress_callback=lambda stage, p, t: self.progress.emit(stage, p, t),
                )
            else:
                raise ValueError(f"Unknown worker mode: {self.mode}")
            self.finished_ok.emit(self.kwargs.get('success_message', 'Done.'))
        except Exception as e:
            self.failed.emit(str(e))


class PreferencesBackupHelper:
    """Helper class for Backup/Restore tab in Preferences window"""

    def __init__(self, parent, db_manager):
        self.parent = parent
        self.db_manager = db_manager
        self._worker = None
        self._progress_dialog = None
        self._progress_bar = None
        self._progress_label = None

    # ------------------------------------------------------------------ UI

    def create_backup_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(12, 12, 12, 12)
        tab_layout.setSpacing(12)

        # ============================================================
        # Section 1: Manual export / import
        # ============================================================
        manual_group = QGroupBox("Manual Backup and Restore")
        manual_group.setObjectName("manualBackupGroup")
        manual_layout = QVBoxLayout(manual_group)
        manual_layout.setContentsMargins(12, 16, 12, 12)
        manual_layout.setSpacing(10)

        manual_layout.addWidget(self._make_description(
            "Export the current database to a file, or restore from a previous export. "
            "CSV is portable and human-readable; SQL preserves the full PostgreSQL schema "
            "and is the recommended format for large databases."
        ))

        actions_row = QHBoxLayout()
        actions_row.setSpacing(12)
        actions_row.setContentsMargins(0, 0, 0, 0)

        # ---- Export column ----
        export_box = QGroupBox("Export")
        export_box.setObjectName("exportBox")
        export_layout = QVBoxLayout(export_box)
        export_layout.setContentsMargins(12, 14, 12, 12)
        export_layout.setSpacing(8)

        self.parent.backup_btn = QPushButton(qta.icon("fa6s.file-csv"), " Export to CSV")
        self.parent.backup_btn.setMinimumHeight(34)
        self.parent.backup_btn.setCursor(Qt.PointingHandCursor)
        self.parent.backup_btn.setToolTip(
            "Export all database tables to a single CSV file. Best for small/medium "
            "databases that you want to inspect or share."
        )
        export_layout.addWidget(self.parent.backup_btn)

        self.parent.backup_sql_btn = QPushButton(qta.icon("fa6s.file-export"), " Export to SQL (.sql)")
        self.parent.backup_sql_btn.setMinimumHeight(34)
        self.parent.backup_sql_btn.setCursor(Qt.PointingHandCursor)
        self.parent.backup_sql_btn.setToolTip(
            "Export the full database to a SQL script. Recommended for large databases; "
            "uses pg_dump if available, otherwise the built-in streaming engine."
        )
        export_layout.addWidget(self.parent.backup_sql_btn)

        actions_row.addWidget(export_box, 1)

        # ---- Import column ----
        import_box = QGroupBox("Import")
        import_box.setObjectName("importBox")
        import_layout = QVBoxLayout(import_box)
        import_layout.setContentsMargins(12, 14, 12, 12)
        import_layout.setSpacing(8)

        self.parent.restore_btn = QPushButton(qta.icon("fa6s.file-import"), " Import from CSV")
        self.parent.restore_btn.setMinimumHeight(34)
        self.parent.restore_btn.setCursor(Qt.PointingHandCursor)
        self.parent.restore_btn.setToolTip(
            "Restore from a CSV file previously exported by this application. "
            "You will be asked how to resolve conflicts with existing records."
        )
        import_layout.addWidget(self.parent.restore_btn)

        self.parent.restore_sql_btn = QPushButton(qta.icon("fa6s.database"), " Import from SQL (.sql)")
        self.parent.restore_sql_btn.setMinimumHeight(34)
        self.parent.restore_sql_btn.setCursor(Qt.PointingHandCursor)
        self.parent.restore_sql_btn.setToolTip(
            "Restore the database from a SQL script. Works with both this application's "
            "format and pg_dump's plain-text output."
        )
        import_layout.addWidget(self.parent.restore_sql_btn)

        actions_row.addWidget(import_box, 1)

        manual_layout.addLayout(actions_row)

        # ---- Toolchain status hint (one clean line, full width) ----
        tool_hint_frame = QFrame()
        tool_hint_frame.setObjectName("toolHintFrame")
        tool_hint_frame.setFrameShape(QFrame.StyledPanel)
        tool_hint_layout = QHBoxLayout(tool_hint_frame)
        tool_hint_layout.setContentsMargins(10, 8, 10, 8)
        tool_hint_layout.setSpacing(8)

        backup_helper = self.db_manager.backup_helper
        tools = []
        if backup_helper.has_pg_dump():
            tools.append("pg_dump")
        if backup_helper.has_pg_restore():
            tools.append("pg_restore")
        if backup_helper.has_psql():
            tools.append("psql")

        if tools:
            hint_icon = qta.icon("fa6s.circle-check", color="#2e7d32")
            tools_text = ", ".join(tools)
            hint_text = (
                f"<b>PostgreSQL client tools detected:</b> {tools_text}. "
                f"SQL operations will use them when available; the built-in streaming "
                f"engine is used as a fallback."
            )
        else:
            hint_icon = qta.icon("fa6s.circle-info", color="#1976d2")
            hint_text = (
                f"<b>PostgreSQL client tools not found on PATH.</b> "
                f"SQL operations will use the built-in streaming engine, which is safe "
                f"for large databases. Install pg_dump / pg_restore / psql for the "
                f"fastest backup and restore experience."
            )

        hint_icon_label = QLabel()
        hint_icon_label.setPixmap(hint_icon.pixmap(18, 18))
        hint_icon_label.setFixedWidth(22)
        tool_hint_layout.addWidget(hint_icon_label, 0, Qt.AlignTop)

        hint_text_label = QLabel(hint_text)
        hint_text_label.setWordWrap(True)
        hint_text_label.setTextFormat(Qt.RichText)
        hint_text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tool_hint_layout.addWidget(hint_text_label, 1)

        manual_layout.addWidget(tool_hint_frame)

        tab_layout.addWidget(manual_group)

        # ============================================================
        # Section 2: Automatic daily backups
        # ============================================================
        auto_group = QGroupBox("Automatic Daily Backups")
        auto_group.setObjectName("autoBackupGroup")
        auto_layout = QVBoxLayout(auto_group)
        auto_layout.setContentsMargins(12, 16, 12, 12)
        auto_layout.setSpacing(8)

        auto_layout.addWidget(self._make_description(
            "The application automatically creates a daily SQL backup of the database. "
            "The last 7 days are kept. You can also create a backup on demand."
        ))

        # Top action bar
        auto_toolbar = QHBoxLayout()
        auto_toolbar.setContentsMargins(0, 0, 0, 0)
        auto_toolbar.setSpacing(8)

        self.parent.backup_db_btn = QPushButton(qta.icon("fa6s.database"), " Create Backup Now")
        self.parent.backup_db_btn.setMinimumHeight(32)
        self.parent.backup_db_btn.setCursor(Qt.PointingHandCursor)
        self.parent.backup_db_btn.setToolTip("Create a SQL backup immediately and add it to the list below.")
        self.parent.backup_db_btn.clicked.connect(self.backup_database_now)
        auto_toolbar.addWidget(self.parent.backup_db_btn)
        auto_toolbar.addStretch()

        self.parent.db_backup_list_label = QLabel("<b>Recent backups</b>")
        self.parent.db_backup_list_label.setTextFormat(Qt.RichText)
        auto_toolbar.addWidget(self.parent.db_backup_list_label)
        auto_layout.addLayout(auto_toolbar)

        self.parent.db_backup_list_widget = QListWidget()
        self.parent.db_backup_list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.parent.db_backup_list_widget.setAlternatingRowColors(True)
        self.parent.db_backup_list_widget.setUniformItemSizes(False)
        self.parent.db_backup_list_widget.setMinimumHeight(180)
        self.parent.db_backup_list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        auto_layout.addWidget(self.parent.db_backup_list_widget, 1)

        tab_layout.addWidget(auto_group, 1)

        # Signals
        self.parent.backup_btn.clicked.connect(self.backup_database_csv)
        self.parent.restore_btn.clicked.connect(self.restore_database_csv)
        self.parent.backup_sql_btn.clicked.connect(self.backup_database_sql)
        self.parent.restore_sql_btn.clicked.connect(self.restore_database_sql)

        return tab

    def _make_description(self, text):
        """Return a consistently styled description label."""
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("color: #555;")
        return label

    def refresh_db_backup_list(self):
        """Refresh the database backup list"""
        self.parent.db_backup_list_widget.clear()
        backup_dir = os.path.join(self.db_manager.db_dir, "db_backups")
        if not os.path.exists(backup_dir):
            return
        backup_files = []
        for fname in os.listdir(backup_dir):
            if fname.startswith("archive_database_") and fname.endswith(".sql"):
                fpath = os.path.join(backup_dir, fname)
                backup_files.append((fpath, os.path.getmtime(fpath)))
        backup_files.sort(key=lambda x: x[1], reverse=True)
        for fpath, mtime in backup_files:
            dt = datetime.fromtimestamp(mtime)
            days_old = self._get_days_old_from_filename(fpath)
            fname = os.path.basename(fpath)
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(6, 4, 6, 4)
            item_layout.setSpacing(8)
            label = QLabel(f"{fname}  ({dt.strftime('%Y-%m-%d %H:%M:%S')})")
            if days_old == 0:
                label.setStyleSheet("color: #1976d2;")
            else:
                label.setStyleSheet("color: #555;")
            item_layout.addWidget(label, 1)
            restore_btn = QPushButton(qta.icon("fa6s.rotate-left"), " Restore")
            restore_btn.setCursor(Qt.PointingHandCursor)
            restore_btn.setFixedHeight(26)
            restore_btn.clicked.connect(lambda checked, path=fpath, days=days_old: self.restore_db_backup_clicked(path, days))
            item_layout.addWidget(restore_btn)
            item_widget.setLayout(item_layout)
            list_item = QListWidgetItem()
            list_item.setSizeHint(item_widget.sizeHint())
            self.parent.db_backup_list_widget.addItem(list_item)
            self.parent.db_backup_list_widget.setItemWidget(list_item, item_widget)

    def _get_days_old_from_filename(self, db_file_path):
        """Calculate days old from filename"""
        fname = os.path.basename(db_file_path)
        try:
            base = fname.replace("archive_database_", "").replace(".sql", "")
            dt = datetime.strptime(base, "%Y%m%d").date()
            days_old = (date.today() - dt).days
            return days_old if days_old >= 0 else 0
        except Exception:
            return 0

    # ------------------------------------------------------------------ daily backup actions

    def restore_db_backup_clicked(self, backup_path, backup_days_old):
        """Handle restore backup button click"""
        dt = datetime.fromtimestamp(os.path.getmtime(backup_path))
        age_str = f"{backup_days_old} day{'s' if backup_days_old != 1 else ''}"
        msg = (
            f"This backup is {age_str} old (created {dt.strftime('%Y-%m-%d %H:%M:%S')}).\n"
            f"Restoring will overwrite the current database contents.\n\n"
            f"Continue?"
        )
        reply = QMessageBox.question(self.parent, "Restore Database Backup", msg)
        if reply == QMessageBox.Yes:
            self._run_import_worker(
                mode='import_sql',
                path=backup_path,
                success_message="Database restored from backup.",
            )

    def backup_database_now(self):
        """Create immediate database backup (runs in background thread)."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(self.db_manager.db_dir, "db_backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f"manual_database_{timestamp}.sql")

        self._run_export_worker(
            mode='export_sql',
            path=backup_path,
            success_message=f"Database backup created:\n{backup_path}",
            extra_kwargs={'use_pg_dump': self.db_manager.backup_helper.has_pg_dump()},
            on_success=lambda: self.refresh_db_backup_list(),
        )

    # ------------------------------------------------------------------ CSV actions

    def backup_database_csv(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"Rak_Arsip_Database_Backup_{timestamp}.csv"
        filename, _ = QFileDialog.getSaveFileName(
            self.parent, "Save Database Backup (CSV)", default_filename, "CSV Files (*.csv)"
        )
        if not filename:
            return

        # Pre-count rows for progress (cheap; runs once on the main thread)
        try:
            total_rows = 0
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            for table_name in self.db_manager.backup_helper.get_all_user_tables():
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                total_rows += cursor.fetchone()[0]
            self.db_manager.close()
        except Exception:
            total_rows = 0

        self._start_progress_dialog(
            title="Exporting Data",
            label_text="Exporting data to CSV, please wait...",
            total=total_rows if total_rows > 0 else 100,
            indeterminate=(total_rows <= 0),
        )

        self._run_export_worker(
            mode='export_csv',
            path=filename,
            success_message=f"Database backup saved to:\n{filename}",
        )

    def restore_database_csv(self):
        """Import database from CSV file"""
        filename, _ = QFileDialog.getOpenFileName(
            self.parent, "Select Database Backup", "", "CSV Files (*.csv)"
        )
        if not filename:
            return

        import_summary = self._analyze_csv_import(filename)
        if not import_summary:
            QMessageBox.critical(self.parent, "Error", "Failed to analyze CSV file.")
            return

        resolution_mode = self._show_import_summary_dialog(import_summary)
        if resolution_mode is None:
            return

        self._start_progress_dialog(
            title="Importing Data",
            label_text="Importing data from CSV, please wait...",
            total=import_summary['total_records'] if import_summary['total_records'] > 0 else 100,
            indeterminate=(import_summary['total_records'] <= 0),
        )

        self._run_import_worker(
            mode='import_csv',
            path=filename,
            success_message="Database imported successfully.",
            extra_kwargs={'resolution_mode': resolution_mode},
        )

    # ------------------------------------------------------------------ SQL actions

    def backup_database_sql(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"Rak_Arsip_Database_Backup_{timestamp}.sql"
        filename, _ = QFileDialog.getSaveFileName(
            self.parent, "Save Database Backup (SQL)", default_filename, "SQL Files (*.sql)"
        )
        if not filename:
            return

        self._start_progress_dialog(
            title="Backing Up Database",
            label_text="Creating SQL backup, please wait...",
            total=100,
            indeterminate=True,
        )

        self._run_export_worker(
            mode='export_sql',
            path=filename,
            success_message=f"Database SQL backup saved to:\n{filename}",
            extra_kwargs={'use_pg_dump': self.db_manager.backup_helper.has_pg_dump()},
        )

    def restore_database_sql(self):
        """Import database from SQL file (.sql)."""
        filename, _ = QFileDialog.getOpenFileName(
            self.parent, "Select SQL Backup", "", "SQL Files (*.sql);;All Files (*)"
        )
        if not filename:
            return

        reply = QMessageBox.question(
            self.parent,
            "Confirm SQL Restore",
            "Restoring from SQL will overwrite the current database contents.\n"
            "This action cannot be undone.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._start_progress_dialog(
            title="Restoring Database",
            label_text="Importing SQL backup, please wait...",
            total=100,
            indeterminate=True,
        )

        self._run_import_worker(
            mode='import_sql',
            path=filename,
            success_message="Database restored from SQL backup.",
        )

    # ------------------------------------------------------------------ worker plumbing

    def _run_export_worker(self, *, mode, path, success_message, extra_kwargs=None, on_success=None):
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(self.parent, "Busy", "A backup/restore operation is already running.")
            return

        kwargs = {'path': path, 'success_message': success_message}
        if extra_kwargs:
            kwargs.update(extra_kwargs)

        worker = _BackupWorker(self.db_manager.backup_helper, mode, **kwargs)
        worker.progress.connect(self._on_worker_progress)
        worker.finished_ok.connect(lambda msg: self._on_worker_success(msg, on_success))
        worker.failed.connect(self._on_worker_failed)
        # Worker is owned by this helper; once finished it cleans itself up.
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

    def _run_import_worker(self, *, mode, path, success_message, extra_kwargs=None, on_success=None):
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(self.parent, "Busy", "A backup/restore operation is already running.")
            return

        # Close any open connection on the main thread before the worker opens its own.
        try:
            self.db_manager.close()
        except Exception:
            pass

        kwargs = {'path': path, 'success_message': success_message}
        if extra_kwargs:
            kwargs.update(extra_kwargs)

        worker = _BackupWorker(self.db_manager.backup_helper, mode, **kwargs)
        worker.progress.connect(self._on_worker_progress)
        worker.finished_ok.connect(lambda msg: self._on_worker_success(msg, on_success))
        worker.failed.connect(self._on_worker_failed)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

    def _on_worker_progress(self, stage, processed, total):
        if not self._progress_dialog or not self._progress_bar:
            return
        stage_labels = {
            'csv': 'Processing rows',
            'copy': 'Streaming database to file',
            'pg_dump': 'Running pg_dump',
            'restore': 'Executing SQL statements',
            'psql': 'Running psql',
            'pg_restore': 'Running pg_restore',
            'analyze': 'Analyzing backup file',
            'done': 'Finalizing',
        }
        label = stage_labels.get(stage, stage)
        self._progress_label.setText(f"{label}... please wait")
        if total is not None and total > 0 and not self._progress_bar.maximum() == 0:
            if self._progress_bar.maximum() != total:
                self._progress_bar.setMaximum(total)
            self._progress_bar.setValue(min(processed, total))
        else:
            # Indeterminate: just nudge the bar so it animates
            if not self._progress_bar.maximum() == 0:
                self._progress_bar.setMaximum(0)

    def _on_worker_success(self, message, on_success=None):
        self._close_progress_dialog()
        QMessageBox.information(self.parent, "Success", message)
        if on_success:
            try:
                on_success()
            except Exception as e:
                print(f"[BACKUP] post-success callback failed: {e}")

    def _on_worker_failed(self, error):
        self._close_progress_dialog()
        QMessageBox.critical(self.parent, "Error", f"Operation failed:\n{error}")

    def _start_progress_dialog(self, *, title, label_text, total, indeterminate=False):
        dlg = QDialog(self.parent)
        dlg.setWindowTitle(title)
        dlg.setModal(True)
        dlg.setMinimumWidth(420)
        vbox = QVBoxLayout(dlg)
        self._progress_label = QLabel(label_text)
        vbox.addWidget(self._progress_label)
        bar = QProgressBar(dlg)
        bar.setMinimum(0)
        if indeterminate or total <= 0:
            bar.setMaximum(0)  # indeterminate animation
        else:
            bar.setMaximum(total)
            bar.setValue(0)
        vbox.addWidget(bar)
        dlg.setLayout(vbox)
        dlg.show()
        QCoreApplication.processEvents()
        self._progress_dialog = dlg
        self._progress_bar = bar
        self.parent.progress_bar = bar

    def _close_progress_dialog(self):
        if self._progress_dialog is not None:
            try:
                self._progress_dialog.accept()
            except Exception:
                pass
            self._progress_dialog = None
        self._progress_bar = None
        self._progress_label = None
        self.parent.progress_bar = None

    # ------------------------------------------------------------------ CSV helpers (unchanged)

    def _show_import_summary_dialog(self, import_summary):
        """Show import summary dialog with conflict resolution options"""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Confirm CSV Import")
        dialog.setModal(True)
        dialog.setMinimumWidth(500)

        layout = QVBoxLayout(dialog)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon("fa6s.circle-question", color="#1976d2").pixmap(48, 48))

        summary_msg = f"<b>Import Summary:</b><br><br>"
        summary_msg += f"Total records to import: <b>{import_summary['total_records']}</b><br>"
        summary_msg += f"Tables affected: <b>{len(import_summary['tables'])}</b><br><br>"

        if import_summary['tables']:
            summary_msg += "<b>Records per table:</b><br>"
            for table_name, count in import_summary['tables'].items():
                summary_msg += f"&nbsp;&nbsp;• {table_name}: {count} records<br>"

        summary_msg += f"<br>⚠ <b>Potential conflicts: {import_summary['potential_conflicts']}</b><br>"

        summary_label = QLabel(summary_msg)
        summary_label.setWordWrap(True)

        resolution_label = QLabel("<b>Conflict Resolution:</b>")
        resolution_combo = QComboBox()
        resolution_combo.addItem(qta.icon("fa6s.arrows-rotate"), "Replace - Overwrite existing records", "replace")
        resolution_combo.addItem(qta.icon("fa6s.copy"), "Keep Both - Duplicate with new ID", "keep_both")
        resolution_combo.addItem(qta.icon("fa6s.ban"), "Skip Existing - Only add new records", "skip")
        resolution_combo.setCurrentIndex(2)

        header_layout = QHBoxLayout()
        header_layout.addWidget(icon_label)
        header_layout.addWidget(summary_label, 1)

        layout.addLayout(header_layout)
        layout.addSpacing(10)
        layout.addWidget(resolution_label)
        layout.addWidget(resolution_combo)
        layout.addSpacing(10)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_button = QPushButton("Continue")
        ok_button.setIcon(qta.icon("fa6s.circle-check"))
        ok_button.clicked.connect(dialog.accept)

        cancel_button = QPushButton("Cancel")
        cancel_button.setIcon(qta.icon("fa6s.circle-xmark"))
        cancel_button.clicked.connect(dialog.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        if dialog.exec() == QDialog.Accepted:
            return resolution_combo.currentData()
        return None

    def _analyze_csv_import(self, filename):
        """Analyze CSV file and return import summary"""
        try:
            tables = {}
            total_rows = 0
            current_table = None

            with open(filename, 'r', encoding='utf-8') as csvfile:
                for row in csv.reader(csvfile):
                    if not row:
                        continue

                    if row[0] == "TABLE":
                        current_table = row[1] if len(row) > 1 else None
                        if current_table and current_table not in tables:
                            tables[current_table] = 0
                    elif current_table:
                        tables[current_table] += 1
                        total_rows += 1

            existing_records = self._count_existing_records(list(tables.keys()))
            potential_conflicts = sum(min(tables.get(t, 0), existing_records.get(t, 0)) for t in tables.keys())

            return {
                'total_records': total_rows,
                'tables': tables,
                'potential_conflicts': potential_conflicts
            }
        except Exception as e:
            print(f"[CSV Import] Error analyzing file: {e}")
            return None

    def _count_existing_records(self, table_names):
        """Count existing records in specified tables"""
        counts = {}
        try:
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()

            for table_name in table_names:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    counts[table_name] = cursor.fetchone()[0]
                except Exception:
                    counts[table_name] = 0

            self.db_manager.close()
        except Exception as e:
            print(f"[CSV Import] Error counting records: {e}")

        return counts