#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 10 17:24:00 2025

@author: amansharma
"""
import os
import pandas as pd
from .parsing import get_float_pos_comma

def adjacency_to_extracted(extracted_csv_path,adjacency_path):
    
    adj_df = pd.read_csv(adjacency_path)
    if os.path.exists(extracted_csv_path):
        ext_df = pd.read_csv(extracted_csv_path)
    else:
        ext_df={}
        
    adjs_list = adj_df['adjacencies'].tolist()
    deg_nd_i = []
    deg_nd = []
    
    for el in adjs_list:
        elf = get_float_pos_comma(el)
        deg_nd_i.append(len(elf))
        if (len(elf)>0):
            deg_nd.append(len(elf))
        
    pos_x = adj_df['pos_x'].tolist()
    pos_y = adj_df['pos_y'].tolist()
    pos_z = adj_df['pos_z'].tolist()

    pos_zxy = [[pos_z[i_n],pos_y[i_n],pos_x[i_n]] for i_n,i in enumerate(deg_nd) if i>0]    
    
    ext_df['Degree of Node'] = deg_nd
    ext_df['Position(ZXY)'] = pos_zxy
    
    ext_df = pd.DataFrame.from_dict(ext_df)
    
   
    
    ext_df.to_csv(extracted_csv_path,index=False)    