from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                               QLabel, QDateEdit, QComboBox, QLineEdit, QFileDialog,
                               QGroupBox, QFormLayout, QSpinBox, QCheckBox, QDialog,
                               QTextEdit, QDialogButtonBox, QTableWidget, QTableWidgetItem,
                               QHeaderView, QScrollArea, QFrame)
from PySide6.QtCore import Qt, Signal, QDate, QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QFont, QPixmap, QPainter, QImage
import qtawesome as qta
import csv
import os
from datetime import datetime
import tempfile


class WalletReportFilter(QWidget):
    filter_changed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        filter_group = QGroupBox("Filters")
        filter_layout = QFormLayout()
        filter_layout.setSpacing(8)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search transaction name...")
        self.search_input.textChanged.connect(self.on_filter_changed)
        filter_layout.addRow("Search:", self.search_input)
        
        filter_row1 = QHBoxLayout()
        filter_row1.setSpacing(8)
        
        self.transaction_type = QComboBox()
        self.transaction_type.addItems(["All", "Income", "Expense", "Transfer"])
        self.transaction_type.currentTextChanged.connect(self.on_filter_changed)
        filter_row1.addWidget(self.transaction_type)
        
        self.pocket_combo = QComboBox()
        self.pocket_combo.addItem("All Pockets", None)
        self.pocket_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_row1.addWidget(self.pocket_combo)
        
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories", None)
        self.category_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_row1.addWidget(self.category_combo)
        
        self.location_combo = QComboBox()
        self.location_combo.addItem("All Locations", None)
        self.location_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_row1.addWidget(self.location_combo)
        
        filter_layout.addRow("Type/Pocket/Category/Location:", filter_row1)
        
        filter_row2 = QHBoxLayout()
        filter_row2.setSpacing(8)
        
        self.chk_use_date = QCheckBox("Enable Date Filter")
        self.chk_use_date.setChecked(False)
        self.chk_use_date.toggled.connect(self.on_date_filter_toggled)
        filter_row2.addWidget(self.chk_use_date)
        
        filter_row2.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.dateChanged.connect(self.on_filter_changed)
        filter_row2.addWidget(self.date_from)
        
        filter_row2.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(self.on_filter_changed)
        filter_row2.addWidget(self.date_to)
        
        btn_reset = QPushButton(qta.icon("fa6s.xmark"), "Reset")
        btn_reset.clicked.connect(self.reset_filters)
        filter_row2.addWidget(btn_reset)
        
        filter_row2.addStretch()
        filter_layout.addRow("Date Range:", filter_row2)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        self.setLayout(layout)
        
        self.init_date_widgets()
    
    def init_date_widgets(self):
        self.date_from.setEnabled(False)
        self.date_to.setEnabled(False)
    
    def on_date_filter_toggled(self, checked):
        self.date_from.setEnabled(checked)
        self.date_to.setEnabled(checked)
        self.on_filter_changed()
    
    def load_pockets(self, pockets):
        self.pocket_combo.clear()
        self.pocket_combo.addItem("All Pockets", None)
        for pocket in pockets:
            self.pocket_combo.addItem(pocket['name'], pocket['id'])
    
    def load_categories(self, categories):
        self.category_combo.clear()
        self.category_combo.addItem("All Categories", None)
        for category in categories:
            self.category_combo.addItem(category['name'], category['id'])
    
    def load_locations(self, locations):
        self.location_combo.clear()
        self.location_combo.addItem("All Locations", None)
        for location in locations:
            self.location_combo.addItem(location['name'], location['id'])
    
    def on_filter_changed(self):
        filters = self.get_filters()
        self.filter_changed.emit(filters)
    
    def get_filters(self):
        transaction_type_text = self.transaction_type.currentText().lower()
        if transaction_type_text == "all":
            transaction_type_text = ""
        
        date_from = ""
        date_to = ""
        if self.chk_use_date.isChecked():
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to = self.date_to.date().toString("yyyy-MM-dd")
        
        return {
            'date_from': date_from,
            'date_to': date_to,
            'transaction_type': transaction_type_text,
            'pocket_id': self.pocket_combo.currentData(),
            'category_id': self.category_combo.currentData(),
            'location_id': self.location_combo.currentData(),
            'search_text': self.search_input.text()
        }
    
    def reset_filters(self):
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_to.setDate(QDate.currentDate())
        self.chk_use_date.setChecked(False)
        self.transaction_type.setCurrentIndex(0)
        self.pocket_combo.setCurrentIndex(0)
        self.category_combo.setCurrentIndex(0)
        self.location_combo.setCurrentIndex(0)
        self.search_input.clear()


