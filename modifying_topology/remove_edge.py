import pandas as pd
import numpy as np
from app_state import app_state
from utils.parsing import get_float_pos_comma
from .add_edge import join

def remove(viewer)->bool:
    flag = False

    #Extracted nodes dataframe and path
    nd_pdf = app_state.node_dataframe
    node_path = app_state.node_path
    #Find connected nodes if any
    node_ids = nd_pdf['Node ID'].tolist()
    node_positions = nd_pdf['Position(ZXY)'].tolist()
    node_positions_fl = [get_float_pos_comma(st) for st in node_positions]

    #indices of selected nodes and their positions
    if (len(list(viewer.layers[1].selected_data))!=2):
        flag = True
        return flag
    ind_0 = list(viewer.layers[1].selected_data)[0]
    ind_1 = list(viewer.layers[1].selected_data)[1]
    pos_0 =list((viewer.layers[1].data[ind_0]))
    pos_1 =list((viewer.layers[1].data[ind_1]))
    
    check_ind_0 = False
    check_ind_1 = False
    for pn,posts in enumerate(node_positions_fl):
        if np.all(pos_0 == posts):
            node_index_0 = pn
            node_id_0 = node_ids[pn]
            check_ind_0 = True
        if np.all(pos_1 == posts):
            node_index_1 = pn
            node_id_1 = node_ids[pn]
            check_ind_1 = True 

    if check_ind_0 and check_ind_1:
        
        connected_nodes_0 = get_float_pos_comma(nd_pdf.loc[node_index_0,'Neighbour ID'])
        connected_nodes_1 = get_float_pos_comma(nd_pdf.loc[node_index_1,'Neighbour ID'])

        print(connected_nodes_0)
        print(connected_nodes_1)
        if (node_id_1 not in connected_nodes_0) or (node_id_0 not in connected_nodes_1):
            print('Nodes are not connected')
            print (node_id_1,connected_nodes_0)
            print (node_id_0,connected_nodes_1)
            flag = True
            return flag

        connected_nodes_0.remove(node_id_1)
        connected_nodes_1.remove(node_id_0)

        nd_pdf.loc[node_index_0,'Neighbour ID'] = str(connected_nodes_0)
        nd_pdf.loc[node_index_0,'Degree of Node'] = len(connected_nodes_0)
        nd_pdf.loc[node_index_1,'Neighbour ID'] = str(connected_nodes_1)
        nd_pdf.loc[node_index_1,'Degree of Node'] = len(connected_nodes_1)        

        if ((len(connected_nodes_0) == 2) and (node_id_0 not in connected_nodes_0)):
            
            neigh_id_0, neigh_id_1 = connected_nodes_0
            print(node_ids)

            for idn,id in enumerate(node_ids):
                if neigh_id_0 == id: 
                    neigh_ind_0 = idn
                    nns_0 = get_float_pos_comma(nd_pdf.loc[idn,'Neighbour ID'])
                    nns_0.remove(node_id_0)
                    nd_pdf.loc[idn,'Neighbour ID'] = str(nns_0)
                    nd_pdf.loc[idn,'Degree of Node'] = len(nns_0)
                if neigh_id_1 == id: 
                    neigh_ind_1 = idn
                    nns_1 = get_float_pos_comma(nd_pdf.loc[idn,'Neighbour ID'])
                    nns_1.remove(node_id_0)
                    nd_pdf.loc[idn,'Neighbour ID'] = str(nns_1)
                    nd_pdf.loc[idn,'Degree of Node'] = len(nns_1)

            print(neigh_id_0,neigh_id_1)
            print(neigh_ind_0,neigh_ind_1)
            join(viewer,neigh_ind_0,neigh_ind_1,True)
            nd_pdf.drop(node_index_0,inplace=True)
        
        
        nd_pdf.to_csv(node_path,index=False)
        node_ids = nd_pdf['Node ID'].tolist()
        node_positions = nd_pdf['Position(ZXY)'].tolist()

        if ((len(connected_nodes_1) == 2) and (node_id_1 not in connected_nodes_0)):
            
            neigh_id_0, neigh_id_1 = connected_nodes_1
            print(node_ids)
            for idn,id in enumerate(node_ids):
                if neigh_id_0 == id: 
                    neigh_ind_0 = idn
                    nns_0 = get_float_pos_comma(nd_pdf.loc[idn,'Neighbour ID'])
                    nns_0.remove(node_id_1)
                    nd_pdf.loc[idn,'Neighbour ID'] = str(nns_0)
                    nd_pdf.loc[idn,'Degree of Node'] = len(nns_0)
                    print(nd_pdf)
                    nd_pdf.to_csv(node_path,index=False)
                if neigh_id_1 == id: 
                    neigh_ind_1 = idn
                    nns_1 = get_float_pos_comma(nd_pdf.loc[idn,'Neighbour ID'])
                    nns_1.remove(node_id_1)
                    nd_pdf.loc[idn,'Neighbour ID'] = str(nns_1)
                    nd_pdf.loc[idn,'Degree of Node'] = len(nns_1)
                    print(nd_pdf)
                    nd_pdf.to_csv(node_path,index=False)

            print(neigh_id_0,neigh_id_1)
            print(neigh_ind_0,neigh_ind_1)
            join(viewer,neigh_ind_0,neigh_ind_1,True)
            print(nd_pdf)
            nd_pdf.drop(node_index_1,inplace=True)
            print(nd_pdf)
            nd_pdf.to_csv(node_path,index=False)

        print(connected_nodes_0)
        print(connected_nodes_1)
        nd_pdf.to_csv(node_path,index=False)
        return flag

    else:
        flag = True
        return flag