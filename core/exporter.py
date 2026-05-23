"""
Chart export utilities.

Exports matplotlib figures to high-resolution PNG files.
Default DPI is 300 for print-quality output.
"""

import matplotlib.pyplot as plt
from pathlib import Path


class Exporter:
    """Handles export of charts to disk."""

    def export_figure(self, fig: plt.Figure, file_path: str, dpi: int = 300) -> None:
        """
        Save a matplotlib Figure to a PNG file.

        Parameters
        ----------
        fig       : The figure to export.
        file_path : Destination path (will create parent directories if needed).
        dpi       : Resolution in dots per inch.  Defaults to 300 (print quality).
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor='white')
