import sys
import json
import cv2  # For reading frame rate
from PyQt6.QtWidgets import *
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl, Qt, QTimer, QTime
from PyQt6.QtGui import *


class AddSubtitleDialog(QDialog):
    def __init__(self, start_time, default_end_time, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Subtitle")
        self.resize(400, 300)

        # Start and End Time QTimeEdit fields
        self.start_time_edit = QTimeEdit(QTime.fromString(start_time, 'hh:mm:ss.zzz'))
        self.end_time_edit = QTimeEdit(QTime.fromString(default_end_time, 'hh:mm:ss.zzz'))
        self.start_time_edit.setDisplayFormat("hh:mm:ss.zzz")
        self.end_time_edit.setDisplayFormat("hh:mm:ss.zzz")

        # Text input with word wrap (QTextEdit)
        self.text_edit = QTextEdit()
        self.text_edit.setFixedWidth(300)
        self.text_edit.setFixedHeight(200)
        self.text_edit.setWordWrapMode(QTextOption.WrapMode.WordWrap)

        # Checkbox to allow manual end time adjustment
        self.auto_end_checkbox = QCheckBox("Auto-adjust end time based on 1 sec/word")
        self.auto_end_checkbox.setChecked(True)  # Checked by default

        # Layout
        layout = QFormLayout()
        layout.addRow("Start Time:", self.start_time_edit)
        layout.addRow("End Time:", self.end_time_edit)
        layout.addRow("Subtitle Text:", self.text_edit)
        layout.addRow(self.auto_end_checkbox)

        # OK and Cancel buttons
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        layout.addRow(ok_button, cancel_button)
        self.setLayout(layout)

    def getValues(self):
        return {
            'start': self.start_time_edit.time().toString('hh:mm:ss.zzz'),
            'end': self.end_time_edit.time().toString('hh:mm:ss.zzz'),
            'text': self.text_edit.toPlainText(),
            'auto_end': self.auto_end_checkbox.isChecked()
        }


class EditSubtitleDialog(QDialog):
    def __init__(self, subtitle, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Subtitle")
        self.resize(400, 200)

        self.start_time_edit = QTimeEdit(QTime.fromString(subtitle['start'], 'hh:mm:ss.zzz'))
        self.end_time_edit = QTimeEdit(QTime.fromString(subtitle['end'], 'hh:mm:ss.zzz'))
        self.start_time_edit.setDisplayFormat("hh:mm:ss.zzz")
        self.end_time_edit.setDisplayFormat("hh:mm:ss.zzz")

        self.text_edit = QTextEdit(subtitle['text'])
        self.start_time_edit.setFixedWidth(150)
        self.end_time_edit.setFixedWidth(150)
        self.text_edit.setFixedWidth(400)
        self.text_edit.setFixedHeight(200)

        layout = QFormLayout()
        layout.addRow("Start Time:", self.start_time_edit)
        layout.addRow("End Time:", self.end_time_edit)
        layout.addRow("Text:", self.text_edit)

        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        layout.addRow(ok_button, cancel_button)
        self.setLayout(layout)

    def getValues(self):
        return {
            'start': self.start_time_edit.time().toString('hh:mm:ss.zzz'),
            'end': self.end_time_edit.time().toString('hh:mm:ss.zzz'),
            'text': self.text_edit.toPlainText()
        }


class SubtitleWidget(QWidget):
    def __init__(self, start, end, text):
        super().__init__()
        layout = QVBoxLayout()
        layout.setSpacing(5)

        self.start_label = QLabel(f'Start: {start}')
        self.end_label = QLabel(f'End: {end}')
        self.subtitle_label = QLabel(text)

        self.start_label.setStyleSheet("font-size: 12px; color: gray;")
        self.end_label.setStyleSheet("font-size: 12px; color: gray;")
        self.subtitle_label.setStyleSheet("font-size: 18px; font-weight: bold; color: black;")

        layout.addWidget(self.start_label)
        layout.addWidget(self.end_label)
        layout.addWidget(self.subtitle_label)

        self.setLayout(layout)


class VideoPlayer(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize video widget
        self.videoWidget = QVideoWidget()
        self.videoWidget.setStyleSheet("background-color: black;")

        # Media Player
        self.mediaPlayer = QMediaPlayer(self)
        self.audioOutput = QAudioOutput(self)
        self.mediaPlayer.setAudioOutput(self.audioOutput)

        # Subtitle Display Box (now enlarged)
        self.subtitleBox = QLabel("Subtitles will be displayed here.")
        self.subtitleBox.setStyleSheet("background-color: black; color: white; padding: 5px;")
        self.subtitleBox.setFont(QFont("Courier New", 24))  # Enlarged font
        self.subtitleBox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitleBox.setFixedHeight(50)  # Enlarged height

        # Additional selected subtitle display box
        self.selectedSubtitleBox = QLabel("Selected subtitle will be displayed here.")
        self.selectedSubtitleBox.setStyleSheet("background-color: black; color: white; padding: 5px;")
        self.selectedSubtitleBox.setFont(QFont("Courier New", 16))
        self.selectedSubtitleBox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selectedSubtitleBox.setFixedHeight(50)

        # Open Button
        openButton = QPushButton()
        openButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        openButton.clicked.connect(self.openFile)
        self.styleButton(openButton, double_width=False)

        # Load Subtitles Button
        loadSubtitlesButton = QPushButton("Subs")
        loadSubtitlesButton.clicked.connect(self.loadSubtitles)
        self.styleButton(loadSubtitlesButton, double_width=True)

        # Play Button
        self.playButton = QPushButton()
        self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.playButton.clicked.connect(self.playPause)
        self.styleButton(self.playButton)

        # Frame-by-Frame Buttons
        frameForwardButton = QPushButton("+ Frame")
        frameForwardButton.clicked.connect(self.stepFrameForward)
        self.styleButton(frameForwardButton, double_width=True)

        frameBackwardButton = QPushButton("- Frame")
        frameBackwardButton.clicked.connect(self.stepFrameBackward)
        self.styleButton(frameBackwardButton, double_width=True)

        # Fast Forward and Rewind Buttons
        forwardButton = QPushButton()
        forwardButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward))
        forwardButton.clicked.connect(self.forward)
        self.styleButton(forwardButton)

        backButton = QPushButton()
        backButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekBackward))
        backButton.clicked.connect(self.backward)
        self.styleButton(backButton)

        # Set In and Set Out buttons
        setInButton = QPushButton("Set In")
        setInButton.clicked.connect(self.setInPoint)
        self.styleButton(setInButton, double_width=False)

        setOutButton = QPushButton("Set Out")
        setOutButton.clicked.connect(self.setOutPoint)
        self.styleButton(setOutButton, double_width=False)

        # Timecode Label
        self.timecodeLabel = QLabel("00:00:00:000")
        self.timecodeLabel.setStyleSheet("background-color: black; color: white; padding: 0 10px;")
        self.timecodeLabel.setFont(QFont("Courier New", 16))  # Use Courier New for timecode
        self.timecodeLabel.setFixedHeight(50)
        self.timecodeLabel.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderPressed.connect(self.pauseVideo)
        self.slider.sliderMoved.connect(self.updatePositionWhileSliding)
        self.slider.sliderReleased.connect(self.setPositionAndPause)

        # Layout for buttons
        buttonLayout = QHBoxLayout()
        buttonLayout.setSpacing(10)
        buttonLayout.addWidget(openButton)
        buttonLayout.addWidget(loadSubtitlesButton)
        buttonLayout.addWidget(frameBackwardButton)
        buttonLayout.addWidget(backButton)
        buttonLayout.addWidget(self.playButton)
        buttonLayout.addWidget(forwardButton)
        buttonLayout.addWidget(frameForwardButton)
        buttonLayout.addWidget(setInButton)
        buttonLayout.addWidget(setOutButton)

        # Layout for transport buttons and timecode
        bottomLayout = QHBoxLayout()
        bottomLayout.addLayout(buttonLayout)
        bottomLayout.addWidget(self.timecodeLabel)

        # Subtitle Playlist
        self.subtitleList = QListWidget()

        # Add and Delete buttons for subtitles (reduced size)
        addSubtitleButton = QPushButton("Add")
        addSubtitleButton.clicked.connect(self.addSubtitle)
        self.styleButton(addSubtitleButton, double_width=True)
        addSubtitleButton.setFixedWidth(200)

        deleteSubtitleButton = QPushButton("Remove")
        deleteSubtitleButton.clicked.connect(self.deleteSubtitle)
        self.styleButton(deleteSubtitleButton, double_width=True)
        deleteSubtitleButton.setFixedWidth(200)

        subtitleButtonLayout = QHBoxLayout()
        subtitleButtonLayout.addWidget(addSubtitleButton)
        subtitleButtonLayout.addWidget(deleteSubtitleButton)

        # Splitter to separate video and playlist
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.videoWidget)
        subtitleLayout = QVBoxLayout()
        subtitleLayout.addWidget(self.subtitleList)
        subtitleLayout.addLayout(subtitleButtonLayout)  # Buttons at the bottom, resized
        subtitleWidget = QWidget()
        subtitleWidget.setLayout(subtitleLayout)
        splitter.addWidget(subtitleWidget)
        splitter.setSizes([800, 300])  # More space for the playlist

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(splitter)
        layout.addWidget(self.subtitleBox)
        layout.addWidget(self.selectedSubtitleBox)  # New selected subtitle display box
        layout.addWidget(self.slider)
        layout.addLayout(bottomLayout)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        self.setLayout(layout)

        self.setWindowTitle("Video Player with Subtitles")
        self.setGeometry(100, 100, 1000, 600)

        # Media Player Settings
        self.mediaPlayer.setVideoOutput(self.videoWidget)
        self.mediaPlayer.mediaStatusChanged.connect(self.updateButtons)
        self.mediaPlayer.positionChanged.connect(self.updatePosition)
        self.mediaPlayer.durationChanged.connect(self.updateDuration)

        # Timer to update timecode and subtitles
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.updateTimecode)
        self.timer.start()

        self.frame_rate = 25  # Default frame rate
        self.subtitles = []   # Store subtitles from JSON
        self.currentSubtitle = ""
        self.selectedSubtitle = None  # Track the currently selected subtitle

    def styleButton(self, button, double_width=False):
        width = 75 if double_width else 40  # Reduced size for add/remove buttons
        button.setStyleSheet("""
            QPushButton {
                background-color: #888;
                color: white;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:pressed {
                background-color: #666;
                border-style: inset;
            }
        """)
        button.setFixedSize(width, 30)

    def openFile(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Media File", "", "Video Files (*.mp4 *.avi *.mkv *.mov)")
        if fileName != '':
            self.mediaPlayer.setSource(QUrl.fromLocalFile(fileName))
            self.playButton.setEnabled(True)

            # Get the frame rate of the video using OpenCV
            video = cv2.VideoCapture(fileName)
            self.frame_rate = video.get(cv2.CAP_PROP_FPS)
            video.release()

    def loadSubtitles(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Subtitles File", "", "Subtitle Files (*.json)")
        if fileName:
            with open(fileName, 'r') as file:
                self.subtitles = json.load(file)
                self.populateSubtitleList()

    def populateSubtitleList(self):
        self.subtitleList.clear()
        for index, subtitle in enumerate(self.subtitles):
            widget = SubtitleWidget(subtitle["start"], subtitle["end"], subtitle["text"])
            item = QListWidgetItem(self.subtitleList)
            item.setSizeHint(widget.sizeHint())
            item.setForeground(QColor('white'))  # Set subtitle color to white for visibility
            self.subtitleList.setItemWidget(item, widget)

        self.subtitleList.itemClicked.connect(self.selectSubtitle)

    def selectSubtitle(self, item):
        row = self.subtitleList.row(item)
        subtitle = self.subtitles[row]
        self.selectedSubtitle = subtitle

        # Move video to start time of the selected subtitle
        start_time_ms = QTime.fromString(subtitle['start'], 'hh:mm:ss.zzz').msecsSinceStartOfDay()
        self.mediaPlayer.setPosition(start_time_ms)

        # Update the selected subtitle display box
        self.selectedSubtitleBox.setText(f"{subtitle['start']} --> {subtitle['end']}: {subtitle['text']}")

    def setInPoint(self):
        if self.selectedSubtitle:
            # Update the start time of the selected subtitle to the current media position
            current_timecode = self.mediaPlayer.position()
            new_start_time = QTime(0, 0, 0).addMSecs(current_timecode).toString('hh:mm:ss.zzz')
            self.selectedSubtitle['start'] = new_start_time
            self.populateSubtitleList()
            self.selectedSubtitleBox.setText(f"{self.selectedSubtitle['start']} --> {self.selectedSubtitle['end']}: {self.selectedSubtitle['text']}")

    def setOutPoint(self):
        if self.selectedSubtitle:
            # Update the end time of the selected subtitle to the current media position
            current_timecode = self.mediaPlayer.position()
            new_end_time = QTime(0, 0, 0).addMSecs(current_timecode).toString('hh:mm:ss.zzz')
            self.selectedSubtitle['end'] = new_end_time
            self.populateSubtitleList()
            self.selectedSubtitleBox.setText(f"{self.selectedSubtitle['start']} --> {self.selectedSubtitle['end']}: {self.selectedSubtitle['text']}")

    def addSubtitle(self):
        current_timecode = self.mediaPlayer.position()
        start_time = QTime(0, 0, 0).addMSecs(current_timecode).toString('hh:mm:ss.zzz')
        default_end_time = QTime(0, 0, 0).addMSecs(current_timecode + 2000).toString('hh:mm:ss.zzz')

        # Open the add subtitle dialog
        add_subtitle_dialog = AddSubtitleDialog(start_time, default_end_time, self)
        result = add_subtitle_dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            values = add_subtitle_dialog.getValues()
            text = values['text']
            start_time = values['start']

            # If the checkbox is checked, calculate end time based on the number of words
            if values['auto_end']:
                num_words = len(text.split())
                end_time_ms = current_timecode + num_words * 1000  # 1 second per word
                end_time = QTime(0, 0, 0).addMSecs(end_time_ms).toString('hh:mm:ss.zzz')
            else:
                end_time = values['end']  # Use manually set end time

            new_subtitle = {"start": start_time, "end": end_time, "text": text}
            self.subtitles.append(new_subtitle)
            self.populateSubtitleList()  # Update the list with the new subtitle

    def deleteSubtitle(self):
        selected_row = self.subtitleList.currentRow()
        if selected_row >= 0:
            del self.subtitles[selected_row]
            self.populateSubtitleList()

    def highlightCurrentSubtitle(self, position):
        current_time = QTime(0, 0, 0).addMSecs(position)
        for index, subtitle in enumerate(self.subtitles):
            start_time = QTime.fromString(subtitle['start'], 'hh:mm:ss.zzz')
            end_time = QTime.fromString(subtitle['end'], 'hh:mm:ss.zzz')
            if start_time <= current_time <= end_time:
                self.subtitleList.setCurrentRow(index)
                break

    def getSubtitleForTime(self, position):
        current_time = QTime(0, 0, 0).addMSecs(position)
        for subtitle in self.subtitles:
            start_time = QTime.fromString(subtitle['start'], 'hh:mm:ss.zzz')
            end_time = QTime.fromString(subtitle['end'], 'hh:mm:ss.zzz')
            if start_time <= current_time <= end_time:
                return subtitle['text']
        return ""

    def playPause(self):
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))

    def stop(self):
        self.mediaPlayer.stop()
        self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

    def forward(self):
        self.mediaPlayer.setPosition(self.mediaPlayer.position() + 5000)

    def backward(self):
        self.mediaPlayer.setPosition(self.mediaPlayer.position() - 5000)

    def stepFrameForward(self):
        self.pauseVideo()
        new_position = self.mediaPlayer.position() + int(1000 / self.frame_rate)
        self.mediaPlayer.setPosition(new_position)
        self.updateTimecode(new_position)

    def stepFrameBackward(self):
        self.pauseVideo()
        new_position = self.mediaPlayer.position() - int(1000 / self.frame_rate)
        self.mediaPlayer.setPosition(new_position)
        self.updateTimecode(new_position)

    def setPositionAndPause(self):
        self.mediaPlayer.setPosition(self.slider.value())
        self.pauseVideo()

    def updatePositionWhileSliding(self, position):
        self.slider.setValue(position)
        self.updateTimecode(position)

    def pauseVideo(self):
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.mediaPlayer.pause()

    def updatePosition(self, position):
        self.slider.setValue(position)
        self.updateTimecode(position)

    def updateDuration(self, duration):
        self.slider.setRange(0, duration)

    def updateButtons(self, status):
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

    def updateTimecode(self, position=None):
        if position is None:
            position = self.mediaPlayer.position()

        time = QTime(0, 0, 0).addMSecs(position)
        timecode = f'{time.hour():02}:{time.minute():02}:{time.second():02}:{time.msec():03}'
        self.timecodeLabel.setText(timecode)

        self.currentSubtitle = self.getSubtitleForTime(position)
        self.subtitleBox.setText(self.currentSubtitle)
        self.highlightCurrentSubtitle(position)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())
