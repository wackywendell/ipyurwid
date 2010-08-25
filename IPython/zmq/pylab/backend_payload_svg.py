# Standard library imports
from cStringIO import StringIO

# System library imports.
from matplotlib.backends.backend_svg import new_figure_manager
from matplotlib._pylab_helpers import Gcf

# Local imports.
from backend_payload import add_plot_payload


def show():
    """ Deliver a SVG payload.
    """
    figure_manager = Gcf.get_active()
    if figure_manager is not None:
        # Make the background transparent.
        # figure_manager.canvas.figure.patch.set_alpha(0.0)
        # Set the background to white instead so it looks good on black.
        figure_manager.canvas.figure.set_facecolor('white')
        figure_manager.canvas.figure.set_edgecolor('white')
        data = svg_from_canvas(figure_manager.canvas)
        add_plot_payload('svg', data)

def svg_from_canvas(canvas):
    """ Return a string containing the SVG representation of a FigureCanvasSvg.
    """
    string_io = StringIO()
    canvas.print_svg(string_io)
    return string_io.getvalue()
