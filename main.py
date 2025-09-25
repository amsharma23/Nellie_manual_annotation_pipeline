#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 16:54:53 2025

@author: amansharma
"""
import napari
from napari.utils.notifications import show_warning
from gui.viewer import load_viewer

# Check if Nellie is available
try:
    from nellie.im_info.verifier import ImInfo
    NELLIE_AVAILABLE = True
except ImportError:
    NELLIE_AVAILABLE = False


def main():
    """Main function to start the application."""
    viewer = load_viewer()
    # Check for Nellie library
    if not NELLIE_AVAILABLE:
        show_warning("Nellie library not found. Please install it for full functionality.")
    
    return viewer

if __name__ == "__main__":
    viewer = main()
    napari.run()
