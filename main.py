"""
chartBuilder — entry point.

Launches the PyQt6 application with Fusion style (flat base) and
the centralised chartBuilder stylesheet.

Dark-mode note
--------------
The QSS in ui/palette.py sets explicit background-color and color on
every widget selector — including QAbstractItemView (dropdown lists,
list/tree/table views) and QToolTip — so Fusion never falls back to
the OS dark palette for surfaces the stylesheet owns.
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow
from ui.palette import APP_STYLESHEET


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("chartBuilder")
    app.setStyle("Fusion")          # flat base; QSS overrides gradients
    app.setStyleSheet(APP_STYLESHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
