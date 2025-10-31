import pandas as pd
import numpy as np
from app_state import app_state
from utils.parsing import get_float_pos_comma

def load_tip(viewer):
    nd_pdf = app_state.node_dataframe
    node_path = app_state.node_path

    # Get Extracted Nodes layer by name
    if 'Extracted Nodes' not in viewer.layers:
        print("Extracted Nodes layer not found.")
        return
    extracted_layer = viewer.layers['Extracted Nodes']

    if len(list(extracted_layer.selected_data)) == 0:
        print("No node selected.")
        return

    ind = list(extracted_layer.selected_data)[0]
    pos =(extracted_layer.data[ind])
    insert_loc = nd_pdf.index.max()

    if pd.isna(insert_loc):
        insert_loc = 0
    else:
        insert_loc = insert_loc+1

    nd_pdf.loc[insert_loc,'Degree of Node'] = 1
    nd_pdf.loc[insert_loc,'Position(ZXY)'] = str(pos)
    ind_1 = [get_float_pos_comma(st) for st in list(nd_pdf['Position(ZXY)'])]

    # Update extracted nodes layer
    if 'Extracted Nodes' in viewer.layers:
        pos_ex = list(extracted_layer.data)
        print(type(pos_ex[0]))

        if (any(np.array_equal(pos, arr) for arr in pos_ex)):
            pos_ex[-1] = pos
            extracted_layer.data = pos_ex
            color_ex = list(extracted_layer.face_color)
            color_ex[-1] = [0.,0.,1.,1.]
            extracted_layer.face_color = color_ex
            
            for ni,i  in enumerate(ind_1):
                if(all(x == y for x, y in zip(i, pos)) and len(pos) == len(i)):    
                    nd_pdf.drop((ni),inplace=True)                
            nd_pdf.to_csv(node_path,index=False)
            
        else:
            pos_ex.append(pos)
            extracted_layer.data = pos_ex
            print(list(extracted_layer.data))
            color_ex = list(extracted_layer.face_color)
            color_ex[-1] = [0.,0.,1.,1.]
            extracted_layer.face_color = color_ex
            nd_pdf.to_csv(node_path,index=False)

    else:
        p_l = viewer.add_points(pos,size=5,face_color=[[0.,0.,1.,1.]],name='imp_l',scale= [1.765,1,1])
        nd_pdf.to_csv(node_path,index=False)