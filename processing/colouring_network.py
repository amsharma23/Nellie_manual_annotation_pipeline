import os
import numpy as np
import networkx as nx
from tifffile import imread
import pandas as pd
#from utils.parsing import get_float_pos_comma
import ast
from scipy.ndimage import label as labell
from collections import Counter

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

def get_edge_colours(mask_path,extracted_path,op_path):

    G = nx.MultiGraph()
    ext_df = pd.read_csv(extracted_path)
    nodes_id = ext_df['Node ID'].tolist()
    pos = ext_df['Position(ZXY)'].tolist()
    mask = imread(mask_path)
    print(np.shape(mask))
    mask_l, num_feat = labell(mask)
    print(np.shape(mask_l))
    print(num_feat)
    srcs = []
    edges = []
    
    regions = (np.unique(mask_l[np.nonzero(mask)]))
    print(len(regions))

    if len(regions) ==1:
        mother_value = np.max(regions)
    else:
        min_val_pixs = np.sum(mask_l == np.min(regions))
        max_value_pixs = np.sum(mask_l == np.max(regions))
        if min_val_pixs>max_value_pixs: mother_value = np.min(regions); daughter_value = np.max(regions)
        else:  mother_value = np.max(regions); daughter_value = np.min(regions)

    for i_n,i in enumerate(nodes_id):
        srcs.append(i)

        neighbours = ext_df['Neighbour ID'].apply(ast.literal_eval)[i_n]
        
        neighbours_counts = Counter(neighbours)
        pos_n1 = get_float_pos_comma(pos[i_n])
        pos_x_n1 = pos_n1[1]
        pos_y_n1 = pos_n1[2]

        for neighbour,count in neighbours_counts.items():
            nn = nodes_id.index(neighbour)
            if (neighbour not in srcs) or (neighbour == i):
                
                pos_n2 = get_float_pos_comma(pos[nn])
                pos_x_n2 = pos_n2[1]
                pos_y_n2 = pos_n2[2]

                print(pos_n1,pos_n2)
                print(np.shape(mask))
                print(np.shape(mask_l))
                r_n1 = mask_l[(pos_y_n1),(pos_x_n1)]
                r_n2 = mask_l[(pos_y_n2),(pos_x_n2)]

                if len(regions)==1: #if only mother present
                    colour = 'red'    
                else:
                    if r_n1 == r_n2: #if both are in the same region
                        if r_n1 == mother_value: colour = 'red' #same region being mother
                        else: colour = 'green' #same region being daughter
                    else:                            
                            if r_n1 == 0.0 or r_n2 == 0.0: 
                                r_c = np.nonzero([r_n1,r_n2])
                                if r_c == mother_value: colour = 'red' #by default put in mother
                                else: colour = 'green'
                            else:
                                    colour = 'yellow'
                for _ in range(count):
                        edges.append([i,neighbour,{'colour':colour}])    

    G.add_edges_from(edges)
    nx.write_edgelist(G, op_path)

# if __name__ == "__main__":
    
#      fld_place = '/Users/amansharma/Desktop/Manual_annotation_testing/2/images_folder'
#      mask_fld_path = '/Users/amansharma/Desktop/Manual_annotation_testing/2/cleaned_masks/'
#      op_path = '/Users/amansharma/Desktop/Manual_annotation_testing/2/coloured_edge_lists/'

#      for i in range(3,40,3):
#         expath = os.path.join(fld_place, str(i)+'/nellie_output/t_' + str(i) + '_extracted.csv')
#         mpath = os.path.join(mask_fld_path, 't_'+str(i)+'.tif')
#         opp_path = os.path.join(op_path,'coloured_edge_list_' + str(i) + '.txt')
#         print(opp_path,mpath)
#         get_edge_colours(mpath,expath,opp_path)