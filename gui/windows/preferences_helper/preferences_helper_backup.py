from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel, QPushButton, QListWidget, 
    QAbstractItemView, QHBoxLayout, QMessageBox, QDialog, QProgressBar,
    QFileDialog, QListWidgetItem
)
from PySide6.QtCore import QCoreApplication
import qtawesome as qta
import os
import shutil
import csv
from datetime import datetime, date


class PreferencesBackupHelper:
    """Helper class for Backup/Restore tab in Preferences window"""
    
    def __init__(self, parent, db_manager):
        self.parent = parent
        self.db_manager = db_manager
        
    def create_backup_tab(self):
        """Create and return the Backup/Restore tab widget"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        backup_group = QGroupBox("Database Backup")
        backup_layout = QVBoxLayout(backup_group)
        
        backup_info = QLabel("Export all database data to CSV files for backup purposes.")
        backup_info.setWordWrap(True)
        backup_layout.addWidget(backup_info)
        
        self.parent.backup_btn = QPushButton("Export Database to CSV")
        self.parent.backup_btn.setIcon(qta.icon("fa6s.download"))
        backup_layout.addWidget(self.parent.backup_btn)

        self.parent.backup_db_btn = QPushButton("Backup Database Now")
        self.parent.backup_db_btn.setIcon(qta.icon("fa6s.database"))
        self.parent.backup_db_btn.clicked.connect(self.backup_database_now)
        backup_layout.addWidget(self.parent.backup_db_btn)

        self.parent.db_backup_list_label = QLabel("Database Backups (last 7 days):")
        backup_layout.addWidget(self.parent.db_backup_list_label)
        self.parent.db_backup_list_widget = QListWidget()
        self.parent.db_backup_list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        backup_layout.addWidget(self.parent.db_backup_list_widget)
        self.parent.db_backup_list_widget.setMinimumHeight(180)
        self.parent.db_backup_list_widget.setMaximumHeight(220)
        self.parent.db_backup_list_widget.setAlternatingRowColors(True)

        restore_group = QGroupBox("Database Restore")
        restore_layout = QVBoxLayout(restore_group)
        
        restore_info = QLabel("Import CSV files exported by this application to restore database data.")
        restore_info.setWordWrap(True)
        restore_layout.addWidget(restore_info)
        
        self.parent.restore_btn = QPushButton("Import Database from CSV")
        self.parent.restore_btn.setIcon(qta.icon("fa6s.upload"))
        restore_layout.addWidget(self.parent.restore_btn)
        
        layout.addWidget(backup_group)
        layout.addWidget(restore_group)
        layout.addStretch()
        
        # Connect signals
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
            restore_btn.setProperty("backup_path", fpath)
            restore_btn.setProperty("backup_days_old", days_old)
            restore_btn.clicked.connect(self.restore_db_backup_clicked)
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

    def restore_db_backup_clicked(self):
        """Handle restore backup button click"""
        sender = self.parent.sender()
        backup_path = sender.property("backup_path")
        backup_days_old = sender.property("backup_days_old")
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
        """Export database to CSV file"""
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

            # Count total rows for progress
            total_rows = 0
            self.db_manager.connect()
            cursor = self.db_manager.connection.cursor()
            table_queries = [
                "SELECT COUNT(*) FROM categories",
                "SELECT COUNT(*) FROM subcategories",
                "SELECT COUNT(*) FROM statuses",
                "SELECT COUNT(*) FROM templates",
                "SELECT COUNT(*) FROM files",
                "SELECT COUNT(*) FROM teams",
                "SELECT COUNT(*) FROM attendance",
                "SELECT COUNT(*) FROM item_price",
                "SELECT COUNT(*) FROM earnings",
                "SELECT COUNT(*) FROM client",
                "SELECT COUNT(*) FROM file_client_price",
                "SELECT COUNT(*) FROM batch_list",
                "SELECT COUNT(*) FROM file_client_batch"
            ]
            for query in table_queries:
                cursor.execute(query)
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
        if filename:
            reply = QMessageBox.question(
                self.parent, "Restore Database", 
                "This will add data from the backup file to the current database.\nContinue?"
            )
            if reply == QMessageBox.Yes:
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

                total_rows = 0
                with open(filename, 'r', encoding='utf-8') as csvfile:
                    for row in csv.reader(csvfile):
                        if row and row[0] != "TABLE":
                            total_rows += 1

                progress_bar.setMinimum(0)
                progress_bar.setMaximum(total_rows)
                progress_bar.setValue(0)
                progress_dialog.show()
                QCoreApplication.processEvents()

                try:
                    self.db_manager.import_from_csv(filename, progress_callback=lambda processed, total: progress_bar.setValue(processed))
                except Exception as e:
                    if hasattr(self.parent, "progress_bar") and self.parent.progress_bar:
                        self.parent.progress_bar.setValue(0)
                    QMessageBox.critical(self.parent, "Error", f"Failed to restore database: {e}")
                    progress_dialog.accept()
                    self.parent.progress_bar = None
                    return
                progress_bar.setValue(total_rows)
                QCoreApplication.processEvents()
                progress_dialog.accept()
                self.parent.progress_bar = None
                QMessageBox.information(self.parent, "Success", "Database restored successfully.")
                self.db_manager.close()
                # Refresh data after restore
                if hasattr(self.parent, 'load_data'):
                    self.parent.load_data()
