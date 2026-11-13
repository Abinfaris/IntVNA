"""IntVNA 0.1 — UI and reporting extension for NanoVNA Saver v0.7.3.

Copyright 2026 IntSensing LLC (new additions).
Derived application: NanoVNA Saver, GPL-3.0-or-later; retain upstream notices.
Launch with PYTHONPATH=src python /path/to/intvna.py from the source checkout.
"""
from __future__ import annotations

import math
import sys
from datetime import datetime
from pathlib import Path

from PySide6 import QtCore, QtWidgets
from NanoVNASaver.NanoVNASaver import NanoVNASaver

STYLESHEET = """
QWidget { background: #111b2a; color: #e9f0fa; font-size: 12px; }
QLabel { background: transparent; }
QGroupBox { background: #17263a; border: 1px solid #314761; border-radius: 9px;
            margin-top: 12px; padding: 10px 7px 7px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #8dd6ff; }
QPushButton { background: #214464; border: 1px solid #3b668a; border-radius: 7px;
              padding: 7px 10px; min-height: 17px; }
QPushButton:hover { background: #2c648e; }
QPushButton:pressed { background: #153754; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #0d1724; border: 1px solid #39516a; border-radius: 5px;
    padding: 5px; selection-background-color: #207db3; }
QScrollArea, QScrollArea > QWidget > QWidget { border: none; }
QTableWidget { gridline-color: #2b4056; background: #0d1724;
               alternate-background-color: #16283b; }
QHeaderView::section { background: #24415c; color: white; padding: 5px; border: 0; }
QTabWidget::pane { border: 1px solid #304964; }
QTabBar::tab { background: #1a3147; padding: 7px 12px; }
QTabBar::tab:selected { background: #25688f; }
QProgressBar { background: #0b1622; border: 1px solid #3d536a; border-radius: 5px; }
QProgressBar::chunk { background: #20a4c7; }
"""

COLUMNS = [
    "Frequency (Hz)", "Frequency (MHz)", "S11 real", "S11 imag",
    "S11 magnitude (dB)", "S11 phase (deg)", "S11 |Γ|",
    "Return loss (dB)", "VSWR", "Resistance (Ω)", "Reactance (Ω)",
    "Q factor", "S21 real", "S21 imag", "S21 magnitude (dB)",
    "S21 phase (deg)", "S21 |S21|",
]


def snapshot_rows(data11, data21):
    """Generate spreadsheet rows from Saver Datapoint objects; no USB calls."""
    if not data11:
        return []
    lookup21 = {int(p.freq): p for p in data21}
    rows = []
    for p in data11:
        freq = int(p.freq)
        q = lookup21.get(freq)
        g = complex(p.re, p.im)
        mag = abs(g)
        gain = 20 * math.log10(mag) if mag else -math.inf
        vswr = (1 + mag) / (1 - mag) if mag < 1 else math.inf
        z = (50 * (1 + g) / (1 - g)) if abs(1 - g) > 1e-12 else complex(math.inf, math.inf)
        quality = abs(z.imag / z.real) if z.real and math.isfinite(z.real) else math.inf
        if q is not None:
            t = complex(q.re, q.im)
            gain21 = 20 * math.log10(abs(t)) if abs(t) else -math.inf
            phase21 = math.degrees(math.atan2(t.imag, t.real))
            real21, imag21, mag21 = t.real, t.imag, abs(t)
        else:
            real21 = imag21 = gain21 = phase21 = mag21 = None
        rows.append([
            freq, freq / 1e6, p.re, p.im, gain,
            math.degrees(math.atan2(g.imag, g.real)), mag,
            -gain if math.isfinite(gain) else math.inf,
            vswr, z.real, z.imag, quality,
            real21, imag21, gain21, phase21, mag21,
        ])
    return rows


def safe_value(value):
    """Excel has no representation for infinities or NaNs."""
    if value is None:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return "∞" if value > 0 else "−∞" if value < 0 else "NaN"
    return value