class WalletReportActions(QWidget):
    export_csv_clicked = Signal()
    export_pdf_clicked = Signal()
    refresh_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        btn_refresh = QPushButton(qta.icon("fa6s.arrows-rotate"), " Refresh")
        btn_refresh.clicked.connect(self.refresh_clicked.emit)
        layout.addWidget(btn_refresh)
        
        btn_export_csv = QPushButton(qta.icon("fa6s.file-csv"), " Export CSV")
        btn_export_csv.clicked.connect(self.export_csv_clicked.emit)
        layout.addWidget(btn_export_csv)
        
        btn_export_pdf = QPushButton(qta.icon("fa6s.file-pdf"), " Export PDF")
        btn_export_pdf.clicked.connect(self.export_pdf_clicked.emit)
        layout.addWidget(btn_export_pdf)
        
        layout.addStretch()
        
        self.setLayout(layout)


class WalletReportPagination(QWidget):
    page_changed = Signal(int)
    per_page_changed = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = 1
        self.total_pages = 1
        self.total_items = 0
        self.items_per_page = 50
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        layout.addWidget(QLabel("Items per page:"))
        
        self.combo_per_page = QComboBox()
        self.combo_per_page.addItems(["25", "50", "100", "200"])
        self.combo_per_page.setCurrentText("50")
        self.combo_per_page.currentTextChanged.connect(self.on_per_page_changed)
        layout.addWidget(self.combo_per_page)
        
        layout.addStretch()
        
        self.btn_first_page = QPushButton(qta.icon("fa6s.angles-left"), "")
        self.btn_first_page.setFixedSize(32, 32)
        self.btn_first_page.clicked.connect(self.go_to_first_page)
        layout.addWidget(self.btn_first_page)
        
        self.btn_prev_page = QPushButton(qta.icon("fa6s.chevron-left"), "")
        self.btn_prev_page.setFixedSize(32, 32)
        self.btn_prev_page.clicked.connect(self.go_to_prev_page)
        layout.addWidget(self.btn_prev_page)
        
        layout.addWidget(QLabel("Page:"))
        
        self.spin_page = QSpinBox()
        self.spin_page.setMinimum(1)
        self.spin_page.setMaximum(1)
        self.spin_page.setValue(1)
        self.spin_page.valueChanged.connect(self.on_page_value_changed)
        layout.addWidget(self.spin_page)
        
        self.lbl_page_info = QLabel("of 1")
        layout.addWidget(self.lbl_page_info)
        
        self.btn_next_page = QPushButton(qta.icon("fa6s.chevron-right"), "")
        self.btn_next_page.setFixedSize(32, 32)
        self.btn_next_page.clicked.connect(self.go_to_next_page)
        layout.addWidget(self.btn_next_page)
        
        self.btn_last_page = QPushButton(qta.icon("fa6s.angles-right"), "")
        self.btn_last_page.setFixedSize(32, 32)
        self.btn_last_page.clicked.connect(self.go_to_last_page)
        layout.addWidget(self.btn_last_page)
        
        layout.addStretch()
        
        self.label_total = QLabel("Total: 0 items")
        self.label_total.setStyleSheet("font-weight: bold; color: #666;")
        layout.addWidget(self.label_total)
        
        self.setLayout(layout)
    
    def on_per_page_changed(self, per_page_text):
        self.items_per_page = int(per_page_text)
        self.current_page = 1
        self.per_page_changed.emit(self.items_per_page)
    
    def on_page_value_changed(self, page):
        self.current_page = page
        self.page_changed.emit(page)
    
    def go_to_first_page(self):
        if self.current_page != 1:
            self.spin_page.setValue(1)
    
    def go_to_prev_page(self):
        if self.current_page > 1:
            self.spin_page.setValue(self.current_page - 1)
    
    def go_to_next_page(self):
        if self.current_page < self.total_pages:
            self.spin_page.setValue(self.current_page + 1)
    
    def go_to_last_page(self):
        if self.current_page != self.total_pages:
            self.spin_page.setValue(self.total_pages)
    
    def update_pagination(self, current_page, total_items, items_per_page):
        self.current_page = current_page
        self.total_items = total_items
        self.items_per_page = items_per_page
        self.total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        
        self.spin_page.blockSignals(True)
        self.spin_page.setMaximum(max(1, self.total_pages))
        self.spin_page.setValue(self.current_page)
        self.spin_page.blockSignals(False)
        
        self.lbl_page_info.setText(f"of {self.total_pages}")
        
        has_prev = self.current_page > 1
        has_next = self.current_page < self.total_pages
        
        self.btn_first_page.setEnabled(has_prev)
        self.btn_prev_page.setEnabled(has_prev)
        self.btn_next_page.setEnabled(has_next)
        self.btn_last_page.setEnabled(has_next)
        
        start_item = (self.current_page - 1) * self.items_per_page + 1
        end_item = min(self.current_page * self.items_per_page, self.total_items)
        
        if self.total_items > 0:
            self.label_total.setText(f"Showing {start_item}-{end_item} of {self.total_items} items")
        else:
            self.label_total.setText("No items found")


