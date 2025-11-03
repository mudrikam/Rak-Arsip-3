from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                               QProgressBar, QTabWidget, QGridLayout, QScrollArea)
from PySide6.QtCore import Qt, QMargins, QPointF
from PySide6.QtGui import QFont, QPainter, QColor
from PySide6.QtCharts import (QChart, QChartView, QPieSeries, QPieSlice, 
                              QLineSeries, QValueAxis, QBarCategoryAxis)


class WalletOverviewCharts(QWidget):
    """Widget for displaying charts (bar charts and pie charts)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.currency_symbol = "Rp"
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        grid = QGridLayout()
        grid.setSpacing(8)
        
        self.trend_widget = self.create_trend_widget()
        grid.addWidget(self.trend_widget, 0, 0)
        
        self.comparison_widget = self.create_comparison_widget()
        grid.addWidget(self.comparison_widget, 0, 1)
        
        self.pie_widget = self.create_pie_widget()
        grid.addWidget(self.pie_widget, 1, 0, 1, 2)
        
        main_layout.addLayout(grid)
    
    def create_trend_widget(self):
        """Create monthly/yearly trend chart widget"""
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        title_label = QLabel("Transaction Trends")
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        self.trend_tabs = QTabWidget()
        
        self.monthly_chart_widget = QWidget()
        self.monthly_chart_layout = QVBoxLayout(self.monthly_chart_widget)
        self.monthly_chart_layout.setContentsMargins(0, 0, 0, 0)
        
        self.yearly_chart_widget = QWidget()
        self.yearly_chart_layout = QVBoxLayout(self.yearly_chart_widget)
        self.yearly_chart_layout.setContentsMargins(0, 0, 0, 0)
        
        self.trend_tabs.addTab(self.monthly_chart_widget, "Monthly")
        self.trend_tabs.addTab(self.yearly_chart_widget, "Yearly")
        
        layout.addWidget(self.trend_tabs)
        
        return frame
    
    def create_comparison_widget(self):
        """Create month-to-month comparison widget"""
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        title_label = QLabel("This Month vs Last Month")
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        self.comparison_layout = QVBoxLayout()
        self.comparison_layout.setSpacing(6)
        layout.addLayout(self.comparison_layout)
        
        layout.addStretch()
        
        return frame
    
    def create_pie_widget(self):
        """Create pie chart widget with tabs"""
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        title_label = QLabel("Distribution Analysis")
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        self.pie_tabs = QTabWidget()
        
        self.category_pie = QWidget()
        self.category_pie_layout = QVBoxLayout(self.category_pie)
        self.category_pie_layout.setContentsMargins(0, 0, 0, 0)
        
        self.pocket_pie = QWidget()
        self.pocket_pie_layout = QVBoxLayout(self.pocket_pie)
        self.pocket_pie_layout.setContentsMargins(0, 0, 0, 0)
        
        self.location_pie = QWidget()
        self.location_pie_layout = QVBoxLayout(self.location_pie)
        self.location_pie_layout.setContentsMargins(0, 0, 0, 0)
        
        self.pie_tabs.addTab(self.category_pie, "Categories")
        self.pie_tabs.addTab(self.pocket_pie, "Pockets")
        self.pie_tabs.addTab(self.location_pie, "Locations")
        
        layout.addWidget(self.pie_tabs)
        
        return frame
    
    def update_trend_data(self, monthly_data, yearly_data, currency_symbol="Rp"):
        """Update trend charts with monthly and yearly data"""
        self.currency_symbol = currency_symbol
        
        while self.monthly_chart_layout.count():
            item = self.monthly_chart_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not monthly_data:
            no_data = QLabel("No data available")
            no_data.setStyleSheet("color: #6c757d; font-style: italic;")
            no_data.setAlignment(Qt.AlignCenter)
            self.monthly_chart_layout.addWidget(no_data)
        else:
            months_dict = {}
            for item in monthly_data:
                month = item.get('month', '')
                trans_type = item.get('transaction_type', '')
                total = item.get('total', 0)
                
                if month not in months_dict:
                    months_dict[month] = {'income': 0, 'expense': 0, 'transfer': 0}
                
                if trans_type in ['income', 'expense', 'transfer']:
                    months_dict[month][trans_type] = total
            
            sorted_months = sorted(months_dict.items())[-12:]
            monthly_chart = self.create_line_chart(sorted_months, "Monthly Trends")
            self.monthly_chart_layout.addWidget(monthly_chart)
        
        while self.yearly_chart_layout.count():
            item = self.yearly_chart_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not yearly_data:
            no_data = QLabel("No data available")
            no_data.setStyleSheet("color: #6c757d; font-style: italic;")
            no_data.setAlignment(Qt.AlignCenter)
            self.yearly_chart_layout.addWidget(no_data)
        else:
            years_dict = {}
            for item in yearly_data:
                year = item.get('year', '')
                trans_type = item.get('transaction_type', '')
                total = item.get('total', 0)
                
                if year not in years_dict:
                    years_dict[year] = {'income': 0, 'expense': 0, 'transfer': 0}
                
                if trans_type in ['income', 'expense', 'transfer']:
                    years_dict[year][trans_type] = total
            
            sorted_years = sorted(years_dict.items())[-3:]
            yearly_chart = self.create_line_chart(sorted_years, "Yearly Trends")
            self.yearly_chart_layout.addWidget(yearly_chart)
    
    def create_line_chart(self, data_items, title):
        """Create a line chart for trends"""
        income_series = QLineSeries()
        income_series.setName("Income")
        income_series.setColor(QColor("#28a745"))
        
        pen_income = income_series.pen()
        pen_income.setWidth(3)
        income_series.setPen(pen_income)
        
        expense_series = QLineSeries()
        expense_series.setName("Expense")
        expense_series.setColor(QColor("#dc3545"))
        
        pen_expense = expense_series.pen()
        pen_expense.setWidth(3)
        expense_series.setPen(pen_expense)
        
        transfer_series = QLineSeries()
        transfer_series.setName("Transfer")
        transfer_series.setColor(QColor("#17a2b8"))
        
        pen_transfer = transfer_series.pen()
        pen_transfer.setWidth(3)
        transfer_series.setPen(pen_transfer)
        
        categories = []
        max_value = 0
        
        for idx, (period, data) in enumerate(data_items):
            income = data.get('income', 0)
            expense = data.get('expense', 0)
            transfer = data.get('transfer', 0)
            
            income_series.append(QPointF(idx, income))
            expense_series.append(QPointF(idx, expense))
            transfer_series.append(QPointF(idx, transfer))
            
            categories.append(str(period))
            max_value = max(max_value, income, expense, transfer)
        
        chart = QChart()
        chart.addSeries(income_series)
        chart.addSeries(expense_series)
        chart.addSeries(transfer_series)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.setBackgroundVisible(False)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_x.setLabelsAngle(-45)
        axis_x.setGridLineVisible(True)
        axis_x.setGridLineColor(QColor(128, 128, 128, 13))
        chart.addAxis(axis_x, Qt.AlignBottom)
        income_series.attachAxis(axis_x)
        expense_series.attachAxis(axis_x)
        transfer_series.attachAxis(axis_x)
        
        axis_y = QValueAxis()
        axis_y.setLabelFormat("%i")
        axis_y.setRange(0, max_value * 1.1 if max_value > 0 else 100)
        axis_y.setGridLineVisible(True)
        axis_y.setGridLineColor(QColor(128, 128, 128, 13))
        chart.addAxis(axis_y, Qt.AlignLeft)
        income_series.attachAxis(axis_y)
        expense_series.attachAxis(axis_y)
        transfer_series.attachAxis(axis_y)
        
        chart.setMargins(QMargins(0, 0, 0, 0))
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setMinimumHeight(250)
        
        return chart_view
    
    def update_comparison_data(self, this_month, last_month, currency_symbol="Rp"):
        """Update month-to-month comparison"""
        self.currency_symbol = currency_symbol
        
        while self.comparison_layout.count():
            item = self.comparison_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        items = [
            ('Income', this_month.get('income', 0), last_month.get('income', 0), '#28a745'),
            ('Expense', this_month.get('expense', 0), last_month.get('expense', 0), '#dc3545'),
            ('Transfer', this_month.get('transfer', 0), last_month.get('transfer', 0), '#17a2b8'),
        ]
        
        for label, current, previous, color in items:
            item_widget = self.create_comparison_item(label, current, previous, color)
            self.comparison_layout.addWidget(item_widget)
    
    def create_comparison_item(self, label, current, previous, color):
        """Create a comparison item"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()

        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"font-weight: bold; font-size: 15px; color: {color};")
        header_layout.addWidget(label_widget)

        header_layout.addStretch()

        # Arrow icon
        arrow_label = QLabel()
        arrow_label.setFixedWidth(18)
        if previous > 0:
            change = ((current - previous) / previous) * 100
            change_text = f"{change:+.1f}%"
            change_color = "#28a745" if change >= 0 else "#dc3545"
            if change > 0:
                arrow_label.setText("▲")
                arrow_label.setStyleSheet("color: #28a745; font-size: 15px; font-weight: bold;")
            else:
                arrow_label.setText("▼")
                arrow_label.setStyleSheet("color: #dc3545; font-size: 15px; font-weight: bold;")
        else:
            change_text = "New"
            change_color = "#6c757d"
            arrow_label.setText("")
        header_layout.addWidget(arrow_label)

        change_label = QLabel(change_text)
        change_label.setStyleSheet(f"font-size: 15px; color: {change_color}; font-weight: bold;")
        header_layout.addWidget(change_label)

        layout.addLayout(header_layout)

        values_layout = QHBoxLayout()

        current_label = QLabel(f"{self.currency_symbol} {current:,.0f}")
        current_label.setStyleSheet("font-size: 13px;")
        values_layout.addWidget(current_label)

        values_layout.addStretch()

        previous_label = QLabel(f"(prev: {self.currency_symbol} {previous:,.0f})")
        previous_label.setStyleSheet("font-size: 12px; color: #6c757d;")
        values_layout.addWidget(previous_label)

        layout.addLayout(values_layout)

        return widget
    
    def update_pie_charts(self, categories, pockets, locations, currency_symbol="Rp"):
        """Update all pie charts"""
        self.currency_symbol = currency_symbol
        
        self.update_category_pie(categories)
        self.update_pocket_pie(pockets)
        self.update_location_pie(locations)
    
    def update_category_pie(self, data):
        """Update category pie chart"""
        while self.category_pie_layout.count():
            item = self.category_pie_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not data:
            no_data = QLabel("No data available")
            no_data.setStyleSheet("color: #6c757d; font-style: italic;")
            self.category_pie_layout.addWidget(no_data)
            return
        
        chart_widget = self.create_pie_chart(data, 'category_name')
        self.category_pie_layout.addWidget(chart_widget)
    
    def update_pocket_pie(self, data):
        """Update pocket pie chart"""
        while self.pocket_pie_layout.count():
            item = self.pocket_pie_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not data:
            no_data = QLabel("No data available")
            no_data.setStyleSheet("color: #6c757d; font-style: italic;")
            self.pocket_pie_layout.addWidget(no_data)
            return
        
        chart_widget = self.create_pie_chart(data, 'name')
        self.pocket_pie_layout.addWidget(chart_widget)
    
    def update_location_pie(self, data):
        """Update location pie chart"""
        while self.location_pie_layout.count():
            item = self.location_pie_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not data:
            no_data = QLabel("No data available")
            no_data.setStyleSheet("color: #6c757d; font-style: italic;")
            self.location_pie_layout.addWidget(no_data)
            return
        
        chart_widget = self.create_pie_chart(data, 'location_name')
        self.location_pie_layout.addWidget(chart_widget)
    
    def create_pie_chart(self, data, name_key):
        """Create a pie chart with legend"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        series = QPieSeries()
        series.setHoleSize(0.0)
        
        colors = ['#28a745', '#dc3545', '#17a2b8', '#ffc107', '#6f42c1', '#fd7e14', '#20c997', '#e83e8c']
        slices = []
        
        for idx, item in enumerate(data[:8]):
            name = item.get(name_key, 'Unknown') or 'Uncategorized'
            value = item.get('total', 0) or item.get('total_amount', 0) or item.get('balance', 0)
            
            slice = series.append(name, value)
            slice.setColor(QColor(colors[idx % len(colors)]))
            slice.setLabelVisible(False)
            slices.append(slice)
        
        # Connect hover signals for slices
        for slice in slices:
            slice.hovered.connect(lambda state, s=slice: self.on_slice_hover(s, state, slices))
        
        chart = QChart()
        chart.addSeries(series)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setVisible(False)
        chart.setBackgroundVisible(False)
        chart.setMargins(QMargins(0, 0, 0, 0))
        
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setMinimumHeight(300)
        chart_view.setMinimumWidth(300)
        
        layout.addWidget(chart_view, 2)
        
        # Legend with scroll area
        legend_scroll = QScrollArea()
        legend_scroll.setWidgetResizable(True)
        legend_scroll.setFrameShape(QFrame.NoFrame)
        legend_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        legend_widget = QWidget()
        legend_layout = QVBoxLayout(legend_widget)
        legend_layout.setSpacing(6)
        legend_layout.setContentsMargins(12, 12, 12, 12)
        
        total = sum(item.get('total', 0) or item.get('total_amount', 0) or item.get('balance', 0) for item in data[:8])
        
        legend_items = []
        
        for idx, item in enumerate(data[:8]):
            name = item.get(name_key, 'Unknown') or 'Uncategorized'
            value = item.get('total', 0) or item.get('total_amount', 0) or item.get('balance', 0)
            percentage = (value / total * 100) if total > 0 else 0
            
            item_widget = QWidget()
            item_widget.setObjectName(f"legend_item_{idx}")
            item_widget.setCursor(Qt.PointingHandCursor)
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(4, 4, 4, 4)
            
            color_box = QLabel()
            color_box.setFixedSize(16, 16)
            color_box.setStyleSheet(f"background-color: {colors[idx % len(colors)]}; border-radius: 3px;")
            color_box.setObjectName(f"color_box_{idx}")
            item_layout.addWidget(color_box)
            
            name_label = QLabel(name[:25])
            name_label.setStyleSheet("font-size: 10px;")
            name_label.setObjectName(f"name_label_{idx}")
            item_layout.addWidget(name_label)
            
            item_layout.addStretch()
            
            amount_label = QLabel(f"{self.currency_symbol} {value:,.0f}")
            amount_label.setStyleSheet("font-size: 10px; font-weight: bold;")
            amount_label.setObjectName(f"amount_label_{idx}")
            item_layout.addWidget(amount_label)
            
            percentage_label = QLabel(f"({percentage:.1f}%)")
            percentage_label.setStyleSheet("font-size: 9px; color: #6c757d;")
            percentage_label.setObjectName(f"percentage_label_{idx}")
            item_layout.addWidget(percentage_label)
            
            # Store references for hover effects
            item_widget.setProperty("slice", slices[idx])
            item_widget.setProperty("all_slices", slices)
            item_widget.setProperty("index", idx)
            item_widget.setProperty("color", colors[idx % len(colors)])
            item_widget.installEventFilter(self)
            
            legend_items.append(item_widget)
            legend_layout.addWidget(item_widget)
        
        # Store legend items for slice hover effect
        for idx, slice in enumerate(slices):
            slice.setProperty("legend_item", legend_items[idx])
            slice.setProperty("index", idx)
        
        legend_layout.addStretch()
        legend_scroll.setWidget(legend_widget)
        
        layout.addWidget(legend_scroll, 3)
        
        return widget
    
    def on_slice_hover(self, hovered_slice, state, all_slices):
        """Handle pie slice hover"""
        if state:
            # Highlight hovered slice
            for slice in all_slices:
                if slice == hovered_slice:
                    slice.setExploded(True)
                    slice.setExplodeDistanceFactor(0.1)
                    # Highlight legend
                    legend_item = slice.property("legend_item")
                    if legend_item:
                        legend_item.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 4px;")
                else:
                    slice.setExploded(False)
                    original_color = slice.color()
                    gray_color = QColor(200, 200, 200, 100)
                    slice.setColor(gray_color)
                    # Gray out legend
                    legend_item = slice.property("legend_item")
                    if legend_item:
                        legend_item.setStyleSheet("opacity: 0.3;")
        else:
            # Reset all slices
            for slice in all_slices:
                slice.setExploded(False)
                idx = slice.property("index")
                colors = ['#28a745', '#dc3545', '#17a2b8', '#ffc107', '#6f42c1', '#fd7e14', '#20c997', '#e83e8c']
                slice.setColor(QColor(colors[idx % len(colors)]))
                # Reset legend
                legend_item = slice.property("legend_item")
                if legend_item:
                    legend_item.setStyleSheet("")
    
    def eventFilter(self, obj, event):
        """Handle legend item hover"""
        if event.type() == event.Type.Enter:
            slice = obj.property("slice")
            all_slices = obj.property("all_slices")
            if slice and all_slices:
                # Highlight this slice
                for s in all_slices:
                    if s == slice:
                        s.setExploded(True)
                        s.setExplodeDistanceFactor(0.1)
                        obj.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); border-radius: 4px;")
                    else:
                        s.setExploded(False)
                        gray_color = QColor(200, 200, 200, 100)
                        s.setColor(gray_color)
                        # Gray out other legends
                        legend_item = s.property("legend_item")
                        if legend_item and legend_item != obj:
                            legend_item.setStyleSheet("opacity: 0.3;")
        
        elif event.type() == event.Type.Leave:
            all_slices = obj.property("all_slices")
            if all_slices:
                colors = ['#28a745', '#dc3545', '#17a2b8', '#ffc107', '#6f42c1', '#fd7e14', '#20c997', '#e83e8c']
                # Reset all slices
                for s in all_slices:
                    s.setExploded(False)
                    idx = s.property("index")
                    s.setColor(QColor(colors[idx % len(colors)]))
                    # Reset all legends
                    legend_item = s.property("legend_item")
                    if legend_item:
                        legend_item.setStyleSheet("")
                obj.setStyleSheet("")
        
        return super().eventFilter(obj, event)