def write_excel(path, rows, source, calibration_note):
    import xlsxwriter
    workbook = xlsxwriter.Workbook(str(path))
    title_format = workbook.add_format({"bold": True, "font_size": 18, "font_color": "#134F79"})
    header = workbook.add_format({"bold": True, "bg_color": "#153D60", "font_color": "#FFFFFF", "border": 0})
    numeric = workbook.add_format({"num_format": "0.000000"})
    summary = workbook.add_worksheet("Summary")
    summary.set_column("A:A", 28)
    summary.set_column("B:B", 54)
    summary.write("A1", "IntVNA | RF Measurement Report", title_format)
    fields = [
        ("Created", datetime.now().astimezone().isoformat(timespec="seconds")),
        ("Application", "IntVNA 0.1 / NanoVNA Saver v0.7.3"),
        ("Source", source or "Current sweep"),
        ("Points", len(rows)),
        ("Start frequency (Hz)", rows[0][0]),
        ("Stop frequency (Hz)", rows[-1][0]),
        ("Calibration", calibration_note),
        ("Reference impedance (Ω)", 50),
        ("Note", "S11 return loss is -20 log10(|S11|). Non-finite values are text."),
    ]
    for i, (key, value) in enumerate(fields, start=3):
        summary.write(i, 0, key, header)
        summary.write(i, 1, value)
    ws = workbook.add_worksheet("Measurement Data")
    ws.freeze_panes(1, 2)
    ws.autofilter(0, 0, len(rows), len(COLUMNS) - 1)
    ws.set_column(0, 0, 19)
    ws.set_column(1, len(COLUMNS) - 1, 19)
    for col, name in enumerate(COLUMNS):
        ws.write(0, col, name, header)
    for r, row in enumerate(rows, start=1):
        for c, val in enumerate(row):
            val = safe_value(val)
            if val is None:
                continue
            if isinstance(val, (float, int)):
                ws.write_number(r, c, val, numeric if c else None)
            else:
                ws.write_string(r, c, str(val))
    chart = workbook.add_chart({"type": "scatter", "subtype": "straight"})
    for col, label in [(4, "S11 (dB)"), (14, "S21 (dB)")]:
        chart.add_series({"name": label,
                          "categories": ["Measurement Data", 1, 1, len(rows), 1],
                          "values": ["Measurement Data", 1, col, len(rows), col]})
    chart.set_title({"name": "Frequency Response"})
    chart.set_x_axis({"name": "Frequency (MHz)"})
    chart.set_y_axis({"name": "Magnitude (dB)"})
    summary.insert_chart("A16", chart, {"x_scale": 1.7, "y_scale": 1.4})
    workbook.close()


class IntVNA(NanoVNASaver):
    def __init__(self):
        super().__init__()
        self.baseTitle = "IntVNA 0.1 | powered by NanoVNA Saver"
        self.updateTitle()
        self._result_window = None
        # Keep all NanoVNA Saver widgets and all existing measurement functions.
        panel = QtWidgets.QGroupBox("IntVNA Workspace")
        panel_layout = QtWidgets.QVBoxLayout(panel)
        description = QtWidgets.QLabel("Professional results • live table • Excel export")
        description.setWordWrap(True)
        panel_layout.addWidget(description)
        view = QtWidgets.QPushButton("Open results table")
        save = QtWidgets.QPushButton("Export current sweep to Excel")
        view.clicked.connect(self.show_results)
        save.clicked.connect(self.export_excel)
        panel_layout.addWidget(view)
        panel_layout.addWidget(save)
        # Main UI's left control column is the first item in the internal outer row.
        content = self.layout().itemAt(0).widget().widget()
        row_layout = content.layout()
        left = row_layout.itemAt(0).layout()
        left.insertWidget(0, panel)
        self.communicate.data_available.connect(self.update_results_window)

    def capture(self):
        # Always copy data under Saver's lock; never query the USB device here.
        with self.dataLock:
            d11 = list(self.data.s11)
            d21 = list(self.data.s21)
        return snapshot_rows(d11, d21)

    def calibration_status(self):
        # Avoid claiming calibration status without a verified flag from Saver.
        return "Check NanoVNA Saver calibration window; status not independently verified"

    def export_excel(self):
        rows = self.capture()
        if not rows:
            QtWidgets.QMessageBox.information(self, "No sweep", "Acquire or load a sweep before exporting.")
            return
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export IntVNA measurement", "IntVNA_measurement.xlsx", "Excel (*.xlsx)"
        )
        if not filename:
            return
        if not filename.lower().endswith(".xlsx"):
            filename += ".xlsx"
        try:
            write_excel(Path(filename), rows, self.sweepSource, self.calibration_status())
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Export failed", str(exc))
            return
        QtWidgets.QMessageBox.information(self, "Saved", f"Exported {len(rows)} rows to:\n{filename}")

    def show_results(self):
        if self._result_window is None:
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle("IntVNA | Complete measurement results")
            dialog.resize(1200, 650)
            layout = QtWidgets.QVBoxLayout(dialog)
            label = QtWidgets.QLabel("S11 / S21 data from the current NanoVNA Saver sweep")
            table = QtWidgets.QTableWidget(0, len(COLUMNS))
            table.setHorizontalHeaderLabels(COLUMNS)
            table.setAlternatingRowColors(True)
            table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setSortingEnabled(False)
            controls = QtWidgets.QHBoxLayout()
            export = QtWidgets.QPushButton("Export Excel")
            export.clicked.connect(self.export_excel)
            controls.addWidget(export)
            controls.addStretch(1)
            layout.addWidget(label)
            layout.addWidget(table)
            layout.addLayout(controls)
            self._result_window = dialog
            self._result_table = table
        self.update_results_window()
        self._result_window.show()
        self._result_window.raise_()

    def update_results_window(self):
        if self._result_window is None or not self._result_window.isVisible():
            return
        rows = self.capture()
        table = self._result_table
        table.setUpdatesEnabled(False)
        try:
            table.setRowCount(len(rows))
            for r, values in enumerate(rows):
                for c, value in enumerate(values):
                    v = safe_value(value)
                    label = "" if v is None else f"{v:.6g}" if isinstance(v, float) else str(v)
                    table.setItem(r, c, QtWidgets.QTableWidgetItem(label))
        finally:
            table.setUpdatesEnabled(True)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    window = IntVNA()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
