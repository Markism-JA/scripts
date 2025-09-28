#!/usr/bin/env python3

import sys
import os
import subprocess
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QTableView,
    QHeaderView,
    QAbstractItemView,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QSplitter,
    QTextEdit,
)
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QKeyEvent, QKeySequence, QColor, QFont, QShortcut

from check_tasks import get_all_tasks_with_details
from typing import Any

OPEN_HELPER_SCRIPT = Path(__file__).parent / "open_task_helper.sh"


def load_stylesheet(filename: str) -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    css_path = os.path.join(base_dir, filename)

    with open(css_path, "r") as f:
        return f.read()


class NumericSortProxyModel(QSortFilterProxyModel):
    def lessThan(self, left, right):
        if left.column() == 1 and right.column() == 1:
            try:
                left_data = int(self.sourceModel().data(left))
                right_data = int(self.sourceModel().data(right))
                return left_data < right_data
            except (ValueError, TypeError):
                pass
        return super().lessThan(left, right)


class TaskTableModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data
        self.column_map = [
            ("#", "row_number"),
            ("PRI", "priority"),
            ("Difficulty", "difficulty"),
            ("Due Date", "due_date"),
            ("Subject", "subject"),
            ("Task Name", "name"),
        ]

    def rowCount(self, parent: Any = QModelIndex()):
        return len(self._data)

    def columnCount(self, parent: Any = QModelIndex()):
        return len(self.column_map)

    def data(self, index, role: Any = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._data):
            return None
        task = self._data[index.row()]
        _, key = self.column_map[index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            if key == "row_number":
                return str(index.row() + 1)
            return str(task.get(key, ""))

        elif role == Qt.ItemDataRole.BackgroundRole:
            priority = task.get("priority", 0)
            if priority >= 10:  # Urgent
                return QColor("#422121")  # Dark, subtle red
            elif priority >= 6:  # High priority
                return QColor("#423B21")  # Dark, subtle amber

        elif role == Qt.ItemDataRole.FontRole:
            priority = task.get("priority", 0)
            if priority >= 10:
                font = QFont()
                font.setBold(True)
                return font
        return None

    def headerData(self, section, orientation, role: Any = Qt.ItemDataRole.DisplayRole):
        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            return self.column_map[section][0]
        return None


class TaskDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Dashboard")
        self.resize(1200, 700)
        self.setStyleSheet(load_stylesheet("MATERIAL.css"))

        try:
            self.tasks_data = get_all_tasks_with_details()
        except Exception as e:
            self.tasks_data = []
            print(f"Error loading tasks: {e}")

        self.setup_ui()
        self.setup_model_and_connections()
        self.setup_shortcuts()
        self.update_stats()

        if self.proxy_model.rowCount() > 0:
            self.table.setFocus()
            self.table.selectRow(0)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        header_layout = QHBoxLayout()
        self.filter_le = QLineEdit()
        self.filter_le.setPlaceholderText(
            "Filter tasks (Press '/' to focus, Esc to return to table)"
        )
        self.stats_label = QLabel()
        header_layout.addWidget(self.filter_le)
        header_layout.addWidget(self.stats_label)
        main_layout.addLayout(header_layout)

        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableView()
        self.table.setAlternatingRowColors(True)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.splitter.addWidget(self.table)
        self.splitter.addWidget(self.preview)
        self.splitter.setSizes([500, 200])  # Initial sizes are maintained

        # --- UI IMPROVEMENT: Removed the fixed/disabled splitter handle for responsiveness ---
        # The splitter is now user-resizable by default.

        main_layout.addWidget(self.splitter)
        button_layout = QHBoxLayout()
        self.open_btn = QPushButton("Open Task (Enter)")
        self.quit_btn = QPushButton("Quit (Esc)")
        button_layout.addWidget(self.open_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.quit_btn)
        main_layout.addLayout(button_layout)

    def setup_model_and_connections(self):
        self.model = TaskTableModel(self.tasks_data)
        self.proxy_model = NumericSortProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)
        self.table.setModel(self.proxy_model)

        self.table.sortByColumn(1, Qt.SortOrder.DescendingOrder)
        self.table.setSortingEnabled(False)  # Sorting is now locked.

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.filter_le.textChanged.connect(self.filter_changed)
        self.table.doubleClicked.connect(self.open_selected_task)
        self.table.selectionModel().selectionChanged.connect(self.update_preview)
        self.open_btn.clicked.connect(self.open_selected_task)
        self.quit_btn.clicked.connect(self.close)

    def setup_shortcuts(self):
        QShortcut(QKeySequence("/"), self, self.focus_search)

    def filter_changed(self, text):
        self.proxy_model.setFilterRegularExpression(text)
        self.update_stats()
        if self.proxy_model.rowCount() > 0:
            self.table.selectRow(0)

    def update_stats(self):
        self.stats_label.setText(
            f"Tasks: {self.proxy_model.rowCount()} of {len(self.tasks_data)}"
        )

    def update_preview(self):
        indices = self.table.selectionModel().selectedRows()
        if not indices:
            self.preview.clear()
            return

        source_index = self.proxy_model.mapToSource(indices[0])
        task = self.tasks_data[source_index.row()]
        path = Path(task.get("full_path", ""))

        header_html = f"""
        <h2 style="margin-top: 2px; margin-bottom: 8px;">{task.get("name", "Untitled Task")}</h2>
        <p><b>Priority:</b> {task.get("priority")} | <b>Difficulty:</b> {task.get("difficulty")} | <b>Subject:</b> {task.get("subject")}</p>
        <p><b>Due Date:</b> {task.get("due_date", "N/A")}</p>
        <p><b>Path:</b> {task.get("full_path", "N/A")}</p>
        <hr>
        """
        self.preview.setHtml(header_html)

        text_extensions = [".md", ".txt", ".py", ".sh", "conf", ".json", ".yaml"]
        if path.is_file() and path.suffix.lower() in text_extensions:
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                self.preview.append("\n--- CONTENT PREVIEW ---\n\n" + content)
            except Exception as e:
                self.preview.append(
                    f"\n--- ERROR ---\nCould not read file content: {e}"
                )
        else:
            self.preview.append(
                "\n<i>(Binary file or directory - no preview available)</i>"
            )

    def open_selected_task(self):
        indices = self.table.selectionModel().selectedRows()
        if indices:
            self.open_task_at_index(indices[0])

    def open_task_at_index(self, index):
        if not index.isValid():
            return
        source_index = self.proxy_model.mapToSource(index)
        task = self.tasks_data[source_index.row()]
        path = task.get("full_path")
        if not path:
            return

        print(f"Launching detached helper to open: {path}")
        try:
            subprocess.Popen([str(OPEN_HELPER_SCRIPT), path])
            app = QApplication.instance()
            if app is not None:
                app.quit()
        except FileNotFoundError:
            self.preview.append(
                f"\n\n--- FATAL ERROR ---\nHelper script not found at:\n{OPEN_HELPER_SCRIPT}\nPlease ensure it exists and is executable."
            )
        except Exception as e:
            print(f"Error launching helper script: {e}")

    def focus_search(self):
        self.filter_le.setFocus()
        self.filter_le.selectAll()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if self.table.hasFocus():
            if key == Qt.Key.Key_J:
                self.table.selectRow(
                    min(
                        self.table.currentIndex().row() + 1,
                        self.proxy_model.rowCount() - 1,
                    )
                )
            elif key == Qt.Key.Key_K:
                self.table.selectRow(max(self.table.currentIndex().row() - 1, 0))
            elif key == Qt.Key.Key_G:
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.table.selectRow(self.proxy_model.rowCount() - 1)
                else:
                    self.table.selectRow(0)
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.open_selected_task()
            elif key == Qt.Key.Key_Escape:
                self.close()
            else:
                super().keyPressEvent(event)
        elif self.filter_le.hasFocus():
            if key == Qt.Key.Key_Escape:
                self.table.setFocus()
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.open_selected_task()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TaskDashboard()
    window.show()
    sys.exit(app.exec())
