# Install igraph if you don't have it already
if (!require(igraph)) {
  install.packages("igraph")
}
library(igraph)

# Specify the input folder (where your .txt files are located)
input_folder <- "/Users/saranshumale/Library/Mobile Documents/com~apple~CloudDocs/Documents/MitoProject_SharedFolder/Population_Fig1/gal_03032022/Gnets_gal"  # Replace with your input folder path

# Specify the output folder (where the PDF files will be saved)
output_folder <- "/Users/saranshumale/Library/Mobile Documents/com~apple~CloudDocs/Documents/MitoProject_SharedFolder/Population_Fig1/gal_03032022/R_output"  # Replace with your output folder path

# Create the output folder if it doesn't exist
if (!dir.exists(output_folder)) {
  dir.create(output_folder)
}

# Function to create edge curvature values for parallel edges
create_edge_curves <- function(graph, layout) {
  # Get the edge list
  edge_list <- as_edgelist(graph)
  
  # Initialize the edge curvature list
  edge_curves <- rep(0, ecount(graph))
  
  # Create a hash map to store edge counts between node pairs
  edge_counts <- list()
  edge_indices <- list()
  
  # Count parallel edges and store their indices
  for (i in 1:ecount(graph)) {
    edge <- edge_list[i, ]
    # Create a key (always put smaller node ID first for undirected graphs)
    key <- paste(min(edge), max(edge), sep="-")
    
    # Initialize if first encounter
    if (is.null(edge_counts[[key]])) {
      edge_counts[[key]] <- 0
      edge_indices[[key]] <- c()
    }
    
    # Increment count and store edge index
    edge_counts[[key]] <- edge_counts[[key]] + 1
    edge_indices[[key]] <- c(edge_indices[[key]], i)
  }
  
  # Set curvature for parallel edges
  for (key in names(edge_counts)) {
    count <- edge_counts[[key]]
    indices <- edge_indices[[key]]
    
    if (count > 1) {
      # Calculate offsets for multiple edges
      if (count == 2) {
        # For 2 parallel edges, use small positive and small negative curvature
        edge_curves[indices[1]] <- 0.3
        edge_curves[indices[2]] <- -0.3
      } else if (count == 3) {
        # For 3 parallel edges, use zero, positive, and negative curvature
        edge_curves[indices[1]] <- 0
        edge_curves[indices[2]] <- 0.5
        edge_curves[indices[3]] <- -0.5
      } else {
        # For 4+ parallel edges, distribute evenly from -0.5 to 0.5
        curve_range <- seq(-0.5, 0.5, length.out = count)
        for (i in 1:count) {
          edge_curves[indices[i]] <- curve_range[i]
        }
      }
    } else {
      # For single edges, use a slight curve to maintain spline appearance
      edge_curves[indices[1]] <- 0.05
    }
  }
  
  return(edge_curves)
}

# Get the list of text files to process from the input folder
file_list <- list.files(input_folder, pattern = "*.txt", full.names = TRUE)

