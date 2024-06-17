# EEG Streamer
EEG Streamer is a graphical user interface (GUI) application designed to record and visualize EEG (Electroencephalography) data using the Muse 2 headset. The application allows users to stream, record, and analyze EEG data in real-time, with features for playing music during recordings, visualizing raw EEG data, and generating various EEG-related plots.

# Features
1. Real-time EEG data streaming and recording.
2. Music playback during EEG recording.
3. Visualization of raw EEG data.
4. Generation of EEG-related plots:
5. EEG signal plot
6. Headmap plot
7. Averaged EEG plot
8. Power Spectral Density (PSD) plot
9. User-friendly interface with PyQt5.
10. Easy-to-use file management for saved recordings.

# Requirements
1. Python 3.8+
2. PyQt5
3. matplotlib
4. brainflow
5. mne
6. pyqttoast
7. pygame

# Installation
1. Clone the repository:

```bash
git clone https://github.com/Kosmasu/muse-reader.git
cd muse-reader
```

2. Create a virtual environment and activate it:

```bash
python -m venv venv
source venv/bin/activate   # On Windows use `venv\Scripts\activate`
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```
5. Ensure the Muse 2 headset is turned on.
6. Start recording!

# Usage
1. Run the application:
```bash
python eeg_streamer.py
```
2. Navigate through the application using the menu bar:

* Recording Page: Set up and start a new EEG recording session.
* Data Page: Load and analyze previously saved EEG recordings.
3. Fill out the recording form:

* Duration: Set the duration of the recording (1-3600 seconds).
* Filename: Specify the filename for the saved recording.
* Music: Choose a music file to play during the recording (optional).
4. Click Start Recording to begin recording EEG data. The Stop Recording button will become enabled, allowing you to end the recording session manually if needed.
5. View the real-time EEG data plot on the recording page.
6. Once the recording is finished, navigate to the Data Page to analyze and visualize the recorded data.
