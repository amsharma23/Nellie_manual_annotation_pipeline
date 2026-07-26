#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dock widget + key bindings for the standalone Dynamic-Event Annotation tool.

UI: two Browse buttons (raw 4D stack, skeleton 4D stack), resolution spinboxes,
a View button, and a status log. Navigation uses napari's built-in T-slider;
the annotation key bindings read the current timepoint from viewer.dims.
"""
import os

from qtpy.QtWidgets import (
    QDoubleSpinBox, QFormLayout, QGroupBox, QLabel, QPushButton,
    QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QFileDialog,
)

from app_state import app_state
from loader import load_two_file_4d, load_dynamics_events_layer_4d
from manual_event_correction import (
    delete_selected_event, show_event_info, add_event_at_skeleton_point,
)

_TIFF_FILTER = "OME-TIFF (*.ome.tif *.ome.tiff);;TIFF (*.tif *.tiff);;All files (*)"


class AnnotationWidget(QWidget):
    """Side-panel widget for loading a 4D stack + skeleton and annotating events."""

    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self._key_bindings_setup = False
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("Dynamic Event Annotation")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # --- File selection ---
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout()
        file_group.setLayout(file_layout)

        raw_row = QHBoxLayout()
        self.raw_label = QLabel("No raw stack selected")
        raw_row.addWidget(self.raw_label)
        raw_btn = QPushButton("Browse Raw 4D...")
        raw_btn.clicked.connect(self.on_browse_raw)
        raw_row.addWidget(raw_btn)
        file_layout.addLayout(raw_row)

        skel_row = QHBoxLayout()
        self.skel_label = QLabel("No skeleton stack selected")
        skel_row.addWidget(self.skel_label)
        skel_btn = QPushButton("Browse Skeleton 4D...")
        skel_btn.clicked.connect(self.on_browse_skel)
        skel_row.addWidget(skel_btn)
        file_layout.addLayout(skel_row)

        layout.addWidget(file_group)

        # --- Resolution settings ---
        res_group = QGroupBox("Resolution Settings (µm)")
        res_layout = QFormLayout()
        res_group.setLayout(res_layout)

        self.z_res_spin = self._make_res_spin(app_state.z_resolution)
        res_layout.addRow("Z Resolution:", self.z_res_spin)
        self.y_res_spin = self._make_res_spin(app_state.y_resolution)
        res_layout.addRow("Y Resolution:", self.y_res_spin)
        self.x_res_spin = self._make_res_spin(app_state.x_resolution)
        res_layout.addRow("X Resolution:", self.x_res_spin)
        layout.addWidget(res_group)

        # --- View ---
        self.view_btn = QPushButton("Load / View")
        self.view_btn.clicked.connect(self.on_view)
        self.view_btn.setEnabled(False)
        layout.addWidget(self.view_btn)

        # --- Keybinding reference ---
        help_group = QGroupBox("Annotation Keys")
        help_layout = QVBoxLayout()
        help_group.setLayout(help_layout)
        help_text = QLabel(
            "Select a Skeleton point, then:\n"
            "  Ctrl+1  Tip-Edge Fusion\n"
            "  Ctrl+2  Junction Breakage\n"
            "  Ctrl+3  Tip-Tip Fusion\n"
            "  Ctrl+4  Tip-Tip Fission\n"
            "  Ctrl+5  Extrusion\n"
            "  Ctrl+6  Retraction\n"
            "Select a Dynamic Event, then:\n"
            "  d        Delete event\n"
            "  Ctrl+i   Event info"
        )
        help_layout.addWidget(help_text)
        layout.addWidget(help_group)

        # --- Status ---
        layout.addWidget(QLabel("Status:"))
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMinimumHeight(150)
        layout.addWidget(self.status_text)

    def _make_res_spin(self, value):
        spin = QDoubleSpinBox()
        spin.setRange(0.001, 10.0)
        spin.setDecimals(3)
        spin.setValue(value)
        spin.valueChanged.connect(self.on_resolution_changed)
        return spin

    # ----- logging -----
    def log_status(self, message):
        current = self.status_text.toPlainText()
        self.status_text.setPlainText(f"{current}\n{message}" if current else message)
        self.status_text.verticalScrollBar().setValue(
            self.status_text.verticalScrollBar().maximum()
        )

    # ----- handlers -----
    def on_resolution_changed(self):
        app_state.z_resolution = self.z_res_spin.value()
        app_state.y_resolution = self.y_res_spin.value()
        app_state.x_resolution = self.x_res_spin.value()

    def on_browse_raw(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Raw 4D Stack", "", _TIFF_FILTER)
        if path:
            app_state.raw_path = path
            self.raw_label.setText(os.path.basename(path))
            self.log_status(f"Raw stack: {path}")
            self._update_view_enabled()

    def on_browse_skel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Skeleton 4D Stack", "", _TIFF_FILTER)
        if path:
            app_state.skel_path = path
            self.skel_label.setText(os.path.basename(path))
            self.log_status(f"Skeleton stack: {path}")
            self._update_view_enabled()

    def _update_view_enabled(self):
        self.view_btn.setEnabled(bool(app_state.raw_path and app_state.skel_path))

    def _annotation_folder(self):
        """Per-dataset subfolder for event CSVs, next to the raw stack."""
        raw_dir = os.path.dirname(app_state.raw_path)
        stem = os.path.basename(app_state.raw_path)
        for ext in ('.ome.tif', '.ome.tiff', '.tif', '.tiff'):
            if stem.lower().endswith(ext):
                stem = stem[: -len(ext)]
                break
        folder = os.path.join(raw_dir, f"{stem}_annotations")
        os.makedirs(folder, exist_ok=True)
        return folder

    def on_view(self):
        try:
            data = load_two_file_4d(app_state.raw_path, app_state.skel_path)
            if data is None:
                self.log_status("Failed to load stacks (see error notification).")
                return

            app_state.num_t = data['num_t']
            app_state.is_timeseries_4d = True
            app_state.loaded_folder = self._annotation_folder()
            self.log_status(f"Event annotations save to: {app_state.loaded_folder}")

            self.viewer.layers.clear()
            scale_4d = [1] + list(app_state.visualization_scale)

            app_state.raw_layer = self.viewer.add_image(
                data['raw_4d'], scale=scale_4d, name='Raw Image',
            )
            if len(data['skel_points']) > 0:
                app_state.skeleton_layer = self.viewer.add_points(
                    data['skel_points'],
                    size=3,
                    face_color=data['face_colors'],
                    scale=scale_4d,
                    name='Skeleton',
                )

            # Render any pre-existing event CSVs.
            load_dynamics_events_layer_4d(self.viewer)

            try:
                self.viewer.dims.set_current_step(0, 0)
            except Exception:
                pass

            if not self._key_bindings_setup:
                setup_key_bindings(self, self.viewer)
                self._key_bindings_setup = True

            self.log_status(
                f"Loaded 4D stack {data['raw_4d'].shape} ({app_state.num_t} timepoints). "
                "Use the bottom T-slider to navigate frames."
            )
        except Exception as e:
            self.log_status(f"Error viewing results: {e}")


def _current_timepoint(viewer):
    """1-indexed current timepoint from napari's T axis."""
    try:
        return int(viewer.dims.current_step[0]) + 1
    except Exception:
        return 1


def setup_key_bindings(widget, viewer):
    """Bind the dynamic-event annotation keys."""

    @viewer.bind_key('d')
    def delete_event(viewer):
        """Delete selected dynamic event (key: 'd')."""
        delete_selected_event(viewer, widget)

    @viewer.bind_key('Control-i')
    def event_info(viewer):
        """Show info about the selected event (key: 'Ctrl+i')."""
        show_event_info(viewer, widget)

    # Ctrl+digit avoids napari's bare-digit Points-layer modes (1-5) and its
    # rule that Shift is consumed with non-letter keys.
    _adders = {
        'Control-1': 'tip_edge_fusion',
        'Control-2': 'junction_breakage',
        'Control-3': 'tip_tip_fusion',
        'Control-4': 'tip_tip_fission',
        'Control-5': 'extrusion',
        'Control-6': 'retraction',
    }

    def _make_adder(event_type_key):
        def _adder(viewer):
            add_event_at_skeleton_point(
                viewer, widget, event_type_key, _current_timepoint(viewer)
            )
        return _adder

    for key, event_type_key in _adders.items():
        viewer.bind_key(key, _make_adder(event_type_key))
