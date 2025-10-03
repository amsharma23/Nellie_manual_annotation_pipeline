import pandas as pd
import numpy as np
from app_state import app_state
from utils.parsing import get_float_pos_comma


def highlight(viewer,widget):
    
    #Extracted nodes dataframe and path
    nd_pdf = app_state.node_dataframe
    node_path = app_state.node_path
    
    #indices of selected nodes and their positions
    if (len(list(viewer.layers[1].selected_data))==0):
        widget.log_status("No node selected to edit.")
        return
    ind = list(viewer.layers[1].selected_data)[0]
    pos =(viewer.layers[1].data[ind])
    app_state.selected_node_position = pos    
    
    #Find connected nodes if any
    node_ids = nd_pdf['Node ID'].tolist()
    node_positions = nd_pdf['Position(ZXY)'].tolist()

    ind_selected = [stn for stn,st in enumerate(list(node_positions)) if (get_float_pos_comma(st) == pos).all()][0]
    connected_nodes = get_float_pos_comma(nd_pdf.loc[ind_selected,'Neighbour ID'])
    
    for eln,el in enumerate(node_ids):
        if el in connected_nodes:
            app_state.editable_node_positions.append(get_float_pos_comma(node_positions[eln]))
    widget.log_status(f"Connected nodes found: {len(app_state.editable_node_positions)}")
    app_state.points_layer = viewer.add_points(
                                    app_state.editable_node_positions,
                                    size=5,
                                    face_color='yellow',
                                    scale=[1.765, 1, 1],
                                    name='Connected Nodes'
                                )
    