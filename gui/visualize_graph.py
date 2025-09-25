from app_state import app_state
from utils.parsing import get_float_pos_comma
import os
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from qtpy.QtGui import QPixmap, QImage
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QLabel

def make_multigraph_image(widget,extracted_data_path,base_name,scale_factor=1.0):
    """
    Visualize a multigraph from an adjacency list CSV file with proper handling of parallel edges.
    Includes node numbers for better identification.
    
    Parameters:
    -----------
    adjacency_path : str
        Path to the adjacency list CSV file
    output_path : str
        Path where the output image will be saved
    scale_factor : float, optional
        Scale factor to apply to the graph (default: 1.0)
        
    Returns:
    --------
    bool
        True if visualization succeeded, False otherwise
    """
    try:
        
        output_path = os.path.join(app_state.nellie_output_path, base_name+'_multigraph.png')
        # Check if input file exists
        
        if not os.path.exists(extracted_data_path):
            widget.log_status(f"Error: Input file does not exist: {extracted_data_path}")
            return False
        else:
            widget.log_status(f"Making Multigraph for: {extracted_data_path}")

        # Read the extracted list CSV data
        ext_data = pd.read_csv(extracted_data_path)
        
        # Create a MultiGraph to properly track parallel edges
        G = nx.MultiGraph()
        
        # Add all nodes with their positions (helpful for layout)
        for _, row in ext_data.iterrows():
            G.add_node(row['Node ID'], 
                    pos_x=get_float_pos_comma(row['Position(ZXY)'])[1], 
                    pos_y=get_float_pos_comma(row['Position(ZXY)'])[2], 
                    pos_z=get_float_pos_comma(row['Position(ZXY)'])[0],
            )
        
        # Add edges and track multiplicity
        edge_count = {}  # This should be a dictionary, not an int
        for _, row in ext_data.iterrows():
            node_id = row['Node ID']
            adj_list = get_float_pos_comma(row['Neighbour ID'])
            edge_count_temp = {}
            for neighbor in adj_list:
                # Also track for statistics
                if tuple(sorted([node_id, neighbor])) not in edge_count.keys():
                    edge_key = tuple(sorted([node_id, neighbor]))
                    if edge_key in edge_count_temp:
                        edge_count_temp[edge_key] += 1
                    else:
                        edge_count_temp[edge_key] = 1

            for edge_key in edge_count_temp.keys():
                for i in range(edge_count_temp[edge_key]): G.add_edge(edge_key[0], edge_key[1])
                edge_count[edge_key] = edge_count_temp[edge_key]

       # Calculate node degrees (from the multigraph to count parallel edges)
        node_degrees = dict(G.degree())
        
        # Set up the plot with high resolution
        fig = plt.figure(figsize=(13.33, 10), dpi=300)
        ax = plt.gca()
        # Use a specialized layout algorithm for reducing edge crossings
        try:
            # First try kamada_kawai which often gives better layouts with fewer crossings
            layout = nx.kamada_kawai_layout(G, scale=scale_factor)
        
        except:
            # Fall back to spring layout if kamada_kawai fails
            layout = nx.spring_layout(
                G, 
                k=0.3 / np.sqrt(len(G.nodes())) * scale_factor,
                iterations=1000,
                seed=42
            )
        
        # Node colors based on degree
        node_colors = []
        for node in G.nodes():
            if node_degrees[node] == 1:
                node_colors.append('blue')  # Endpoints
            elif node_degrees[node] >= 3:
                node_colors.append('red')   # Junctions
            else:
                node_colors.append('lightblue')  # Other nodes
        
        # Draw nodes
        node_size = max(5, 15 / scale_factor) * 25
        nx.draw_networkx_nodes(
            G, 
            layout,
            node_color=node_colors,
            node_size=node_size,
            edgecolors='black',
            linewidths=1.5
        )
        
        # Draw all edges with appropriate curves for parallel edges
        edge_width = max(0.5, 1.5/scale_factor)
        
        # Now draw each group of edges
        for edge_key in edge_count.keys():
            u, v = edge_key
            num_edges = edge_count[edge_key]

            if num_edges == 1:
                # Single edge - draw straight
                nx.draw_networkx_edges(
                    G,
                    layout,
                    edgelist=[(u, v)],
                    width=edge_width,
                    edge_color='gray'
                )
            else:
                # Multiple parallel edges - draw curved with different curvature values
                max_curve = 0.3 * min(1, np.sqrt(num_edges) / 5)
                
                if num_edges % 2 == 0:  # Even number
                    curves = np.linspace(-max_curve, max_curve, num_edges)
                else:  # Odd number with one straight edge
                    curves = np.linspace(-max_curve, max_curve, num_edges)
                
                for i in range(num_edges):
                    ax.annotate("", 
                                xy=layout[u], xycoords='data',
                                xytext=layout[v], textcoords='data',
                                arrowprops=dict(
                                arrowstyle="-", 
                                color='gray',  # You can replace with your color scheme
                                connectionstyle=f"arc3,rad={curves[i]}",
                                linewidth=edge_width  # Using the edge_width from your first snippet
                            ))
        
        # Draw node labels (node numbers)
        # Adjust font size based on scale and number of nodes
        font_size = max(8, 10 / scale_factor)
        if len(G.nodes()) > 100:
            font_size = max(6, 8 / scale_factor)  # Smaller font for larger graphs
            
        # Create labels dictionary (each node gets its number as label)
        labels = {node: str(node) for node in G.nodes()}
        
        # Draw the labels with a slight offset from the nodes
        nx.draw_networkx_labels(
            G, 
            layout, 
            labels=labels,
            font_size=font_size,
            font_weight='bold',
            font_color='black',
            # Add a white background to make labels more readable
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=1)
        )
        
        # Create legend
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=10, label='Endpoints (deg 1)'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='red', markersize=10, label='Junctions (deg 3+)'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='lightblue', markersize=10, label='Other Nodes')
        ]
        
        plt.legend(
            handles=legend_elements, 
            loc='upper right',
            frameon=True,
            framealpha=1,
            facecolor='white',
            edgecolor='black',
            fontsize=12
        )
        
        # Statistics for title
        total_nodes = len(G.nodes())
        unique_edges = len(edge_count)
        total_edges = G.number_of_edges()
        multiple_edges = sum(1 for count in edge_count.values() if count > 1)
        
        # Add title and subtitle
        plt.title(f"Multigraph from {base_name}", fontsize=14)
        plt.figtext(
            0.5, 0.01,
            f"Total nodes: {total_nodes} - Total edges: {total_edges} - Unique edges: {unique_edges} - "
            f"Multiple edges: {multiple_edges} - Scale: {scale_factor}x",
            ha='center',
            fontsize=12
        )
        
        # Remove axis and set tight layout
        plt.axis('off')
        plt.tight_layout(pad=2.0)
        plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
        
        # Save the figure
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        app_state.graph_image_path = output_path
        widget.log_status(f"Graph saved to: {output_path}")
        return True
        
    except Exception as e:
        widget.log_status(f"Error processing file: {str(e)}")
        return False

def load_graph_on_viewer(widget):
    
    # Load the image and convert to QPixmap for display
    graph_image = QImage(app_state.graph_image_path)
    pixmap = QPixmap.fromImage(graph_image)
    
    # Calculate available width from the scroll area
    available_width = widget.graph_scroll.width() - 20  # Subtract some padding
    
    # Scale the image to fit while maintaining aspect ratio
    scaled_pixmap = pixmap.scaled(
        available_width, 
        available_width,  # Use width for height too to maintain aspect ratio
        Qt.KeepAspectRatio, 
        Qt.SmoothTransformation
    )
    
    # Display the image in the graph_image_label
    widget.graph_image_label.setPixmap(scaled_pixmap)
    widget.graph_image_label.setMinimumSize(scaled_pixmap.width(), scaled_pixmap.height())
    
    # Log status
    widget.log_status("Graph visualization displayed")
    
    # Enable the button to open in new window
    widget.open_graph_btn.setEnabled(True)