# Loop through each file
for (file_name in file_list) {
  
  # Read the graph from the text file (edge list format)
  graph_data <- read.table(file_name, header = FALSE)
  
  # Extract only the first two columns (nodes), ignoring the weight (third column if present)
  edge_list <- graph_data[, 1:2]
  
  # Find the unique vertex IDs and relabel them if necessary
  unique_vertices <- unique(c(edge_list[, 1], edge_list[, 2]))
  vertex_mapping <- setNames(1:length(unique_vertices), unique_vertices)
  
  # Relabel the edge list using the vertex mapping
  relabeled_edge_list <- data.frame(
    node1 = vertex_mapping[as.character(edge_list[, 1])],
    node2 = vertex_mapping[as.character(edge_list[, 2])]
  )
  
  # Create a simplified edge list for the initial graph layout (one edge per node pair)
  simplified_edge_list <- unique(relabeled_edge_list)
  
  # First, create a simple graph for layout calculation
  simple_graph <- graph_from_edgelist(as.matrix(simplified_edge_list), directed = FALSE)
  
  # Create the full multigraph from the complete edge list 
  # This preserves all parallel edges
  multigraph <- graph_from_edgelist(as.matrix(relabeled_edge_list), directed = FALSE)
  
  # Calculate the degree of each node in the multigraph
  node_degrees <- degree(multigraph)
  
  # Define the node color based on degree
  # Color nodes with degree 3 as "red", others as "lightblue"
  node_colors <- ifelse(node_degrees == 3, "red", "lightblue")
  
  # Create a color vector for edges (darker color)
  edge_colors <- "gray40"  # Darker color for edges
  
  # Set up the PDF output file name based on the current text file
  pdf_file_name <- paste0(gsub(".txt", "", basename(file_name)), "_multigraph_splines.pdf")
  pdf_output_path <- file.path(output_folder, pdf_file_name)
  
  # Start PDF plotting
  pdf(pdf_output_path, width = 10, height = 8)  # Larger size for better visibility
  
  # Try Fruchterman-Reingold with more iterations and adjusted repulsion for better spacing
  # Use the simplified graph for layout calculation to avoid layout distortion from parallel edges
  layout_coords <- layout_with_fr(simple_graph, 
                                  niter = 5000,      # Increase iterations for more optimization
                                  area = 2000,       # More space between nodes
                                  repulserad = 250)  # Increased repulsion to avoid tight clusters
  
  # Calculate edge curves for the multigraph
  edge_curves <- create_edge_curves(multigraph, layout_coords)
  
  # Use the par function to enhance the plotting area
  par(mar = c(1, 1, 2, 1))  # Adjust margins for better fit
  
  # Plot the multigraph with spline edges
  plot(multigraph, 
       layout = layout_coords,     # Use the calculated layout
       main = paste("Multigraph from", basename(file_name)),
       vertex.size = 20,           # Node size
       vertex.label = NA,          # No labels
       vertex.color = node_colors, # Color nodes based on degree
       vertex.frame.color = "gray30", # Darker frame for nodes
       edge.arrow.size = 0,        # No arrow for undirected graph
       edge.color = edge_colors,   # Edge color
       edge.curved = edge_curves,  # Use calculated curvature
       edge.width = 1.5,           # Slightly thicker edges for visibility
       edge.lty = 1,               # Solid lines
       margin = 0)                 # No margin around vertices
  
  # Add title with better positioning
  title(main = paste("Multigraph from", basename(file_name)), 
        line = 0.5, 
        cex.main = 1.2)
  
  # Close the PDF device to save the plot
  dev.off()
  
  # Print message after each graph is saved
  cat("Saved multigraph with splines for", basename(file_name), "as", pdf_output_path, "\n")
  
  # Create a second visualization with larger size and better layout for complex graphs
  if (vcount(multigraph) > 15 || ecount(multigraph) > 30) {
    # For larger graphs, create an additional visualization with different layout
    pdf_file_name_large <- paste0(gsub(".txt", "", basename(file_name)), "_multigraph_large.pdf")
    pdf_output_path_large <- file.path(output_folder, pdf_file_name_large)
    
    pdf(pdf_output_path_large, width = 12, height = 10)  # Larger size
    
    # Try Kamada-Kawai layout which often works better for complex networks
    layout_coords_kk <- layout_with_kk(simple_graph)
    
    # Recalculate edge curves for this layout
    edge_curves <- create_edge_curves(multigraph, layout_coords_kk)
    
    # Use enhanced plotting parameters
    par(mar = c(1, 1, 2, 1))
    
    plot(multigraph, 
         layout = layout_coords_kk,
         main = paste("Multigraph (KK Layout) from", basename(file_name)),
         vertex.size = 20,
         vertex.label = NA,
         vertex.color = node_colors,
         vertex.frame.color = "gray30",
         edge.arrow.size = 0,
         edge.color = edge_colors,
         edge.curved = edge_curves,
         edge.width = 1.5,
         edge.lty = 1,
         margin = 0)
    
    dev.off()
    
    cat("Saved large multigraph for", basename(file_name), "as", pdf_output_path_large, "\n")
  }
}