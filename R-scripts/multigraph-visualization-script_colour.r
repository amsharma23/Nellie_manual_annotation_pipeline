# Install igraph if you don't have it already
if (!require(igraph)) {
  install.packages("igraph")
}
library(igraph)

# Specify the input folder (where your .txt files are located)
input_folder <- "/Users/amansharma/Documents/Data/Saransh_mito_data/Agar_Pad_mito_population/Size_sorted_gnets/ethanol" # Replace with your input folder path

# Specify the output folder (where the PDF files will be saved)
output_folder <- "/Users/amansharma/Documents/Data/Saransh_mito_data/Agar_Pad_mito_population/Size_sorted_gnets/ethanol/Routput"  # Replace with your output folder path

# Create the output folder if it doesn't exist
if (!dir.exists(output_folder)) {
  dir.create(output_folder)
}

# Function to extract color from a dictionary-like string
extract_color <- function(dict_string) {
  # Default color if parsing fails
  default_color <- "gray40"
  
  # Print the raw string for debugging
  cat("Raw string: ", dict_string, "\n")
  
  # Check if the string matches {'colour': 'red'} format
  # This regex looks for 'colour': followed by a value in quotes
  color_match <- regexpr("'colour':\\s*'([^']+)'", dict_string)
  
  if (color_match > 0) {
    # Extract the matched group (the color value)
    match_length <- attr(color_match, "match.length")
    matched_text <- substr(dict_string, color_match, color_match + match_length - 1)
    
    # Extract just the color value (between the second set of quotes)
    color_value_match <- regexpr("'([^']+)'$", matched_text)
    if (color_value_match > 0) {
      value_length <- attr(color_value_match, "match.length")
      value_text <- substr(matched_text, color_value_match, color_value_match + value_length - 1)
      # Remove quotes
      color <- gsub("'", "", value_text)
      cat("Extracted color: ", color, "\n")
      return(color)
    }
  }
  
  # Try without quotes - format: {colour: red}
  color_match <- regexpr("\\{colour:\\s*([^}]+)\\}", dict_string)
  
  if (color_match > 0) {
    # Extract the matched text
    match_length <- attr(color_match, "match.length")
    matched_text <- substr(dict_string, color_match, color_match + match_length - 1)
    
    # Extract just the color value (everything after "colour: " and before the closing brace)
    color_value <- gsub("\\{colour:\\s*", "", matched_text)
    color_value <- gsub("\\}$", "", color_value)
    
    # Trim any whitespace
    color_value <- trimws(color_value)
    
    cat("Extracted color: ", color_value, "\n")
    return(color_value)
  }
  
  cat("No match found, using default color\n")
  return(default_color)
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
file_list <- list.files(input_folder, pattern = "*.gnet", full.names = TRUE)

# Loop through each file
for (file_name in file_list) {
  cat("Processing file:", basename(file_name), "\n")
  
  # First, read the file as raw text to properly handle the dictionary format
  lines <- readLines(file_name,skip=1)
  # Initialize empty vectors for nodes and colors
  from_nodes <- c()
  to_nodes <- c()
  colors <- c()
  
  # Process each line to extract nodes and color
  for (line in lines) {
    # Skip empty lines
    if (trimws(line) == "") next
    
    # Find the positions of the first two spaces
    first_space <- regexpr(" ", line)
    
    if (first_space > 0) {
      # Extract first node
      from_node <- substr(line, 1, first_space - 1)
      
      # Look for second space after the first space
      remaining <- substr(line, first_space + 1, nchar(line))
      second_space <- regexpr(" ", remaining)
      
      if (second_space > 0) {
        # Extract second node
        to_node <- substr(remaining, 1, second_space - 1)
        
        # Everything after the second node is the dictionary part
        dict_part <- substr(remaining, second_space + 1, nchar(remaining))
        
        # Extract color
        color <- extract_color(dict_part)
      } else {
        # If there's no second space, just use the rest as the second node
        # and set a default color
        to_node <- remaining
        color <- "gray40"
      }
      
      # Add to our vectors
      from_nodes <- c(from_nodes, from_node)
      to_nodes <- c(to_nodes, to_node)
      colors <- c(colors, color)
    }
  }
  
  # Create the edge list
  edge_list <- data.frame(
    from = from_nodes,
    to = to_nodes,
    stringsAsFactors = FALSE
  )
  
  # Debug: Print the first few rows of parsed data
  cat("First few rows of parsed data:\n")
  print(head(edge_list))
  cat("Associated colors:\n")
  print(head(colors))
  
  # Find the unique vertex IDs and relabel them if necessary
  unique_vertices <- unique(c(edge_list$from, edge_list$to))
  vertex_mapping <- setNames(1:length(unique_vertices), unique_vertices)
  
  # Relabel the edge list using the vertex mapping
  relabeled_edge_list <- data.frame(
    node1 = vertex_mapping[edge_list$from],
    node2 = vertex_mapping[edge_list$to]
  )
  
  # Create a simplified edge list for the initial graph layout (one edge per node pair)
  simplified_edge_list <- unique(relabeled_edge_list)
  
  # First, create a simple graph for layout calculation
  simple_graph <- graph_from_edgelist(as.matrix(simplified_edge_list), directed = FALSE)
  
  # Create the full multigraph from the complete edge list 
  # This preserves all parallel edges
  multigraph <- graph_from_edgelist(as.matrix(relabeled_edge_list), directed = FALSE)
  
  # Add edge colors as an edge attribute
  E(multigraph)$color <- colors
  
  # Calculate the degree of each node in the multigraph
  node_degrees <- degree(multigraph)
  
  # Define the node color based on degree
  # Color nodes with degree 3 or more as "red", others as "lightblue"
  node_colors <- ifelse(node_degrees >= 3, "red", "lightblue")
  
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
       vertex.size = 10,           # Node size
       vertex.label = NA,          # No labels
       vertex.color = node_colors, # Color nodes based on degree
       vertex.frame.color = "gray30", # Darker frame for nodes
       edge.arrow.size = 0,        # No arrow for undirected graph
       edge.curved = edge_curves,  # Use calculated curvature
       edge.width = 2.0,           # Slightly thicker edges for visibility
       edge.lty = 1,               # Solid lines
       edge.color = E(multigraph)$color, # Use the extracted edge colors
       margin = 0)                 # No margin around vertices
  
  # Close the PDF device to save the plot
  dev.off()
  
  # Print message after each graph is saved
  cat("Saved multigraph with splines for", basename(file_name), "as", pdf_output_path, "\n")
}