from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QLineEdit,
)

from presets.manager import list_presets, load_preset, save_preset


class PresetManagerDialog(QDialog):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle("Photo Presets")
        self.resize(500, 400)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Preset name")

        self.preset_list = QListWidget()
        self.preset_list.itemDoubleClicked.connect(self.apply_selected)

        self.save_button = QPushButton("Save current adjustments")
        self.apply_button = QPushButton("Apply selected")
        self.delete_button = QPushButton("Delete selected")
        self.close_button = QPushButton("Close")

        self.save_button.clicked.connect(self.save_current)
        self.apply_button.clicked.connect(self.apply_selected)
        self.delete_button.clicked.connect(self.delete_selected)
        self.close_button.clicked.connect(self.close)

        row = QHBoxLayout()
        row.addWidget(self.name_edit)
        row.addWidget(self.save_button)

        buttons = QHBoxLayout()
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.delete_button)
        buttons.addStretch()
        buttons.addWidget(self.close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Saved presets"))
        layout.addWidget(self.preset_list)
        layout.addLayout(row)
        layout.addLayout(buttons)

        self.refresh_list()

    def refresh_list(self):
        self.preset_list.clear()
        for preset_path in list_presets():
            item = QListWidgetItem(preset_path.stem)
            item.setData(0, str(preset_path))
            self.preset_list.addItem(item)

    def current_path(self):
        item = self.preset_list.currentItem()
        if item is None:
            return None
        return Path(item.data(0))

    def save_current(self):
        if not self.window.document.has_image():
            QMessageBox.information(self, "Save Preset", "Open an image first.")
            return

        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Save Preset", "Give the preset a name first.")
            return

        try:
            path = save_preset(self.window.document.adjustments, name)
            self.name_edit.clear()
            self.refresh_list()
            self.preset_list.setCurrentRow(self.preset_list.count() - 1)
            self.window.status_label.setText(f"Preset saved: {path.name}")
        except Exception as exc:  # pragma: no cover - UI validation path
            QMessageBox.critical(self, "Save Preset", str(exc))

    def apply_selected(self, *args):
        path = self.current_path()
        if path is None:
            QMessageBox.information(self, "Apply Preset", "Select a preset first.")
            return

        try:
            self.window.document.adjustments = load_preset(path)
            self.window.document.push_history()
            self.window.refresh_view()
            self.window.status_label.setText(f"Preset applied: {path.stem}")
        except Exception as exc:
            QMessageBox.critical(self, "Apply Preset", str(exc))

    def delete_selected(self):
        path = self.current_path()
        if path is None:
            QMessageBox.information(self, "Delete Preset", "Select a preset first.")
            return

        try:
            path.unlink()
            self.refresh_list()
            self.window.status_label.setText(f"Preset deleted: {path.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Delete Preset", str(exc))
