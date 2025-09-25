from qtpy.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, 
QLabel, QPushButton, QSpinBox, QTextEdit, 
QVBoxLayout, QHBoxLayout, QWidget, QFileDialog)

def log(text_edit, message):
        """Add a message to the status log."""
        current_text = text_edit.toPlainText()
        text_edit.setPlainText(f"{current_text}\n{message}" if current_text else message)
        text_edit.verticalScrollBar().setValue(text_edit.verticalScrollBar().maximum())
        