class CSVPreviewDialog(QDialog):
    """Preview dialog for CSV export before saving"""
    
    def __init__(self, data, headers, title, parent=None):
        super().__init__(parent)
        self.data = data
        self.headers = headers
        self.title = title
        self.should_save = False
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(f"CSV Preview - {self.title}")
        self.resize(900, 600)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Title
        title_label = QLabel(f"Preview: {self.title}")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Info
        info_label = QLabel(f"Document Type: CSV | Total Records: {len(self.data)}")
        info_label.setStyleSheet("color: #666;")
        layout.addWidget(info_label)
        
        # Preview table
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(len(self.headers))
        self.preview_table.setHorizontalHeaderLabels(self.headers)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Populate table
        self.preview_table.setRowCount(len(self.data))
        for row_idx, row_data in enumerate(self.data):
            for col_idx, cell_data in enumerate(row_data):
                item = QTableWidgetItem(str(cell_data))
                self.preview_table.setItem(row_idx, col_idx, item)
        
        layout.addWidget(self.preview_table, 1)
        
        # Buttons
        button_box = QHBoxLayout()
        button_box.addStretch()
        
        btn_cancel = QPushButton(qta.icon("fa6s.xmark"), " Cancel")
        btn_cancel.clicked.connect(self.reject)
        button_box.addWidget(btn_cancel)
        
        btn_save = QPushButton(qta.icon("fa6s.floppy-disk"), " Save")
        btn_save.clicked.connect(self.accept_and_save)
        btn_save.setDefault(True)
        button_box.addWidget(btn_save)
        
        layout.addLayout(button_box)
        
        self.setLayout(layout)
    
    def accept_and_save(self):
        self.should_save = True
        self.accept()


