"""
chartBuilder — entry point.

Launches the PyQt6 application with Fusion style (flat base) and
the centralised chartBuilder stylesheet.

Theme handling
--------------
Two stylesheets live in ui/palette.py — APP_STYLESHEET (light) and
APP_DARK_STYLESHEET (dark).  On startup the correct one is chosen based
on the OS appearance.  If the OS switches while the app is running,
_apply_theme() is re-called via the colorSchemeChanged signal (Qt ≥ 6.5)
so the transition is seamless without a restart.
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow
from ui.palette import APP_STYLESHEET, APP_DARK_STYLESHEET


def _is_dark(app: QApplication) -> bool:
    """Return True when the OS is currently in dark mode."""
    try:
        # Qt 6.5+ — authoritative, works on all platforms
        scheme = app.styleHints().colorScheme()
        return scheme == Qt.ColorScheme.Dark
    except AttributeError:
        # Fallback for Qt < 6.5: measure the window-background lightness
        from PyQt6.QtGui import QPalette
        lum = app.palette().color(QPalette.ColorRole.Window).lightness()
        return lum < 128


def _apply_theme(app: QApplication) -> None:
    """Apply the light or dark stylesheet to match the current OS appearance."""
    app.setStyleSheet(APP_DARK_STYLESHEET if _is_dark(app) else APP_STYLESHEET)


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("chartBuilder")
    app.setStyle("Fusion")   # flat base; stylesheets override gradients

    # Apply the theme that matches the current OS appearance
    _apply_theme(app)

    # Re-apply whenever the OS toggles dark / light mode at runtime
    try:
        app.styleHints().colorSchemeChanged.connect(lambda: _apply_theme(app))
    except AttributeError:
        pass   # colorSchemeChanged not available on Qt < 6.5

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
