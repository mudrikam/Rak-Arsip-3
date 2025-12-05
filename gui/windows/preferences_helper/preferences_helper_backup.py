from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel, QPushButton, QListWidget, 
    QAbstractItemView, QHBoxLayout, QMessageBox, QDialog, QProgressBar,
    QFileDialog, QListWidgetItem, QComboBox
)
from PySide6.QtCore import QCoreApplication
import qtawesome as qta
import os
import shutil
import csv
import sys
from datetime import datetime, date


class PreferencesBackupHelper:
    """Helper class for Backup/Restore tab in Preferences window"""
    
    def __init__(self, parent, db_manager):
        self.parent = parent
        self.db_manager = db_manager
        
    def create_backup_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        csv_group = QGroupBox("CSV Backup and Restore")
        csv_layout = QHBoxLayout(csv_group)
        
        export_section = QVBoxLayout()
        export_label = QLabel("Export to CSV")
        export_label.setStyleSheet("font-weight: bold;")
        export_section.addWidget(export_label)
        export_info = QLabel("Export all database data to CSV file for backup purposes.")
        export_info.setWordWrap(True)
        export_info.setMinimumHeight(40)
        export_section.addWidget(export_info)
        self.parent.backup_btn = QPushButton("Export Database to CSV")
        self.parent.backup_btn.setIcon(qta.icon("fa6s.file-export"))
        export_section.addWidget(self.parent.backup_btn)
        export_section.addStretch()
        
        import_section = QVBoxLayout()
        import_label = QLabel("Import from CSV")
        import_label.setStyleSheet("font-weight: bold;")
        import_section.addWidget(import_label)
        import_info = QLabel("Import CSV files exported by this application to restore database data.")
        import_info.setWordWrap(True)
        import_info.setMinimumHeight(40)
        import_section.addWidget(import_info)
        self.parent.restore_btn = QPushButton("Import Database from CSV")
        self.parent.restore_btn.setIcon(qta.icon("fa6s.file-import"))
        import_section.addWidget(self.parent.restore_btn)
        import_section.addStretch()
        
        csv_layout.addLayout(export_section, 1)
        csv_layout.addLayout(import_section, 1)
        
        db_backup_group = QGroupBox("Database File Backup")
        db_backup_layout = QVBoxLayout(db_backup_group)
        
        db_backup_info = QLabel("Create a complete database file backup (.db file).")
        db_backup_info.setWordWrap(True)
        db_backup_layout.addWidget(db_backup_info)

        self.parent.backup_db_btn = QPushButton("Backup Database Now")
        self.parent.backup_db_btn.setIcon(qta.icon("fa6s.database"))
        self.parent.backup_db_btn.clicked.connect(self.backup_database_now)
        db_backup_layout.addWidget(self.parent.backup_db_btn)

        self.parent.db_backup_list_label = QLabel("Database Backups (last 7 days):")
        db_backup_layout.addWidget(self.parent.db_backup_list_label)
        self.parent.db_backup_list_widget = QListWidget()
        self.parent.db_backup_list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        db_backup_layout.addWidget(self.parent.db_backup_list_widget)
        self.parent.db_backup_list_widget.setMinimumHeight(180)
        self.parent.db_backup_list_widget.setMaximumHeight(220)
        self.parent.db_backup_list_widget.setAlternatingRowColors(True)
        
        layout.addWidget(csv_group)
        layout.addWidget(db_backup_group)
        layout.addStretch()
        
        self.parent.backup_btn.clicked.connect(self.backup_database)
        self.parent.restore_btn.clicked.connect(self.restore_database)
        
        return tab
        
    def refresh_db_backup_list(self):
        """Refresh the database backup list"""
        self.parent.db_backup_list_widget.clear()
        db_path = self.db_manager.db_path
        backup_dir = os.path.join(os.path.dirname(db_path), "db_backups")
        if not os.path.exists(backup_dir):
            return
        backup_files = []
        for fname in os.listdir(backup_dir):
            if fname.startswith("archive_database_") and fname.endswith(".db"):
                fpath = os.path.join(backup_dir, fname)
                backup_files.append((fpath, os.path.getmtime(fpath)))
        backup_files.sort(key=lambda x: x[1], reverse=True)
        for fpath, mtime in backup_files:
            dt = datetime.fromtimestamp(mtime)
            days_old = self._get_days_old_from_filename(fpath)
            fname = os.path.basename(fpath)
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(2, 2, 2, 2)
            label = QLabel(f"{fname}  ({dt.strftime('%Y-%m-%d %H:%M:%S')})")
            if days_old == 0:
                label.setStyleSheet("color: #1976d2;")
            else:
                label.setStyleSheet("color: #666;")
            item_layout.addWidget(label)
            item_layout.addStretch()
            restore_btn = QPushButton("Restore")
            restore_btn.setIcon(qta.icon("fa6s.rotate-left"))
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
            base = fname.replace("archive_database_", "").replace(".db", "")
            dt = datetime.strptime(base, "%Y%m%d").date()
            days_old = (date.today() - dt).days
            return days_old if days_old >= 0 else 0
        except Exception:
            return 0

    def restore_db_backup_clicked(self, backup_path, backup_days_old):
        """Handle restore backup button click"""
        db_path = self.db_manager.db_path
        db_dir = os.path.dirname(db_path)
        old_db_path = os.path.join(db_dir, "archive_database_old.db")
        dt = datetime.fromtimestamp(os.path.getmtime(backup_path))
        age_str = f"{backup_days_old} day{'s' if backup_days_old != 1 else ''}"
        msg = f"This backup is {age_str} old (based on filename, backup file created {dt.strftime('%Y-%m-%d %H:%M:%S')}).\nAre you sure you want to restore this backup?\n\nThe current database will be saved as archive_database_old.db."
        reply = QMessageBox.question(self.parent, "Restore Database Backup", msg)
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(db_path):
                    shutil.copy2(db_path, old_db_path)
                shutil.copy2(backup_path, db_path)
                QMessageBox.information(self.parent, "Success", "Database restored from backup.\nPlease restart the application for changes to take effect.")
            except Exception as e:
                QMessageBox.critical(self.parent, "Error", f"Failed to restore database: {e}")

    def backup_database_now(self):
        """Create immediate database backup"""
        backup_path = self.db_manager.manual_backup_database()
        if backup_path:
            QMessageBox.information(self.parent, "Success", f"Database backup created:\n{backup_path}")
            self.refresh_db_backup_list()
        else:
            QMessageBox.critical(self.parent, "Error", "Failed to create database backup.")

    def backup_database(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"Rak_Arsip_Database_Backup_{timestamp}.csv"
        filename, _ = QFileDialog.getSaveFileName(
            self.parent, "Save Database Backup", default_filename, "CSV Files (*.csv)"
        )
        if filename:
            progress_dialog = QDialog(self.parent)
            progress_dialog.setWindowTitle("Exporting Data")
            progress_dialog.setModal(True)
            vbox = QVBoxLayout(progress_dialog)
            label = QLabel("Exporting data, please wait...")
            vbox.addWidget(label)
            progress_bar = QProgressBar(progress_dialog)
            vbox.addWidget(progress_bar)
            progress_dialog.setLayout(vbox)
            self.parent.progress_bar = progress_bar

            total_rows = 0
            self.db_manager.connect(write=False)
            cursor = self.db_manager.connection.cursor()
            
            backup_helper = self.db_manager.backup_helper
            tables = backup_helper.get_all_user_tables()
            
            for table_name in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                total_rows += cursor.fetchone()[0]
            
            self.db_manager.close()

            progress_bar.setMinimum(0)
            progress_bar.setMaximum(total_rows)
            progress_bar.setValue(0)
            progress_dialog.show()
            QCoreApplication.processEvents()

            def progress_callback(processed, total):
                progress_bar.setValue(processed)
                QCoreApplication.processEvents()

            try:
                self.db_manager.export_to_csv(filename, progress_callback=progress_callback)
                QMessageBox.information(self.parent, "Success", f"Database backup saved to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self.parent, "Error", f"Failed to backup database: {e}")
            progress_dialog.accept()
            self.parent.progress_bar = None

    def restore_database(self):
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
        
        progress_dialog = QDialog(self.parent)
        progress_dialog.setWindowTitle("Importing Data")
        progress_dialog.setModal(True)
        vbox = QVBoxLayout(progress_dialog)
        label = QLabel("Importing data, please wait...")
        vbox.addWidget(label)
        progress_bar = QProgressBar(progress_dialog)
        vbox.addWidget(progress_bar)
        progress_dialog.setLayout(vbox)
        self.parent.progress_bar = progress_bar

        progress_bar.setMinimum(0)
        progress_bar.setMaximum(import_summary['total_records'])
        progress_bar.setValue(0)
        progress_dialog.show()
        QCoreApplication.processEvents()

        try:
            self.db_manager.backup_helper.import_from_csv(
                filename, 
                progress_callback=lambda processed, total: progress_bar.setValue(processed),
                resolution_mode=resolution_mode
            )
            progress_bar.setValue(import_summary['total_records'])
            QCoreApplication.processEvents()
            progress_dialog.accept()
            self.parent.progress_bar = None
            
            self._show_relaunch_dialog()
            
        except Exception as e:
            if hasattr(self.parent, "progress_bar") and self.parent.progress_bar:
                self.parent.progress_bar.setValue(0)
            QMessageBox.critical(self.parent, "Error", f"Failed to restore database: {e}")
            progress_dialog.accept()
            self.parent.progress_bar = None
    
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
    
    def _show_relaunch_dialog(self):
        """Show relaunch dialog after successful import"""
        dialog = QDialog(self.parent)
        dialog.setWindowTitle("Import Successful")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon("fa6s.circle-check", color="#4caf50").pixmap(48, 48))
        
        message_label = QLabel("<b>Database imported successfully.</b><br><br>Please relaunch the application for changes to take effect.")
        message_label.setWordWrap(True)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(icon_label)
        header_layout.addWidget(message_label, 1)
        
        layout.addLayout(header_layout)
        layout.addSpacing(10)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        relaunch_btn = QPushButton("Relaunch Now")
        relaunch_btn.setIcon(qta.icon("fa6s.rotate"))
        relaunch_btn.clicked.connect(lambda: self._relaunch_app(dialog))
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setIcon(qta.icon("fa6s.circle-xmark"))
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(relaunch_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _relaunch_app(self, dialog):
        """Save data and relaunch application"""
        try:
            self.db_manager.close()
            dialog.accept()
            from PySide6.QtWidgets import QApplication
            QApplication.quit()
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            QMessageBox.critical(self.parent, "Error", f"Failed to relaunch: {e}")
