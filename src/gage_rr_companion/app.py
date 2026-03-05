import json
import sys
from typing import Any, Dict

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
)

from .compute import ComputeGageRR
from .gage_rr_io import load_gage_rr_data


def dataframe_to_tablewidget(df: pd.DataFrame) -> QTableWidget:
    """Convert a pandas DataFrame into a read-only QTableWidget."""
    table = QTableWidget()
    table.setRowCount(len(df))
    table.setColumnCount(len(df.columns))
    table.setHorizontalHeaderLabels([str(c) for c in df.columns])

    for r in range(len(df)):
        for c in range(len(df.columns)):
            val = df.iat[r, c]
            item = QTableWidgetItem("" if pd.isna(val) else str(val))
            # read-only
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(r, c, item)

    table.resizeColumnsToContents()
    table.resizeRowsToContents()
    return table


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Gage R&R Companion")
        self.setMinimumSize(900, 600)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        # Top bar
        top = QHBoxLayout()
        layout.addLayout(top)

        self.status_label = QLabel("Upload your Gage R&R data (CSV format)")
        top.addWidget(self.status_label)

        self.upload_btn = QPushButton("Choose CSV…")
        self.upload_btn.clicked.connect(self.choose_csv)
        top.addWidget(self.upload_btn)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.tab_anova = QWidget()
        self.tab_var = QWidget()
        self.tab_grr = QWidget()
        self.tab_ops = QWidget()
        self.tab_summary = QWidget()

        self.tabs.addTab(self.tab_anova, "ANOVA Table")
        self.tabs.addTab(self.tab_var, "Variance Components")
        self.tabs.addTab(self.tab_grr, "Gage R&R Table")
        self.tabs.addTab(self.tab_ops, "Operator Statistics")
        self.tabs.addTab(self.tab_summary, "Summary Metrics")

        self._init_table_tab(self.tab_anova)
        self._init_table_tab(self.tab_var)
        self._init_table_tab(self.tab_grr)
        self._init_table_tab(self.tab_ops)
        self._init_summary_tab(self.tab_summary)

        self.summary_text: QTextEdit = self.tab_summary.findChild(QTextEdit)

    def _init_table_tab(self, tab: QWidget) -> None:
        lay = QVBoxLayout(tab)
        placeholder = QLabel("No data loaded yet.")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(placeholder)

    def _init_summary_tab(self, tab: QWidget) -> None:
        lay = QVBoxLayout(tab)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlaceholderText("Summary metrics will appear here.")
        lay.addWidget(txt)

    def choose_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Gage R&R CSV",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return

        try:
            df = load_gage_rr_data(path, is_path=True)
            results: Dict[str, Any] = ComputeGageRR(df)

            self.status_label.setText(f"Loaded: {path}")
            self.populate_results(results)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load or compute results.\n\n{e}",
            )

    def _set_table_tab(self, tab: QWidget, df: pd.DataFrame) -> None:
        lay = tab.layout()
        # Clear existing widgets
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        lay.addWidget(dataframe_to_tablewidget(df))

    def populate_results(self, results: Dict[str, Any]) -> None:
        self._set_table_tab(self.tab_anova, results["anova_table"])
        self._set_table_tab(self.tab_var, results["variance_components"])
        self._set_table_tab(self.tab_grr, results["gage_rr_table"])
        self._set_table_tab(self.tab_ops, results["operator_stats"])

        summary = results.get("summary_metrics", {})
        self.summary_text.setPlainText(json.dumps(summary, indent=2))


def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()