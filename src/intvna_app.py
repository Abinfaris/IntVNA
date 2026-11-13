"""IntVNA 0.4.0-beta — cross-platform test launcher.

Developed by Dr. Abdulrahman Binfaris | IntSensing LLC
Uses NanoVNA Saver as the underlying measurement engine (GPLv3).
This is a beta candidate, not a validated calibrated instrument.
"""
import sys
import math
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets as QtW
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from intvna import IntVNA as SaverEngine, COLUMNS

THEME = """
QWidget { background:#f4f7fc; color:#20364b; font-family:Arial; font-size:12px; }
QFrame#card { background:#ffffff; border:1px solid #dce5f0; border-radius:9px; }
QLabel#metric { font-size:19px; font-weight:bold; color:#195c92; }
QPushButton { background:#e3eefb; color:#174b73; border:1px solid #b9d1e7;
 border-radius:6px; padding:6px 11px; min-height:22px; }
QPushButton:disabled { color:#63778a; background:#edf1f5; }
QPushButton:hover { background:#d1e5f7; }
QHeaderView::section { background:#dfecf9; color:#23435e; padding:6px; }
QTableWidget { background:white; alternate-background-color:#f2f6fb; }
"""

class Dashboard(QtW.QMainWindow):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.setWindowTitle("IntVNA | RF Dashboard")
        self.resize(1390, 930)
        root = QtW.QWidget()
        self.setCentralWidget(root)
        layout = QtW.QVBoxLayout(root)
        layout.setContentsMargins(15,12,15,12)
        top = QtW.QHBoxLayout()
        name = QtW.QLabel("IntVNA")
        name.setStyleSheet("font-size:28px; font-weight:700; color:#195c92")
        top.addWidget(name)
        top.addWidget(QtW.QLabel("  Developed by Dr. Abdulrahman Binfaris"))
        top.addStretch()
        for label, cb in [("Instrument settings", self.show_controls),
                          ("Open Results Table", self.engine.show_results),
                          ("Export Excel", self.engine.export_excel)]:
            button=QtW.QPushButton(label);button.clicked.connect(cb);top.addWidget(button)
        layout.addLayout(top)
        summary=QtW.QHBoxLayout(); self.cards={}
        for key,label in [("range","Sweep frequency"),("s11","S11 midpoint"),
                          ("s21","S21 midpoint"),("vswr","VSWR midpoint"),("n","Points")]:
            card=QtW.QFrame();card.setObjectName("card")
            box=QtW.QVBoxLayout(card)
            box.addWidget(QtW.QLabel(label))
            value=QtW.QLabel("—");value.setObjectName("metric")
            box.addWidget(value);self.cards[key]=value;summary.addWidget(card,1)
        layout.addLayout(summary)
        self.figure=Figure(figsize=(12,7),dpi=100,facecolor="white",layout="constrained")
        self.axes=self.figure.subplots(2,2)
        self.canvas=FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas,1)
        self.status=QtW.QLabel("No sweep loaded. Use Instrument settings to connect or load measurements.")
        layout.addWidget(self.status)
        self.timer=QtCore.QTimer(self)
        self.timer.setInterval(1300)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.refresh()

    def show_controls(self):
        self.engine.show();self.engine.raise_();self.engine.activateWindow()

    def refresh(self):
        try:
            rows=self.engine.capture()
        except Exception as e:
            self.status.setText("Waiting for instrument: " + str(e))
            return
        if not rows: return
        f=np.array([float(r[1]) for r in rows]);
        if len(f)==0:return
        a=np.array([complex(r[2],r[3]) for r in rows]);
        b=np.array([complex(r[12],r[13]) if r[12] is not None else np.nan+1j*np.nan for r in rows])
        z=np.divide(50*(1+a),1-a,out=np.full(a.shape,np.nan+1j*np.nan),where=np.abs(1-a)>1e-9)
        i=len(rows)//2;g=abs(a[i]);v=(1+g)/(1-g) if g<1 else float('inf')
        if f[-1]<1:
            self.cards['range'].setText(f"{f[0]*1000:.2f}–{f[-1]*1000:.2f} kHz")
        else:
            self.cards['range'].setText(f"{f[0]:.3f}–{f[-1]:.3f} MHz")
        self.cards['s11'].setText(f"{20*np.log10(max(g,1e-12)):.2f} dB")
        self.cards['s21'].setText(f"{20*np.log10(max(abs(b[i]),1e-12)):.2f} dB")
        self.cards['vswr'].setText(f"{v:.2f}" if math.isfinite(v) else "∞")
        self.cards['n'].setText(str(len(rows)))
        for ax in self.axes.flat:
            ax.clear();ax.set_aspect('auto');ax.set_facecolor('white')
            ax.grid(True,color='#e1e9f1',linewidth=.7)
            ax.tick_params(labelsize=8)
        a1,a2,a3,a4=self.axes.flat
        a1.plot(f,20*np.log10(np.maximum(np.abs(a),1e-12)),color='#2563eb',lw=2)
        a1.set(title='S11 | Reflection',xlabel='Frequency (MHz)',ylabel='Magnitude (dB)')
        a2.plot(f,20*np.log10(np.maximum(np.abs(b),1e-12)),color='#0891b2',lw=2)
        a2.set(title='S21 | Transmission',xlabel='Frequency (MHz)',ylabel='Magnitude (dB)')
        # Avoid displaying numerical explosions when Gamma approaches 1.
        real=np.where(np.abs(z.real)<1e6,z.real,np.nan)
        imag=np.where(np.abs(z.imag)<1e6,z.imag,np.nan)
        a3.plot(f,real,label='R',color='#2563eb',lw=1.8)
        a3.plot(f,imag,label='X',color='#d97706',lw=1.8)
        a3.legend(loc='upper right',fontsize=8)
        a3.set(title='Complex impedance (50 Ω reference)',xlabel='Frequency (MHz)',ylabel='Impedance (Ω)')
        circle=np.linspace(0,2*np.pi,360)
        for radius in [.25,.5,.75,1]:
            a4.plot(radius*np.cos(circle),radius*np.sin(circle),color='#dce4ed',lw=.75)
        a4.axhline(0,color='#dce4ed',lw=.75);a4.axvline(0,color='#dce4ed',lw=.75)
        a4.plot(a.real,a.imag,color='#7c3aed',lw=2)
        a4.set(title='S11 | Complex reflection plane',xlabel='Real Γ',ylabel='Imag Γ',xlim=(-1.1,1.1),ylim=(-1.1,1.1))
        a4.set_aspect('equal',adjustable='box')
        for ax in self.axes.flat:
            ax.title.set_fontsize(11);ax.title.set_fontweight('bold')
            ax.xaxis.label.set_fontsize(9);ax.yaxis.label.set_fontsize(9)
        self.canvas.draw_idle()
        self.status.setText(f"{len(rows)} points | Calibration status: verify in Instrument settings")

    def closeEvent(self,event):
        self.timer.stop()
        try:self.engine.close()
        finally:event.accept()



