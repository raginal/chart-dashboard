"""
chartBuilder — entry point.

Launches the PyQt6 application with Fusion style (flat base) and
the centralised chartBuilder stylesheet.

Dark-mode note
--------------
An explicit light QPalette is applied before the stylesheet so that
Fusion never inherits the system dark-mode colours.  The QSS covers
most surfaces, but Fusion also uses the palette directly for widget
parts it renders natively (dropdown popup lists, disabled text, focus
rings, scroll-bar handles, etc.).  Setting the palette here makes all
of those consistently light regardless of the OS appearance setting.
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow
from ui.palette import APP_STYLESHEET


def _make_light_palette() -> QPalette:
    """
    Return a fully explicit light-mode QPalette using the app's colour tokens.

    Every colour group (Active, Inactive, Disabled) is set explicitly so that
    Fusion never falls back to the OS dark palette for any widget state.
    """
    # Colour tokens (mirrors ui/palette.py constants)
    WHITE        = QColor("#FFFFFF")
    GREY_50      = QColor("#F8FAFC")   # page / panel background
    GREY_100     = QColor("#F1F5F9")   # subtle element backgrounds
    GREY_200     = QColor("#E2E8F0")   # borders / dividers
    GREY_400     = QColor("#94A3B8")   # placeholder / disabled text
    GREY_500     = QColor("#64748B")   # secondary text
    GREY_700     = QColor("#334155")   # primary text
    GREY_900     = QColor("#0F172A")   # near-black headings
    PRIMARY      = QColor("#2563EB")   # highlight / selection
    PRIMARY_TEXT = QColor("#FFFFFF")   # text on primary background

    palette = QPalette()

    # ── Apply to all three colour groups first, then override Disabled ────────
    for group in (
        QPalette.ColorGroup.Active,
        QPalette.ColorGroup.Inactive,
        QPalette.ColorGroup.Disabled,
    ):
        palette.setColor(group, QPalette.ColorRole.Window,          GREY_50)
        palette.setColor(group, QPalette.ColorRole.WindowText,      GREY_700)
        palette.setColor(group, QPalette.ColorRole.Base,            WHITE)
        palette.setColor(group, QPalette.ColorRole.AlternateBase,   GREY_100)
        palette.setColor(group, QPalette.ColorRole.ToolTipBase,     WHITE)
        palette.setColor(group, QPalette.ColorRole.ToolTipText,     GREY_700)
        palette.setColor(group, QPalette.ColorRole.PlaceholderText, GREY_400)
        palette.setColor(group, QPalette.ColorRole.Text,            GREY_700)
        palette.setColor(group, QPalette.ColorRole.Button,          GREY_100)
        palette.setColor(group, QPalette.ColorRole.ButtonText,      GREY_700)
        palette.setColor(group, QPalette.ColorRole.BrightText,      GREY_900)
        palette.setColor(group, QPalette.ColorRole.Link,            PRIMARY)
        palette.setColor(group, QPalette.ColorRole.Highlight,       PRIMARY)
        palette.setColor(group, QPalette.ColorRole.HighlightedText, PRIMARY_TEXT)
        # Shading roles used by Fusion for borders, shadows, bevels
        palette.setColor(group, QPalette.ColorRole.Light,           WHITE)
        palette.setColor(group, QPalette.ColorRole.Midlight,        GREY_100)
        palette.setColor(group, QPalette.ColorRole.Mid,             GREY_200)
        palette.setColor(group, QPalette.ColorRole.Dark,            GREY_200)
        palette.setColor(group, QPalette.ColorRole.Shadow,          GREY_400)

    # ── Disabled overrides — greyed-out text, muted highlight ─────────────────
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, GREY_400)

    palette.setColor(QPalette.ColorGroup.Disabled,
                     QPalette.ColorRole.Highlight,       GREY_200)
    palette.setColor(QPalette.ColorGroup.Disabled,
                     QPalette.ColorRole.HighlightedText, GREY_500)

    return palette


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("chartBuilder")
    app.setStyle("Fusion")               # flat base; QSS overrides gradients
    app.setPalette(_make_light_palette()) # pin to light regardless of OS mode
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