class PDFPreviewDialog(QDialog):
    """Preview dialog showing actual PDF layout before saving"""
    
    def __init__(self, pdf_path, title, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.title = title
        self.should_save = False
        self.zoom_level = 1.2  # Default zoom level 120%
        self.page_labels = []  # Store page labels for re-rendering
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(f"PDF Preview - {self.title}")
        self.resize(1000, 700)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Title
        title_label = QLabel(f"Preview: {self.title}")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Info and zoom controls
        controls_layout = QHBoxLayout()
        
        info_label = QLabel("Document Type: PDF | Preview shows the actual PDF layout")
        info_label.setStyleSheet("color: #666;")
        controls_layout.addWidget(info_label)
        
        controls_layout.addStretch()
        
        # Zoom controls
        zoom_label = QLabel("Zoom:")
        controls_layout.addWidget(zoom_label)
        
        btn_zoom_out = QPushButton(qta.icon("fa6s.magnifying-glass-minus"), "")
        btn_zoom_out.setFixedSize(32, 32)
        btn_zoom_out.clicked.connect(self.zoom_out)
        btn_zoom_out.setToolTip("Zoom Out")
        controls_layout.addWidget(btn_zoom_out)
        
        self.zoom_label_value = QLabel("100%")
        self.zoom_label_value.setMinimumWidth(50)
        self.zoom_label_value.setAlignment(Qt.AlignCenter)
        controls_layout.addWidget(self.zoom_label_value)
        
        btn_zoom_in = QPushButton(qta.icon("fa6s.magnifying-glass-plus"), "")
        btn_zoom_in.setFixedSize(32, 32)
        btn_zoom_in.clicked.connect(self.zoom_in)
        btn_zoom_in.setToolTip("Zoom In")
        controls_layout.addWidget(btn_zoom_in)
        
        btn_zoom_fit = QPushButton(qta.icon("fa6s.maximize"), "")
        btn_zoom_fit.setFixedSize(32, 32)
        btn_zoom_fit.clicked.connect(self.zoom_fit)
        btn_zoom_fit.setToolTip("Fit to Width")
        controls_layout.addWidget(btn_zoom_fit)
        
        layout.addLayout(controls_layout)
        
        # PDF Preview using PyMuPDF (fitz) if available
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.StyledPanel)
        
        self.preview_widget = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_widget)
        self.preview_layout.setSpacing(10)
        self.preview_layout.setContentsMargins(10, 10, 10, 10)
        
        self.load_pdf_preview()
        
        self.preview_layout.addStretch()
        self.scroll_area.setWidget(self.preview_widget)
        
        # Install event filter for Ctrl+Scroll zoom
        self.scroll_area.viewport().installEventFilter(self)
        
        layout.addWidget(self.scroll_area, 1)
        
        # Install event filter for Ctrl+Scroll zoom
        self.scroll_area.viewport().installEventFilter(self)
        
        # Buttons
        button_box = QHBoxLayout()
        button_box.addStretch()
        
        btn_cancel = QPushButton(qta.icon("fa6s.xmark"), " Cancel")
        btn_cancel.clicked.connect(self.reject)
        button_box.addWidget(btn_cancel)
        
        btn_save = QPushButton(qta.icon("fa6s.floppy-disk"), " Save")
        btn_save.clicked.connect(self.accept_and_save)
        btn_save.setDefault(True)
        button_box.addWidget(btn_save)
        
        layout.addLayout(button_box)
        
        self.setLayout(layout)
    
    def load_pdf_preview(self):
        """Load PDF and render pages"""
        # Clear existing pages
        for label in self.page_labels:
            label.deleteLater()
        self.page_labels.clear()
        
        try:
            import fitz  # PyMuPDF
            pdf_doc = fitz.open(self.pdf_path)
            
            # Calculate DPI based on zoom level
            base_dpi = 70  # Lower base DPI for better fit
            dpi = base_dpi * self.zoom_level
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                
                # Render page to image
                mat = fitz.Matrix(dpi/72, dpi/72)
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to QPixmap
                img_data = pix.tobytes("png")
                qimage = QImage()
                qimage.loadFromData(img_data)
                pixmap = QPixmap.fromImage(qimage)
                
                # Create label to show page
                page_label = QLabel()
                page_label.setPixmap(pixmap)
                page_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
                page_label.setStyleSheet("background-color: white; border: 1px solid #ccc; padding: 10px;")
                
                # Append pages in correct order (page 1, then page 2, etc.)
                insert_position = len(self.page_labels)
                self.preview_layout.insertWidget(insert_position, page_label)
                self.page_labels.append(page_label)
            
            pdf_doc.close()
            
        except ImportError:
            # Fallback if PyMuPDF not available
            fallback_label = QLabel("PDF Preview requires PyMuPDF library.\nInstall with: pip install pymupdf")
            fallback_label.setAlignment(Qt.AlignCenter)
            fallback_label.setStyleSheet("color: #666; font-size: 14px; padding: 40px;")
            self.preview_layout.insertWidget(0, fallback_label)
            self.page_labels.append(fallback_label)
        except Exception as e:
            error_label = QLabel(f"Error loading PDF preview:\n{str(e)}")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: #d32f2f; font-size: 12px; padding: 40px;")
            self.preview_layout.insertWidget(self.preview_layout.count() - 1, error_label)
            self.page_labels.append(error_label)
    
    def zoom_in(self):
        """Increase zoom level"""
        self.zoom_level = min(2.0, self.zoom_level + 0.1)
        self.update_zoom()
    
    def zoom_out(self):
        """Decrease zoom level"""
        self.zoom_level = max(0.3, self.zoom_level - 0.1)
        self.update_zoom()
    
    def zoom_fit(self):
        """Fit to width"""
        self.zoom_level = 0.7  # Adjusted for landscape A4
        self.update_zoom()
    
    def update_zoom(self):
        """Update zoom display and reload preview"""
        self.zoom_label_value.setText(f"{int(self.zoom_level * 100)}%")
        self.load_pdf_preview()
    
    def eventFilter(self, obj, event):
        """Handle Ctrl+Scroll for zoom in/out"""
        if obj == self.scroll_area.viewport():
            from PySide6.QtCore import QEvent
            if event.type() == QEvent.Wheel:
                if event.modifiers() & Qt.ControlModifier:
                    # Ctrl is pressed, handle zoom
                    delta = event.angleDelta().y()
                    if delta > 0:
                        self.zoom_in()
                    else:
                        self.zoom_out()
                    return True  # Event handled
        return super().eventFilter(obj, event)
    
    def accept_and_save(self):
        self.should_save = True
        self.accept()