# INTVNA FOUR MARKERS PERMANENT
def restrict_to_four_markers(engine):
    import re
    from PySide6 import QtWidgets as W

    marker_group = getattr(engine, "marker_control", None)

    if marker_group is None:
        matches = [
            g for g in engine.findChildren(W.QGroupBox)
            if g.title().strip().lower() == "markers"
        ]
        marker_group = matches[0] if matches else None

    if marker_group is None:
        print("WARNING: Marker panel not located.")
        return

    hidden = set()

    def hide_marker_row(label):
        number = int(
            re.search(r"(\\d+)", label.text()).group(1)
        )
        if number <= 4:
            return

        parent = label.parentWidget()
        while parent is not None:
            layout = parent.layout()
            if layout is not None:
                if isinstance(layout, W.QFormLayout):
                    row, role = layout.getWidgetPosition(label)
                    if row >= 0:
                        layout.setRowVisible(row, False)
                        hidden.add(number)
                        return

                if isinstance(layout, W.QGridLayout):
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item.widget() is label:
                            row, _, _, _ = layout.getItemPosition(i)
                            for j in range(layout.count()):
                                other = layout.itemAt(j)
                                r, _, _, _ = layout.getItemPosition(j)
                                if r == row and other.widget():
                                    other.widget().hide()
                            hidden.add(number)
                            return

            if parent is marker_group:
                break
            parent = parent.parentWidget()

        # Fallback: hide label without touching sweep controls.
        label.hide()
        hidden.add(number)

    labels = marker_group.findChildren(W.QLabel)
    for label in labels:
        if re.fullmatch(
            r"Marker\\s*(\\d+)",
            label.text().strip(),
            re.IGNORECASE
        ):
            hide_marker_row(label)

    # Restrict any additional Marker 5+ selector widgets.
    for widget in marker_group.findChildren(W.QAbstractButton):
        match = re.fullmatch(
            r"Marker\\s*(\\d+)",
            widget.text().strip(),
            re.IGNORECASE
        )
        if match and int(match.group(1)) > 4:
            widget.hide()
            hidden.add(int(match.group(1)))

    print("IntVNA: Extra marker controls hidden:", len(hidden))
    print("Visible marker limit: 4")


# INTVNA EXACT FOUR MARKERS V2
def apply_four_marker_limit(engine):
    form = engine.marker_control.layout
    markers = engine.markers

    # Keep the first four markers.
    # Hide marker rows 5 onward.
    for i in range(4, len(markers)):
        form.setRowVisible(i, False)

        # Hide the associated measurement readout.
        markers[i].get_data_layout().hide()

    print("Total markers in engine:", len(markers))
    print("Visible marker controls:", min(4, len(markers)))
    print("Extra marker rows hidden:", max(0, len(markers)-4))


