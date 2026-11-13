IntVNA
NanoVNA measurements and Excel reporting
Developed by Dr. Abdulrahman Binfaris

IntVNA is a personal open-source desktop project for working with NanoVNA vector network analyzers. It brings the sweep, dashboard, results table, and Excel report into one workflow.

Run a sweep, see the results, and export them directly to Excel. IntVNA calculates return loss, VSWR, resistance, reactance, and Q factor at each measured frequency. You don’t need a separate calculator or spreadsheet formulas.

Dashboard


<img width="1892" height="965" alt="intvna-dashboard" src="https://github.com/user-attachments/assets/b28ea110-9044-4e68-949a-fabef7cbe7bb" />


Example sweep from 200 to 300 MHz. The dashboard shows four plots alongside controls for instrument settings, the results table, and Excel export.

What you can do
- Run a frequency sweep. Connect a NanoVNA over USB and set the sweep using start and stop frequencies or center frequency and span.
- View the RF response. Use the four-panel dashboard to inspect reflection (S11), forward transmission (S21), impedance, and other supported views such as phase and VSWR.
- Access calibration controls. Open Instrument settings to use the NanoVNA Saver calibration tools for your measurement setup.
- Read exact values. Select Open Results Table to see the numeric results at each measured frequency without estimating them from a graph.
- Export a report. Select Export Excel to save the current sweep as a standard .xlsx workbook.

What you get in Excel
The workbook contains two sheets.
- Summary records the sweep range, point count, measurement source, export time, and reference impedance. It also includes an S11/S21 magnitude chart and a calibration note. Verify calibration in Instrument settings.
- Measurement Data contains one row per measured frequency and 17 result columns. The RF calculations are saved as values, so the results are ready to review, filter, or plot.


The Excel file exports the full Results Table for the current sweep. It does not export every dashboard plot.
Sample Excel report

(https://github.com/user-attachments/files/34817255/IntVNA_measurement_10.xlsx) and select Download on its GitHub file page.

The sample contains a 101-point sweep from 200 to 300 MHz. You can inspect the workbook without installing IntVNA or connecting a NanoVNA.

Download

Open the repository’s Releases section. If the Intel Mac beta has been published, download IntVNA-macOS-Intel.zip from Assets. Extract the ZIP and open IntVNA.app.

The packaged beta described here is for Intel macOS. It is not a native Apple Silicon build or a Windows installer. The source includes scripts for building on macOS and Windows.

Quick start
1. Connect your NanoVNA to your computer with a USB data cable and open IntVNA.
2. Click Instrument settings, select the instrument’s serial port, and connect.
3. Set the sweep range and verify calibration for your test setup.
4. Click Sweep and review the dashboard when the measurement completes.
5. Click Open Results Table to inspect the values or Export Excel to save the report.

Build from source
Install Python 3.12 and Git, then run the script for your platform from the repository root. The scripts use NanoVNA Saver v0.7.3 as the measurement engine.

macOS
bash scripts/build_mac.sh
open dist/IntVNA.app

Windows x64 (PowerShell)
.\scripts\build_windows.ps1
.\dist\IntVNA\IntVNA.exe

Both scripts put their packaged ZIP in releases/. The Windows script produces a ZIP containing the app folder, not a Windows installer. Build scripts are provided for testing and do not imply that every OS and instrument combination has been validated.

Feedback
Use Issues to report a bug or suggest an improvement. For a bug report, include your IntVNA build, operating system, NanoVNA model, and the steps that reproduce it.

License and credits
IntVNA is a personal project developed by Dr. Abdulrahman Binfaris. It builds on NanoVNA Saver and retains attribution to the upstream developers and contributors. See [LICENSE.txt](LICENSE.txt) for the GNU General Public License v3.
