"""Native Qt application bootstrap (placeholder, not the real GUI)."""

import sys

from PySide6.QtWidgets import QApplication

from everlong_stk.gui.main_window import MainWindow


def run_gui() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
