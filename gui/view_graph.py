import os
from app_state import app_state
from natsort import natsorted
from utils.adjacency_reader import adjacency_to_extracted
from .visualize_graph import make_multigraph_image
from .visualize_graph import load_graph_on_viewer

def view_graph(self):
    if app_state.folder_type == 'Single TIFF':
                    
        tif_files = os.listdir(app_state.nellie_output_path)
        multigraph_im = [f for f in tif_files if (f.endswith('multigraph.png') or f.endswith('multigraph.pdf'))]
        
        if not multigraph_im:
            pixel_class_path = [f for f in tif_files if (f.endswith('im_pixel_class.ome.tif') or f.endswith('im_pixel_class.ome.tiff'))][0]
            pixel_base_name = os.path.basename(pixel_class_path).split(".")[0]

            adjacency_path = [fls for fls in os.listdir(app_state.nellie_output_path) if fls.endswith('_adjacency_list.csv')][0]
            adjacency_path = os.path.join(app_state.nellie_output_path, adjacency_path)

            extracted_data_path = [fls for fls in os.listdir(app_state.nellie_output_path) if fls.endswith('_extracted.csv')][0]
            extracted_data_path = os.path.join(app_state.nellie_output_path, extracted_data_path)
            
            if not os.path.exists(extracted_data_path) and os.path.exists(adjacency_path):
                adjacency_to_extracted(extracted_data_path,adjacency_path)
                self.log_status("Error: Extracted data not found.")
                return

            success = make_multigraph_image(self,extracted_data_path,pixel_base_name)

            if success:
                load_graph_on_viewer(self)
            else:
                self.log_status(f"Error: Making Graph visual failed for {extracted_data_path}.")
        
        elif multigraph_im:
                app_state.graph_image_path = os.path.join(nellie_path, multigraph_im[0])
                self.log_status(f"Graph already generated for {current_subdir}.")
                load_graph_on_viewer(self)

        elif app_state.folder_type == 'Time Series':

            subdirs = [d for d in os.listdir(app_state.loaded_folder) 
                    if os.path.isdir(os.path.join(app_state.loaded_folder, d))]
            subdirs = natsorted(subdirs)

            if subdirs:
                
                app_state.current_image_index = self.image_slider.value() - 1
                current_subdir = subdirs[app_state.current_image_index]
                print(f"Current subdir: {current_subdir}")

                subdir_path = os.path.join(app_state.loaded_folder, current_subdir)
                nellie_path = os.path.join(subdir_path,'nellie_output')
                tif_files = os.listdir(nellie_path)
                multigraph_im = [f for f in tif_files if (f.endswith('multigraph.png') or f.endswith('multigraph.pdf'))]
                
                if not multigraph_im:
                    
                    pixel_class_path = [f for f in tif_files if (f.endswith('im_pixel_class.ome.tif') or f.endswith('im_pixel_class.ome.tiff'))][0]
                    pixel_base_name = os.path.basename(pixel_class_path).split(".")[0]

                    adjacency_path = [fls for fls in os.listdir(nellie_path) if fls.endswith('_adjacency_list.csv')][0]
                    adjacency_path = os.path.join(nellie_path, adjacency_path)

                    extracted_data_path = [fls for fls in os.listdir(nellie_path) if (fls == pixel_base_name+'_extracted.csv')][0]
                    extracted_data_path = os.path.join(nellie_path, extracted_data_path)
                    
                    if not os.path.exists(extracted_data_path) and os.path.exists(adjacency_path):
                        adjacency_to_extracted(extracted_data_path,adjacency_path)
                        self.log_status("Error: Extracted data not found.")
                        return
                    
                    self.log_status(f"Skeleton base name: {pixel_base_name}")
                    success = make_multigraph_image(self,extracted_data_path,pixel_base_name)
                
                    if success:
                        load_graph_on_viewer(self)
                    else:
                        self.log_status(f"Error: Graph visualization failed for {current_subdir}.")
                    
                elif multigraph_im:
                    app_state.graph_image_path = os.path.join(nellie_path, multigraph_im[0])
                    self.log_status(f"Graph already generated for {current_subdir}.")
                    load_graph_on_viewer(self)
            
            elif not subdirs:
                self.log_status("No time series data found.")
                return