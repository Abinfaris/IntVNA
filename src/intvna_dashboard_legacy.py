"""IntVNA dashboard prototype; requires IntVNA 0.3 source and NanoVNA Saver.
GPL-3.0-or-later derivative; preserve NanoVNA Saver copyright notices.
"""
import sys
import numpy as np
from PySide6 import QtWidgets as W, QtCore as C, QtGui as G
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from intvna_plus import IntVNAPlus, PALETTE

STYLE = """
QWidget {background:#F4F7FC; color:#1B3148; font-family:'Helvetica Neue',Arial; font-size:12px;}
QFrame#card {background:white; border:1px solid #DFE7F1; border-radius:12px;}
QLabel#kpi {font-size:24px; font-weight:700; color:#144E84;}
QLabel#cardTitle {font-size:12px; color:#60758B;}
QPushButton {background:#E7F0FC; color:#154C78; border:1px solid #C5D8EC; border-radius:7px; padding:9px 12px; font-size:12px; font-weight:600;}
QPushButton:hover {background:#D4E7FA;}
QPushButton#primary {background:#176DB2; color:white; border:0;}
QLabel#subtitle {color:#63788F; font-size:12px;}
"""

class Dashboard(W.QMainWindow):
    def __init__(self, engine):
        super().__init__()
        self.engine=engine
        self.setWindowTitle('IntVNA | RF Measurement Dashboard')
        self.resize(1480,940)
        root=W.QWidget(); self.setCentralWidget(root)
        main=W.QVBoxLayout(root); main.setContentsMargins(20,15,20,15); main.setSpacing(12)
        top=W.QHBoxLayout()
        branding=W.QVBoxLayout()
        title=W.QLabel('IntVNA'); title.setStyleSheet('font-size:30px;font-weight:800;color:#13538D;')
        sub=W.QLabel('RF Measurement Dashboard  •  IntSensing LLC'); sub.setObjectName('subtitle')
        branding.addWidget(title);branding.addWidget(sub)
        top.addLayout(branding);top.addStretch()
        for text,action,primary in [
            ('Full results + TDR',self.open_results,False),
            ('Export Excel',self.export_excel,True),
            ('Instrument settings',self.show_controls,False),
        ]:
            b=W.QPushButton(text); b.clicked.connect(action)
            if primary:b.setObjectName('primary')
            top.addWidget(b)
        main.addLayout(top)
        krow=W.QHBoxLayout(); self.metrics={}
        for key,label in [('freq','Frequency sweep'),('s11','S11 @ center'),('s21','S21 @ center'),('vswr','VSWR @ center'),('points','Measurement points')]:
            frame=W.QFrame();frame.setObjectName('card');
            v=W.QVBoxLayout(frame); v.setContentsMargins(15,12,15,12)
            t=W.QLabel(label);t.setObjectName('cardTitle')
            number=W.QLabel('—');number.setObjectName('kpi')
            v.addWidget(t);v.addWidget(number)
            self.metrics[key]=number;krow.addWidget(frame,1)
        main.addLayout(krow)
        self.fig=Figure(figsize=(12,7),dpi=100,facecolor='#FFFFFF',layout='constrained')
        self.axes=self.fig.subplots(2,2)
        self.canvas=FigureCanvasQTAgg(self.fig)
        panel=W.QFrame();panel.setObjectName('card');p=W.QVBoxLayout(panel)
        p.addWidget(self.canvas);main.addWidget(panel,1)
        self.status=W.QLabel('Ready. Use Instrument settings to connect or configure your NanoVNA.');self.status.setObjectName('subtitle')
        main.addWidget(self.status)
        self.timer=C.QTimer(self);self.timer.setInterval(1800);self.timer.timeout.connect(self.refresh);self.timer.start()
        self.refresh()
    def show_controls(self):
        self.engine.show();self.engine.raise_();self.engine.activateWindow()
    def open_results(self):
        self.engine.show_results()
    def export_excel(self):
        self.engine.export_excel()
    def refresh(self):
        try:rows=self.engine.capture()
        except Exception as exc:
            self.status.setText(f'Measurement temporarily unavailable: {exc}');return
        if not rows:
            self.status.setText('No sweep yet. Open Instrument settings and connect/acquire or import measurements.')
            return
        f=np.array([float(r[1]) for r in rows]);s11=np.array([complex(r[2],r[3]) for r in rows]);
        s21=np.array([complex(r[12],r[13]) if r[12] is not None else np.nan+1j*np.nan for r in rows])
        z=np.divide(50*(1+s11),1-s11,out=np.full(s11.shape,np.nan+1j*np.nan),where=np.abs(1-s11)>1e-12)
        center=len(rows)//2
        g=abs(s11[center]);vswr=(1+g)/(1-g) if g<1 else np.inf
        self.metrics['freq'].setText(f'{f[0]:.1f}–{f[-1]:.1f} MHz')
        self.metrics['s11'].setText(f'{20*np.log10(max(g,1e-12)):.2f} dB')
        self.metrics['s21'].setText(f'{20*np.log10(max(abs(s21[center]),1e-12)):.2f} dB')
        self.metrics['vswr'].setText(f'{vswr:.2f}' if np.isfinite(vswr) else '∞')
        self.metrics['points'].setText(str(len(rows)))
        ax1,ax2,ax3,ax4=self.axes.flat
        for ax in self.axes.flat:
            ax.clear();ax.set_facecolor('#FFFFFF');ax.grid(True,color='#E4ECF4',linewidth=.7)
            ax.tick_params(labelsize=9,colors='#34506B')
            for spine in ax.spines.values():spine.set_color('#D5E0EB')
        ax1.plot(f,20*np.log10(np.maximum(np.abs(s11),1e-12)),color='#2265D4',lw=2.2)
        ax1.set(title='S11 | Reflection',xlabel='Frequency (MHz)',ylabel='Magnitude (dB)')
        ax2.plot(f,20*np.log10(np.maximum(np.abs(s21),1e-12)),color='#0D96AE',lw=2.2)
        ax2.set(title='S21 | Transmission',xlabel='Frequency (MHz)',ylabel='Magnitude (dB)')
        ax3.plot(f,z.real,color='#2265D4',lw=2,label='Resistance')
        ax3.plot(f,z.imag,color='#E58A21',lw=2,label='Reactance')
        ax3.set(title='Complex impedance | 50 Ω reference',xlabel='Frequency (MHz)',ylabel='Impedance (Ω)')
        ax3.legend(loc='best',fontsize=8,frameon=False)
        theta=np.linspace(0,2*np.pi,250)
        ax4.plot(np.cos(theta),np.sin(theta),color='#AABDD0',lw=1)
        ax4.axhline(0,color='#DCE6EF',lw=.7);ax4.axvline(0,color='#DCE6EF',lw=.7)
        for r in [.25,.5,.75]:ax4.plot(r*np.cos(theta),r*np.sin(theta),color='#E0E9F2',lw=.7)
        ax4.plot(s11.real,s11.imag,color='#8256C8',lw=2.2)
        ax4.set(title='S11 | Reflection coefficient plane',xlabel='Real Γ (dimensionless)',ylabel='Imag Γ (dimensionless)',xlim=(-1.1,1.1),ylim=(-1.1,1.1))
        ax4.set_aspect('equal',adjustable='box')
        for ax in self.axes.flat:
            ax.title.set_fontsize(12);ax.title.set_fontweight('bold');ax.title.set_color('#21435F')
            ax.xaxis.label.set_fontsize(10);ax.yaxis.label.set_fontsize(10)
        self.canvas.draw_idle()
        self.status.setText(f'Latest displayed sweep: {len(rows)} points • {f[0]:.3f}–{f[-1]:.3f} MHz • Calibration: verify in Instrument settings')
    def closeEvent(self,event):
        self.timer.stop();self.engine.close();event.accept()

def main():
    app=W.QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE)
    app.setFont(G.QFont('Helvetica Neue',10))
    engine=IntVNAPlus()
    engine.baseTitle = 'IntVNA | Advanced Instrument Controls'
    engine.updateTitle()
    dashboard=Dashboard(engine);dashboard.show()
    sys.exit(app.exec())
if __name__=='__main__': main()