class WalletReportExporter:
    
    @staticmethod
    def merge_currency_amount(data, headers):
        """Merge Currency and Amount columns into one.
        
        Returns tuple of (merged_data, merged_headers)
        """
        # Find indices of Amount and Currency columns
        amount_idx = -1
        currency_idx = -1
        for idx, header in enumerate(headers):
            if 'amount' in header.lower():
                amount_idx = idx
            elif 'currency' in header.lower():
                currency_idx = idx
        
        # If both columns exist, merge them
        merged_headers = list(headers)
        merged_data = []
        
        if amount_idx >= 0 and currency_idx >= 0:
            # Create new headers without Currency column
            merged_headers.pop(max(amount_idx, currency_idx))
            merged_headers.pop(min(amount_idx, currency_idx))
            merged_headers.insert(min(amount_idx, currency_idx), 'Amount')
            
            # Merge data rows
            for row in data:
                new_row = list(row)
                amount_val = row[amount_idx] if amount_idx < len(row) else ''
                currency_val = row[currency_idx] if currency_idx < len(row) else ''
                
                # Combine currency and amount
                merged_value = f"{currency_val} {amount_val}".strip()
                
                # Remove both columns and insert merged value
                new_row.pop(max(amount_idx, currency_idx))
                new_row.pop(min(amount_idx, currency_idx))
                new_row.insert(min(amount_idx, currency_idx), merged_value)
                merged_data.append(new_row)
        else:
            merged_data = data
        
        return merged_data, merged_headers
    
    @staticmethod
    def export_to_csv(data, headers, filters=None, filename=None, parent=None):
        """Export data to CSV file in user's home directory with preview"""
        from pathlib import Path
        
        # Show preview dialog
        preview = CSVPreviewDialog(data, headers, "CSV Export", parent)
        if preview.exec() != QDialog.Accepted or not preview.should_save:
            return False
        
        home_dir = Path.home()
        default_filename = f"wallet_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        if not filename:
            filename, _ = QFileDialog.getSaveFileName(
                None,
                "Save CSV File",
                str(home_dir / default_filename),
                "CSV Files (*.csv)"
            )
        
        if not filename:
            return False
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Add filter information if provided
                if filters:
                    if filters.get('date_from') and filters.get('date_to'):
                        writer.writerow([f"Date Range: {filters['date_from']} to {filters['date_to']}"])
                    if filters.get('transaction_type'):
                        writer.writerow([f"Type: {filters['transaction_type'].capitalize()}"])
                    writer.writerow([])  # Empty row separator
                
                writer.writerow(headers)
                writer.writerows(data)
            return True
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return False
    
    @staticmethod
    def export_to_pdf(data, headers, title, filters=None, filename=None, parent=None):
        """Export data to PDF file in user's home directory with detailed header and preview"""
        from pathlib import Path
        
        # Merge currency and amount columns before generating PDF
        merged_data, merged_headers = WalletReportExporter.merge_currency_amount(data, headers)
        
        # Generate PDF to temporary file first for preview
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_pdf_path = temp_pdf.name
        temp_pdf.close()
        # Generate temporary PDF for preview
        try:
            WalletReportExporter._generate_pdf_content(
                temp_pdf_path, merged_data, merged_headers, title, filters
            )
        except Exception as e:
            print(f"Error generating preview PDF: {e}")
            os.unlink(temp_pdf_path)
            return False
        
        # Show preview dialog with actual PDF
        preview = PDFPreviewDialog(temp_pdf_path, title, parent)
        preview_result = preview.exec()
        should_save = preview.should_save
        
        # Clean up temp file after preview
        if not should_save:
            os.unlink(temp_pdf_path)
            return False
        
        # User wants to save, ask for location
        home_dir = Path.home()
        default_filename = f"wallet_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        if not filename:
            filename, _ = QFileDialog.getSaveFileName(
                parent,
                "Save PDF File",
                str(home_dir / default_filename),
                "PDF Files (*.pdf)"
            )
        
        if not filename:
            os.unlink(temp_pdf_path)
            return False
        
        # Copy temp file to final location
        try:
            import shutil
            shutil.copy2(temp_pdf_path, filename)
            os.unlink(temp_pdf_path)
            return True
        except Exception as e:
            print(f"Error saving PDF: {e}")
            os.unlink(temp_pdf_path)
            return False
    
    @staticmethod
    def _generate_pdf_content(filename, data, headers, title, filters=None):
        """Generate PDF content to file"""
        from pathlib import Path
        
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
            import json
            
            # Load window config
            config_path = Path(__file__).parents[4] / "configs" / "window_config.json"
            icon_path = None
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    app_title = config.get('window', {}).get('title', 'Rak Arsip 3')
                    about_info = config.get('about', {})
                    author = about_info.get('author', 'Unknown')
                    year = about_info.get('year', datetime.now().year)
                    icon_rel_path = config.get('window', {}).get('icon', '')
                    if icon_rel_path:
                        icon_path = Path(__file__).parents[4] / icon_rel_path
                        if not icon_path.exists():
                            icon_path = None
            except:
                app_title = 'Rak Arsip 3'
                author = 'Unknown'
                year = datetime.now().year
            
            doc = SimpleDocTemplate(filename, pagesize=landscape(A4))
            elements = []
            
            styles = getSampleStyleSheet()
            
            # Orange theme color
            orange_color = colors.HexColor('#ff7125')
            
            # Title style
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=orange_color,
                spaceAfter=10,
                alignment=TA_LEFT,
                fontName='Helvetica-Bold'
            )
            
            # Subtitle style
            subtitle_style = ParagraphStyle(
                'Subtitle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#666666'),
                spaceAfter=20,
                alignment=TA_LEFT
            )
            
            # Info style
            info_style = ParagraphStyle(
                'Info',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#333333'),
                spaceAfter=5,
                alignment=TA_LEFT
            )
            
            # Header layout with logo and text
            header_table_data = []
            
            # Add logo if available
            if icon_path and icon_path.exists():
                try:
                    from PIL import Image as PILImage
                    logo = Image(str(icon_path), width=0.5*inch, height=0.5*inch)
                    
                    # Create header with logo on left and text on right
                    header_info_style = ParagraphStyle(
                        'HeaderInfo',
                        parent=subtitle_style,
                        fontSize=10,
                        textColor=colors.HexColor('#333333'),
                        alignment=TA_LEFT
                    )
                    
                    header_info = f"<b><font size=14 color='#ff7125'>{app_title}</font></b><br/><font size=9>{author} - {year}</font>"
                    header_table_data = [[logo, Paragraph(header_info, header_info_style)]]
                    
                    header_table = Table(header_table_data, colWidths=[0.6*inch, 9*inch])
                    header_table.setStyle(TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ]))
                    elements.append(header_table)
                    elements.append(Spacer(1, 0.2*inch))
                except Exception as e:
                    print(f"Could not load icon: {e}")
                    # Fallback to text only
                    elements.append(Paragraph(app_title, title_style))
                    elements.append(Paragraph(f"{author} - {year}", subtitle_style))
            else:
                # No logo, just text
                elements.append(Paragraph(app_title, title_style))
                elements.append(Paragraph(f"{author} - {year}", subtitle_style))
            
            # Report title
            elements.append(Paragraph(f"<b>{title}</b>", title_style))
            
            # Report info
            info_text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            elements.append(Paragraph(info_text, info_style))
            
            # Filter information
            if filters:
                if filters.get('date_from') and filters.get('date_to'):
                    date_info = f"<b>Period:</b> {filters['date_from']} to {filters['date_to']}"
                    elements.append(Paragraph(date_info, info_style))
                elif data:
                    # Auto-detect date range from data if available
                    dates = []
                    for row in data:
                        for cell in row:
                            if isinstance(cell, str) and '-' in cell:
                                # Check if it looks like a date
                                try:
                                    from datetime import datetime as dt
                                    dt.strptime(cell.split(' ')[0], '%Y-%m-%d')
                                    dates.append(cell.split(' ')[0])
                                except:
                                    pass
                    if dates:
                        min_date = min(dates)
                        max_date = max(dates)
                        date_info = f"<b>Transaction Period:</b> {min_date} to {max_date}"
                        elements.append(Paragraph(date_info, info_style))
                
                if filters.get('transaction_type'):
                    type_info = f"<b>Type:</b> {filters['transaction_type'].capitalize()}"
                    elements.append(Paragraph(type_info, info_style))
                
                if filters.get('pocket_name'):
                    pocket_info = f"<b>Pocket:</b> {filters['pocket_name']}"
                    elements.append(Paragraph(pocket_info, info_style))
                
                if filters.get('category_name'):
                    category_info = f"<b>Category:</b> {filters['category_name']}"
                    elements.append(Paragraph(category_info, info_style))
            
            elements.append(Spacer(1, 0.3*inch))
            
            # Table with text wrapping
            # Create paragraph style for table cells
            cell_style = ParagraphStyle(
                'CellStyle',
                parent=styles['Normal'],
                fontSize=8,
                leading=10,
                alignment=TA_LEFT
            )
            
            # Wrap text in Paragraph for automatic line breaks
            table_data = [headers]
            for row in data:
                wrapped_row = []
                for cell in row:
                    cell_text = str(cell) if cell is not None else ''
                    wrapped_row.append(Paragraph(cell_text, cell_style))
                table_data.append(wrapped_row)
            
            # Calculate available width (landscape A4 = 11.69 inches - margins)
            page_width = landscape(A4)[0]
            margin = 0.75 * inch
            available_width = page_width - (2 * margin)
            
            # Set column widths based on number of columns
            num_cols = len(headers)
            if num_cols == 9:  # Date, Name, Type, Pocket, Category, Card, Location, Amount, Status
                col_widths = [
                    0.7*inch,   # Date
                    2.2*inch,   # Name (wider for long transaction names)
                    0.6*inch,   # Type
                    0.9*inch,   # Pocket
                    0.9*inch,   # Category
                    0.7*inch,   # Card
                    0.9*inch,   # Location
                    1.0*inch,   # Amount (with currency, needs more space)
                    0.7*inch    # Status
                ]
            elif num_cols == 8:  # Without one column
                col_widths = [
                    0.7*inch,   # Date
                    2.3*inch,   # Name
                    0.6*inch,   # Type
                    0.9*inch,   # Pocket
                    0.9*inch,   # Category
                    0.7*inch,   # Card
                    0.9*inch,   # Location
                    1.0*inch    # Amount (with currency)
                ]
            else:
                # Auto-distribute widths for other column counts
                col_widths = [available_width / num_cols] * num_cols
            
            table = Table(table_data, colWidths=col_widths, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), orange_color),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff5f0')]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            
            elements.append(table)
            
            # Footer
            elements.append(Spacer(1, 0.3*inch))
            footer_text = f"Total Records: {len(data)}"
            elements.append(Paragraph(footer_text, info_style))
            
            doc.build(elements)
            
        except ImportError:
            raise ImportError("ReportLab library not installed. Install with: pip install reportlab")
        except Exception as e:
            raise Exception(f"Error generating PDF: {e}")
