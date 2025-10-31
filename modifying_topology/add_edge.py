import pandas as pd
import numpy as np
from app_state import app_state
from utils.parsing import get_float_pos_comma


def join(viewer,node_ind_0=None,node_ind_1=None,from_remove=False):

    #Extracted nodes dataframe and path
    nd_pdf = app_state.node_dataframe
    node_path = app_state.node_path

    # Get Extracted Nodes layer by name
    if 'Extracted Nodes' not in viewer.layers and not from_remove:
        print("Extracted Nodes layer not found.")
        return
    if not from_remove:
        extracted_layer = viewer.layers['Extracted Nodes']

    #Find connected nodes if any
    node_positions = nd_pdf['Position(ZXY)'].tolist()
    node_positions_fl = [get_float_pos_comma(st) for st in node_positions]
    nodes_extracted = nd_pdf['Node ID'].tolist()
    node_ids = [int(st) for st in nodes_extracted]
    max_node_id = max(node_ids)
    check_ind_0 = False
    check_ind_1 = False

    #indices of selected nodes and their positions
    if not from_remove and (len(list(extracted_layer.selected_data))!=2):
        print('here1')
        return

    if not from_remove:
        ind_0 = list(extracted_layer.selected_data)[0]
        ind_1 = list(extracted_layer.selected_data)[1]
        pos_0 =(extracted_layer.data[ind_0])
        pos_1 =(extracted_layer.data[ind_1])
   
        
        for posts in node_positions_fl:
            check_ind_0 = np.all(pos_0 == posts) or check_ind_0
            check_ind_1 = np.all(pos_1 == posts) or check_ind_1


    if (check_ind_0 and check_ind_1) or from_remove:
        if not from_remove:    
            for pn,posts in enumerate(node_positions_fl):
                if(np.all(pos_0 == posts)): node_ind_0 = pn; node_id_0 = node_ids[pn]
                if(np.all(pos_1 == posts)): node_ind_1 = pn; node_id_1 = node_ids[pn]
        elif from_remove:
            node_id_0 = node_ids[node_ind_0]
            node_id_1 = node_ids[node_ind_1]

        print('Joining nodes: ',node_id_0,node_id_1)
        connected_nodes_0 = get_float_pos_comma(nd_pdf.loc[node_ind_0,'Neighbour ID'])
        connected_nodes_1 = get_float_pos_comma(nd_pdf.loc[node_ind_1,'Neighbour ID'])
        print(connected_nodes_0,connected_nodes_1)
        connected_nodes_0.append(node_id_1)
        connected_nodes_1.append(node_id_0)
        print(connected_nodes_0,connected_nodes_1)
        nd_pdf.loc[node_ind_0,'Neighbour ID'] = str(connected_nodes_0)
        nd_pdf.loc[node_ind_0,'Degree of Node'] = len(connected_nodes_0)

        nd_pdf.loc[node_ind_1,'Neighbour ID'] = str(connected_nodes_1)
        nd_pdf.loc[node_ind_1,'Degree of Node'] = len(connected_nodes_1)

        print(nd_pdf)
        nd_pdf.to_csv(node_path,index=False)
        return

    
    elif (not check_ind_0) and check_ind_1:
        for pn,posts in enumerate(node_positions_fl):
            if(np.all(pos_1 == posts)): node_id_1 =pn

        connected_nodes_1 = get_float_pos_comma(nd_pdf.loc[node_id_1,'Neighbour ID'])

        insert_loc = nd_pdf.index.max()
        if pd.isna(insert_loc):
            insert_loc = 0    
        else:
            insert_loc = insert_loc+1
        
        nd_pdf.loc[insert_loc,'Node ID'] = max_node_id+1
        nd_pdf.loc[insert_loc,'Degree of Node'] = 1
        nd_pdf.loc[insert_loc,'Position(ZXY)'] = str(pos_0)
        nd_pdf.loc[insert_loc,'Neighbour ID'] = [node_id_1]

        connected_nodes_1.append(max_node_id+1)
        nd_pdf.loc[node_id_1,'Neighbour ID'] = str(connected_nodes_1)
        nd_pdf.loc[node_id_1,'Degree of Node'] = len(connected_nodes_1)

        nd_pdf.to_csv(node_path,index=False)
        return
    


    elif (not check_ind_1) and check_ind_0:

        for pn,posts in enumerate(node_positions_fl):
            if(np.all(pos_0 == posts)): node_id_0 =pn
        connected_nodes_0 = get_float_pos_comma(nd_pdf.loc[node_id_0,'Neighbour ID'])

        insert_loc = nd_pdf.index.max()
        if pd.isna(insert_loc):
            insert_loc = 0    
        else:
            insert_loc = insert_loc+1
        
        nd_pdf.loc[insert_loc,'Node ID'] = max_node_id+1
        nd_pdf.loc[insert_loc,'Degree of Node'] = 1
        nd_pdf.loc[insert_loc,'Position(ZXY)'] = str(pos_1)
        nd_pdf.loc[insert_loc,'Neighbour ID'] = [node_id_0]

        connected_nodes_0.append(max_node_id+1)
        nd_pdf.loc[node_id_0,'Neighbour ID'] = str(connected_nodes_0)
        nd_pdf.loc[node_id_0,'Degree of Node'] = len(connected_nodes_0)

        nd_pdf.to_csv(node_path,index=False)
        return
    
    elif (not check_ind_0) and (not check_ind_1):
        
        insert_loc = nd_pdf.index.max()
        if pd.isna(insert_loc):
            insert_loc = 0    
        else:
            insert_loc = insert_loc+1
        
        nd_pdf.loc[insert_loc,'Node ID'] = max_node_id+1
        nd_pdf.loc[insert_loc,'Degree of Node'] = 1
        nd_pdf.loc[insert_loc,'Position(ZXY)'] = str(pos_0)
        nd_pdf.loc[insert_loc,'Neighbour ID'] = [max_node_id+2]

        nd_pdf.loc[insert_loc+1,'Node ID'] = max_node_id+2
        nd_pdf.loc[insert_loc+1,'Degree of Node'] = 1
        nd_pdf.loc[insert_loc+1,'Position(ZXY)'] = str(pos_1)
        nd_pdf.loc[insert_loc+1,'Neighbour ID'] = [max_node_id+1]

        nd_pdf.to_csv(node_path,index=False)
        return