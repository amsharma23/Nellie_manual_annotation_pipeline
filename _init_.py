#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 16:54:00 2025

@author: amansharma
"""

"""
Napari plugin for analyzing 3D skeletal structures using the Nellie library.
This plugin allows for loading, processing, and visualization of 3D microscopy data.
"""

__version__ = '0.1.0'

# Import main entry point for napari to discover
from .main import main

# Optional: Make key components available at package level
from .app_state import app_state

# Define what gets imported with "from nellie_napari_plugin import *"
__all__ = ['main', 'app_state']