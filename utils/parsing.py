#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 17:13:31 2025

@author: amansharma
"""
import re

def get_float_pos_comma(st):
    """Parse string representation of position to get coordinates.

    Args:
        st (str): String containing position coordinates

    Returns:
        list: List of integer coordinates
    """
    st = re.split(r'[ \[\,\]]', st)
    pos = [int(element) for element in st if element != '']
    return pos