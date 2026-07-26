#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone Dynamic-Event Annotation tool.

Loads a raw 4D OME-TIFF stack and a skeleton (pixel-class) 4D OME-TIFF, and
provides key bindings to annotate dynamic events on the skeleton. No network
analysis, no automated dynamics detection, no Nellie processing.

Run:  python main.py
"""
import napari

from widget import AnnotationWidget


def main():
    viewer = napari.Viewer(title="Dynamic Event Annotation")
    widget = AnnotationWidget(viewer)
    viewer.window.add_dock_widget(widget, area='right', name="Annotation Controls")
    return viewer


if __name__ == "__main__":
    viewer = main()
    napari.run()