def main():
    app=QtW.QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(THEME)
    app.setFont(QtGui.QFont('Arial',10))
    # INTVNA PERMANENT FOUR MARKERS
    from NanoVNASaver.Defaults import APP_SETTINGS
    APP_SETTINGS.setValue("CHART/marker_count", 4)
    APP_SETTINGS.sync()
    print("IntVNA configured for exactly 4 markers")
    engine=SaverEngine()
    restrict_to_four_markers(engine)
    engine.baseTitle="IntVNA | Advanced Instrument Settings"
    engine.updateTitle()
    # The engine retains its original functionality and GPL attribution.
    for group in engine.findChildren(QtW.QGroupBox):
        if group.title().strip().lower()=='intvna workspace':
            group.hide()
    apply_four_marker_limit(engine)
    dashboard=Dashboard(engine)
    dashboard.show()
    return app.exec()


# INTVNA LIVE DISPLAY SYNC FIX
def _live_display_names(engine):
    """Read charts actually selected in NanoVNA Saver."""
    layout = engine.charts_layout
    result = []

    for i in range(layout.count()):
        item = layout.itemAt(i)
        widget = item.widget() if item else None
        if widget is None:
            continue

        name = getattr(widget, "name", None)
        if isinstance(name, str) and name.strip():
            row, col, _, _ = layout.getItemPosition(i)
            result.append((row, col, name.strip()))

    result.sort(key=lambda x: (x[0], x[1]))
    return [name for _, _, name in result[:4]]


_original_dashboard_refresh = Dashboard.refresh

def _synced_dashboard_refresh(self):
    _original_dashboard_refresh(self)

    choices = _live_display_names(self.engine)

    if not choices:
        self.status.setText(
            "No active graphs detected in Display setup."
        )
        return

    rows = self.engine.capture()
    if not rows:
        return

    freq = np.asarray([float(r[1]) for r in rows])
    s11 = np.asarray([
        complex(r[2], r[3]) for r in rows
    ])
    s21 = np.asarray([
        complex(r[12], r[13])
        if r[12] is not None else complex(np.nan, np.nan)
        for r in rows
    ])

    for i, ax in enumerate(self.axes.flat):
        ax.clear()
        ax.set_aspect("auto")
        ax.set_facecolor("white")
        ax.grid(True, color="#E2E8F0")

        if i >= len(choices):
            ax.set_axis_off()
            continue

        name = choices[i]
        label = name.casefold()
        data = s21 if (
            "s21" in label or "transmission" in label
        ) else s11
        mag = np.abs(data)

        ax.set_title(name, fontsize=11)
        ax.set_xlabel("Frequency (MHz)")

        if "smith" in label or "polar" in label:
            if "smith" in label:
                theta = np.linspace(0, 2*np.pi, 256)
                ax.plot(
                    np.cos(theta), np.sin(theta),
                    color="#CBD5E1"
                )
            ax.plot(
                data.real, data.imag,
                color="#2563EB", linewidth=2
            )
            ax.set_xlabel("Real")
            ax.set_ylabel("Imaginary")
            ax.set_aspect("equal", adjustable="box")

        elif "vswr" in label or "swr" in label:
            values = np.where(
                mag < 1,
                (1 + mag) / np.maximum(1 - mag, 1e-12),
                np.nan
            )
            ax.plot(freq, values, color="#0891B2")
            ax.set_ylabel("VSWR")

        elif "group delay" in label:
            if len(freq) > 1:
                phase = np.unwrap(np.angle(data))
                delay = -np.gradient(
                    phase, freq * 1e6
                ) / (2 * np.pi) * 1e9
                ax.plot(freq, delay, color="#0891B2")
            ax.set_ylabel("Group delay (ns)")

        elif "phase" in label:
            ax.plot(
                freq, np.rad2deg(np.angle(data)),
                color="#7C3AED"
            )
            ax.set_ylabel("Phase (degrees)")

        elif "real/imaginary" in label:
            ax.plot(freq, data.real, label="Real")
            ax.plot(freq, data.imag, label="Imaginary")
            ax.legend(fontsize=8)

        elif "r+jx" in label or "impedance" in label:
            z = 50 * (1 + s11) / np.where(
                np.abs(1 - s11) > 1e-12,
                1 - s11, np.nan + 0j
            )
            ax.plot(freq, z.real, label="R")
            ax.plot(freq, z.imag, label="X")
            ax.set_ylabel("Ohms")
            ax.legend(fontsize=8)

        elif "return loss" in label or "gain" in label or "logmag" in label:
            db = 20 * np.log10(
                np.maximum(mag, 1e-12)
            )
            ax.plot(freq, db, color="#2563EB")
            ax.set_ylabel("Magnitude (dB)")

        elif "magnitude" in label or "|s" in label:
            ax.plot(freq, mag, color="#2563EB")
            ax.set_ylabel("Magnitude")

        else:
            ax.text(
                0.5, 0.5,
                "Selected chart not yet implemented:\\n" + name,
                ha="center", va="center",
                transform=ax.transAxes
            )

    self.canvas.draw_idle()
    self.status.setText(
        "Dashboard synchronized: " + ", ".join(choices)
    )

Dashboard.refresh = _synced_dashboard_refresh

if __name__ == '__main__':sys.exit(main())
