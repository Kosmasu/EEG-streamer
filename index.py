import os
import sys
import time
import threading

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from brainflow.board_shim import BoardShim, BrainFlowInputParams, LogLevels, BoardIds
from brainflow import BrainFlowError
import numpy as np
import mne
from typing import Optional
from pyqttoast import Toast, ToastPreset
from pygame import mixer
import pygame

class EEGStreamApp(QMainWindow):
    toast_signal = pyqtSignal(str, str, object, int)
    epochs: Optional[mne.epochs.Epochs]
    evoked: Optional[mne.evoked]

    def __init__(self):
        super().__init__()
        self.initUI()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.eeg_data = []
        self.eeg_data_count = 0
        self.is_recording = False
        self.SAMPLING_FREQUENCY = BoardShim.get_sampling_rate(BoardIds.MUSE_2_BOARD.value)
        self.EEG_CHANNELS = BoardShim.get_eeg_channels(BoardIds.MUSE_2_BOARD.value)
        self.EEG_CHANNELS_NAME = ["TP9", "AF7", "AF8", "TP10"]

        BoardShim.enable_dev_board_logger()
        params = BrainFlowInputParams()
        params.mac_address = "00:55:da:b7:bc:5b"
        self.board = BoardShim(BoardIds.MUSE_2_BOARD.value, params)

        self.raw = None
        self.epochs = None
        self.evoked = None
        mixer.init()

    def initUI(self):
        self.setWindowTitle('EEG Streamer')

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.stacked_layout = QStackedLayout()

        self.init_recording_page()
        self.init_data_page()

        self.central_widget.setLayout(self.stacked_layout)
        self._createMenuBar()

    def _createMenuBar(self):
        menuBar = self.menuBar()

        file_menu = menuBar.addMenu('File')
        navigate_menu = menuBar.addMenu('Navigate')

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        recording_page_action = QAction('Recording Page', self)
        recording_page_action.triggered.connect(self.switch_to_recording_page)
        navigate_menu.addAction(recording_page_action)

        main_page_action = QAction('Data Page', self)
        main_page_action.triggered.connect(self.switch_to_data_page)
        navigate_menu.addAction(main_page_action)

    def switch_to_recording_page(self):
        self.stacked_layout.setCurrentWidget(self.recording_page)

    def switch_to_data_page(self):
        self.stacked_layout.setCurrentWidget(self.data_page)
        self.input_data.clear()
        for filename in os.listdir("./recordings/"):
            if not filename.endswith("_raw.fif"):
                continue
            self.input_data.addItem(filename)

    def init_recording_page(self):
        self.recording_page = QWidget()
        self.recording_page_layout = QVBoxLayout()

        # Title Segment ==========================================================
        title = QLabel("EEG Streamer")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setContentsMargins(0, 0, 0, 12)
        self.recording_page_layout.addWidget(title)

        # Form Segment ===========================================================
        formLayout = QFormLayout()
        formLayout.setHorizontalSpacing(12)
        formLayout.setLabelAlignment(Qt.AlignRight)

        self.input_duration = QLineEdit()
        self.input_duration.setValidator(QIntValidator(1, 3600))  # Only accepts integer from 1 to 3600
        formLayout.addRow("Duration (in second):", self.input_duration)

        self.input_filename = QLineEdit()
        formLayout.addRow("Filename:", self.input_filename)

        self.input_music = QComboBox()
        self.input_music.addItem("No Music")
        supported_formats = ('.mp3', '.wav')
        for music_file in [f for f in os.listdir("./musics") if f.endswith(supported_formats)]:
            self.input_music.addItem(music_file)
        formLayout.addRow("Music:", self.input_music)

        self.recording_page_layout.addLayout(formLayout)

        # Button Segment =========================================================
        buttonLayout = QVBoxLayout()

        self.button_start = QPushButton('Start Recording', self)
        self.button_start.clicked.connect(self.start_recording)
        buttonLayout.addWidget(self.button_start)

        self.button_stop = QPushButton('Stop Recording', self)
        self.button_stop.clicked.connect(self.stop_recording)
        self.button_stop.setEnabled(False)  # Disable stop button initially
        buttonLayout.addWidget(self.button_stop)

        self.recording_page_layout.addLayout(buttonLayout)

        # Graph Segment =========================================================
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)

        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.updateGeometry()
        self.recording_page_layout.addWidget(self.canvas)

        self.recording_page_layout.setStretch(0, 0)  # Title layout does not stretch
        self.recording_page_layout.setStretch(1, 0)  # Form layout does not stretch
        self.recording_page_layout.setStretch(2, 0)  # Button layout does not stretch
        self.recording_page_layout.setStretch(3, 1)  # Graph layout stretches

        self.recording_page.setLayout(self.recording_page_layout)
        self.stacked_layout.addWidget(self.recording_page)

    def init_data_page(self):
        self.data_page = QWidget()
        self.data_page_layout = QVBoxLayout()

        title = QLabel("EEG Streamer")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        title.setContentsMargins(0, 0, 0, 12)
        self.data_page_layout.addWidget(title)

        formLayout = QFormLayout()
        formLayout.setHorizontalSpacing(12)
        formLayout.setLabelAlignment(Qt.AlignRight)
        self.input_data = QComboBox()
        for filename in os.listdir("./recordings/"):
            if not filename.endswith("_raw.fif"):
                continue
            self.input_data.addItem(filename)
        self.input_data.currentTextChanged.connect(self.pick_recording)
        formLayout.addRow("Select Data:", self.input_data)

        self.label_recording_duration = QLabel("")
        formLayout.addRow("Recording Duration:", self.label_recording_duration)

        self.label_sampling_frequency = QLabel("")
        formLayout.addRow("Sampling Frequency:", self.label_sampling_frequency)

        self.label_eeg_channels = QLabel("")
        formLayout.addRow("EEG Channels:", self.label_eeg_channels)

        self.data_page_layout.addLayout(formLayout)

        self.data_page_layout.addSpacing(12)

        self.button_plot_eeg = QPushButton("Plot EEG")
        self.button_plot_eeg.clicked.connect(self.plot_eeg)
        self.data_page_layout.addWidget(self.button_plot_eeg)

        self.button_plot_headmap = QPushButton("Plot Headmap")
        self.button_plot_headmap.clicked.connect(self.plot_headmap)
        self.data_page_layout.addWidget(self.button_plot_headmap)

        self.button_plot_averaged_eeg = QPushButton("Plot Averaged EEG")
        self.button_plot_averaged_eeg.clicked.connect(self.plot_averaged_eeg)
        self.data_page_layout.addWidget(self.button_plot_averaged_eeg)

        self.button_plot_psd = QPushButton("Plot Power Spectral Density")
        self.button_plot_psd.clicked.connect(self.plot_psd)
        self.data_page_layout.addWidget(self.button_plot_psd)

        self.data_page_layout.addStretch(1)

        self.data_page.setLayout(self.data_page_layout)
        self.stacked_layout.addWidget(self.data_page)

    def create_epochs(self):
        if self.raw is None:
            self.show_toast("No Recording Available", "", ToastPreset.ERROR)
            return
        event_id = dict(recording=1)  # event trigger and conditions
        tmin = 0  # start of each epoch (200ms before the trigger)
        tmax = 1  # end of each epoch (500ms after the trigger)
        baseline = (0, 0)  # means from the first instant to t = 0
        events = mne.make_fixed_length_events(self.raw)
        self.epochs = mne.Epochs(
            self.raw,
            events,
            event_id,
            tmin=tmin,
            tmax=tmax,
            proj=True,
            picks=("eeg"),
            baseline=baseline,
            verbose=False
        )
        print("epochs", self.epochs)

    def plot_eeg(self):
        if self.raw is None:
            self.show_toast("No Recording Available", "", ToastPreset.ERROR)
            return
        self.raw.plot(scalings="auto")

    def plot_headmap(self):
        if self.raw is None:
            self.show_toast("No Recording Available", "", ToastPreset.ERROR)
            return
        self.epochs.compute_psd().plot_topomap(sensors=True, show_names=True, cmap=("jet", False), normalize=True)

    def plot_averaged_eeg(self):
        if self.raw is None:
            self.show_toast("No Recording Available", "", ToastPreset.ERROR)
            return
        self.epochs.average().plot()

    def plot_psd(self):
        if self.raw is None:
            self.show_toast("No Recording Available", "", ToastPreset.ERROR)
            return
        self.epochs.compute_psd().plot()

    def show_toast(self, title: str, message: str, preset, duration: int = 8000):
        self.toast_signal.emit(title, message, preset, duration)

    def pick_recording(self, text: str):
        print("pick recording", text)
        if text == "":
            return
        elif text.endswith("_raw.fif"):
            self.raw = mne.io.read_raw_fif(os.path.join("./recordings", self.input_data.currentText()))
            self.raw.set_montage("standard_1020", verbose=False)
            self.raw.set_eeg_reference("average", projection=True, verbose=False)
            self.label_recording_duration.setText(str(self.raw.times[-1]) + " seconds")
            self.label_eeg_channels.setText(str(self.raw.info['ch_names']))
            self.label_sampling_frequency.setText(str(self.raw.info['sfreq']))
        self.create_epochs()

    def start_recording(self):
        if not self.input_duration.text():
            self.show_toast("Error! Cannot start recording.", "Please fill the duration of the recording.",
                            ToastPreset.ERROR)
            return
        if not self.input_filename.text() or self.input_filename.text() == "":
            self.show_toast("Error! Cannot start recording.", "Please fill the filename of the recording.",
                            ToastPreset.ERROR)
            return
        self.is_recording = True
        self.button_start.setEnabled(False)
        self.button_stop.setEnabled(True)
        duration = int(self.input_duration.text())
        self.eeg_data = []
        self.eeg_data_count = 0

        try:
            self.board.prepare_session()
            self.board.start_stream()
        except BrainFlowError as e:
            self.show_toast("Error! Cannot start recording.", f"Something's wrong with BrainFlow: {e}",
                            ToastPreset.ERROR, 12000)
            self.is_recording = False
            self.button_start.setEnabled(True)
            self.button_stop.setEnabled(False)
            return
        except Exception as e:
            self.show_toast("Error! Cannot start recording.", f"Unknown error: {e}", ToastPreset.ERROR, 12000)
            self.is_recording = False
            self.button_start.setEnabled(True)
            self.button_stop.setEnabled(False)
            return

        # Start timer for real-time plotting
        self.timer.start(100)

        # Play Music
        if self.input_music.currentIndex() > 0:
            music_path = os.path.join(os.getcwd(), "musics", self.input_music.currentText())
            mixer.music.load(music_path)
            mixer.music.play()
        # ==========

        # Record data in a separate thread
        self.record_thread = threading.Thread(target=self.record_data, args=(duration,))
        self.record_thread.start()

    def record_data(self, duration):
        while self.eeg_data_count // self.SAMPLING_FREQUENCY < duration:
            if not self.is_recording:
                break
            data = self.board.get_board_data()
            if data.size > 0:  # Check if there is any data returned
                self.eeg_data.append(data)
                self.eeg_data_count += data.shape[1]
            time.sleep(0.2)
        data = self.board.get_board_data()
        if data.size > 0:  # Check if there is any data returned
            self.eeg_data.append(data)  # Append the latest data chunk
            self.eeg_data_count += data.shape[1]
        self.stop_recording()

    def stop_recording(self):
        if self.input_music.currentIndex() > 0:
            mixer.music.stop()
        if self.board:
            self.board.stop_stream()
            self.board.release_session()
        self.is_recording = False
        self.button_start.setEnabled(True)
        self.button_stop.setEnabled(False)
        self.timer.stop()
        self.save_recording()

    def update_plot(self):
        if self.eeg_data:
            # Concatenate data
            eeg_data = np.concatenate(self.eeg_data, axis=1)
            eeg_data = eeg_data[self.EEG_CHANNELS, :]

            # Calculate the number of samples for the last 5 seconds
            num_samples_last_5_sec = 3 * self.SAMPLING_FREQUENCY

            # Get the data for the last 5 seconds
            if eeg_data.shape[1] > num_samples_last_5_sec:
                eeg_data_last_5_sec = eeg_data[:, -num_samples_last_5_sec:]
                start_time = (eeg_data.shape[1] - num_samples_last_5_sec) / self.SAMPLING_FREQUENCY
            else:
                eeg_data_last_5_sec = eeg_data
                start_time = 0

            self.figure.clear()
            ax = self.figure.add_subplot(111)

            for idx, channel_data in enumerate(eeg_data_last_5_sec):
                ax.plot(channel_data.T, label=self.EEG_CHANNELS_NAME[idx])

            ax.set_ylabel('Microvolts (µV)')
            ax.set_xlabel('Time (s)')
            num_samples = eeg_data_last_5_sec.shape[1]

            # Calculate the x-axis values and labels
            x_values = np.arange(start_time, start_time + num_samples / self.SAMPLING_FREQUENCY,
                                 1 / self.SAMPLING_FREQUENCY)
            ax.set_xticks(np.arange(0, num_samples, self.SAMPLING_FREQUENCY))  # Set major ticks at every second
            ax.set_xticklabels(
                (x_values[:num_samples:self.SAMPLING_FREQUENCY] // 1).astype(int))  # Label ticks with second values

            ax.legend(loc='upper right')

            self.figure.subplots_adjust(left=0.05, bottom=0.05, right=0.98, top=0.98, wspace=0, hspace=0)
            self.canvas.draw()

    def create_raw(self):
        eeg_data = np.concatenate(self.eeg_data, axis=1)
        eeg_data = eeg_data[self.EEG_CHANNELS, :] / 1000000  # BrainFlow returns uV, convert to V for MNE

        # Creating MNE objects from brainflow data arrays
        ch_types = ['eeg'] * len(self.EEG_CHANNELS)
        info = mne.create_info(ch_names=self.EEG_CHANNELS_NAME, sfreq=self.SAMPLING_FREQUENCY, ch_types=ch_types)
        self.raw = mne.io.RawArray(eeg_data, info)
        self.raw.set_montage("standard_1020", verbose=False)
        self.raw.set_eeg_reference("average", projection=True, verbose=False)
        print(self.raw.info)

    def save_recording(self):
        self.create_raw()  # Ensure the raw object is created
        filename = self.input_filename.text() + "_raw.fif"
        self.raw.save(f"./recordings/{filename}", overwrite=True)
        self.toast_signal.emit("Success! Recording saved.",
                               f"Recording successfully saved at \"./recordings/{filename}\".", ToastPreset.SUCCESS,
                               8000)


class SignalHandler(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    def show_toast_slot(self, title: str, message: str, preset, duration: int):
        toast = Toast(None)  # Create toast without parent (or with main window as parent if needed)
        toast.setDuration(duration)
        toast.setTitle(title)
        toast.setText(message)
        toast.applyPreset(preset)
        toast.show()


def main():
    pygame.init()
    app = QApplication(sys.argv)
    app.setFont(QFont("Roboto", 12))
    ex = EEGStreamApp()
    handler = SignalHandler()
    ex.toast_signal.connect(handler.show_toast_slot)
    ex.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
