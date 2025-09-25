import napari
from napari.utils.notifications import show_warning
from modifying_topology.add_tip import load_tip
from modifying_topology.add_junction import load_junction 
from gui.gui_layout_and_process import FileLoaderWidget

def load_viewer() -> napari.Viewer:
    """Load the viewer."""
    viewer = napari.Viewer(title="Nellie Network Analysis")
     # Add main widget to viewer
    file_loader = FileLoaderWidget(viewer)
    viewer.window.add_dock_widget(file_loader, area='right', name="Nellie Controls")

    return viewer