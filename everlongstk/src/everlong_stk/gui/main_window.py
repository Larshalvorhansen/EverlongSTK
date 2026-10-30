"""Three-tab scaffold; the HTML mockup remains the detailed UI reference."""

from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """Bootstrap-only window; no simulated state or fake physics is connected."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("EverlongSTK — GUI scaffold")
        self.resize(1200, 800)
        tabs = QTabWidget()
        tabs.addTab(self._configuration_page(), "Configuration")
        tabs.addTab(self._simple_page("Simulation", "Map, playback and live statistics"), "Simulation")
        tabs.addTab(self._simple_page("Results", "Plots, reports and exports"), "Results")
        self.setCentralWidget(tabs)
        self.statusBar().showMessage("Scaffold only — no simulation engine is implemented")

    def _configuration_page(self) -> QScrollArea:
        content = QWidget()
        layout = QVBoxLayout(content)
        for section in (
            "1. Orbit parameters",
            "2. Satellite states and state diagram",
            "3. Satellite components",
        ):
            layout.addWidget(QLabel(section))
        layout.addStretch()
        return self._scrollable(content)

    def _simple_page(self, heading: str, description: str) -> QScrollArea:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.addWidget(QLabel(heading))
        layout.addWidget(QLabel(f"Planned: {description}"))
        layout.addStretch()
        return self._scrollable(content)

    @staticmethod
    def _scrollable(content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        return scroll
