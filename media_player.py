import sys
import json
import cv2  # For reading frame rate
from PyQt6.QtWidgets import *
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl, Qt, QTimer, QTime, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QFont

class SubtitleOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.subtitle = ""
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def setSubtitle(self, subtitle):
        self.subtitle = subtitle
        self.update()

    def paintEvent(self, event):
        if not self.subtitle:
            return

        painter = QPainter(self)
        painter.setPen(QColor(255, 255, 255))  # White text
        painter.setFont(QFont("Courier", 20, QFont.Weight.Bold))

        # Draw the subtitle text at the bottom center of the video
        text_rect = self.rect().adjusted(0, self.height() - 60, 0, -10)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.subtitle)
        painter.end()

class EditSubtitleDialog(QDialog):
    def __init__(self, subtitle, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Subtitle")
        self.resize(400, 200)  # Adjust size to be more spacious

        # Create fields for editing
        self.start_time_edit = QTimeEdit(QTime.fromString(subtitle['start'], 'hh:mm:ss.zzz'))
        self.end_time_edit = QTimeEdit(QTime.fromString(subtitle['end'], 'hh:mm:ss.zzz'))
        self.text_edit = QLineEdit(subtitle['text'])

        self.start_time_edit.setFixedWidth(150)
        self.end_time_edit.setFixedWidth(150)
        self.text_edit.setFixedWidth(300)

        # Layout for the dialog
        layout = QFormLayout()
        layout.addRow("Start Time:", self.start_time_edit)
        layout.addRow("End Time:", self.end_time_edit)
        layout.addRow("Text:", self.text_edit)

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
            'text': self.text_edit.text()
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

        # Media Player
        self.mediaPlayer = QMediaPlayer(self)
        self.audioOutput = QAudioOutput(self)
        self.mediaPlayer.setAudioOutput(self.audioOutput)

        # Video Widget
        self.videoWidget = QVideoWidget()
        self.videoWidget.setStyleSheet("background-color: black;")

        # Subtitle Overlay Widget (on top of the video widget)
        self.subtitleOverlay = SubtitleOverlay(self.videoWidget)

        # Open Button with folder icon
        openButton = QPushButton()
        openButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        openButton.clicked.connect(self.openFile)
        self.styleButton(openButton, double_width=False)

        # Load Subtitles Button
        loadSubtitlesButton = QPushButton("Load Subtitles")
        loadSubtitlesButton.clicked.connect(self.loadSubtitles)
        self.styleButton(loadSubtitlesButton, double_width=False)

        # Play Button
        self.playButton = QPushButton()
        self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.playButton.clicked.connect(self.playPause)
        self.styleButton(self.playButton)

        # Stop Button
        stopButton = QPushButton()
        stopButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        stopButton.clicked.connect(self.stop)
        self.styleButton(stopButton)

        # Forward Button
        forwardButton = QPushButton()
        forwardButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward))
        forwardButton.clicked.connect(self.forward)
        self.styleButton(forwardButton)

        # Backward Button
        backButton = QPushButton()
        backButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSeekBackward))
        backButton.clicked.connect(self.backward)
        self.styleButton(backButton)

        # Frame-by-Frame Buttons
        frameForwardButton = QPushButton("+ Frame")
        frameForwardButton.clicked.connect(self.stepFrameForward)
        self.styleButton(frameForwardButton, double_width=True)

        frameBackwardButton = QPushButton("- Frame")
        frameBackwardButton.clicked.connect(self.stepFrameBackward)
        self.styleButton(frameBackwardButton, double_width=True)

        # Timecode Label
        self.timecodeLabel = QLabel("00:00:00:00 (24fps)")
        self.timecodeLabel.setStyleSheet("background-color: black; color: white; padding: 0 10px;")
        self.timecodeLabel.setFont(QFont("Courier", 16))  # Using Courier for timecode
        self.timecodeLabel.setFixedHeight(50)  # Match the height of the buttons
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
        buttonLayout.addWidget(stopButton)
        buttonLayout.addWidget(forwardButton)
        buttonLayout.addWidget(frameForwardButton)

        # Layout for transport buttons and timecode
        bottomLayout = QHBoxLayout()
        bottomLayout.addLayout(buttonLayout)
        bottomLayout.addWidget(self.timecodeLabel)

        # Subtitle Playlist
        self.subtitleList = QListWidget()

        # Splitter to separate video and playlist
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.videoWidget)
        splitter.addWidget(self.subtitleList)
        splitter.setSizes([800, 200])

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(splitter)
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

        self.frame_rate = 24  # Default frame rate
        self.subtitles = []   # Store subtitles from JSON
        self.currentSubtitle = ""

        # Make sure subtitle overlay resizes with video
        self.videoWidget.installEventFilter(self)

        # Media Player Settings
        self.mediaPlayer.setVideoOutput(self.videoWidget)
        self.mediaPlayer.mediaStatusChanged.connect(self.updateButtons)
        self.mediaPlayer.positionChanged.connect(self.updatePosition)
        self.mediaPlayer.durationChanged.connect(self.updateDuration)


    def eventFilter(self, watched, event):
        if watched == self.videoWidget and event.type() == event.Type.Resize:
            self.subtitleOverlay.resize(self.videoWidget.size())
        return super().eventFilter(watched, event)

    def styleButton(self, button, double_width=False):
        width = 100 if double_width else 50
        button.setStyleSheet("""
            QPushButton {
                background-color: #888;
                color: white;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:pressed {
                background-color: #666;
                border-style: inset;
            }
        """)
        button.setFixedSize(width, 50)

    def openFile(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Media File", "", "Video Files (*.mp4 *.avi *.mkv *.mov)")
        if fileName != '':
            self.mediaPlayer.setSource(QUrl.fromLocalFile(fileName))
            self.playButton.setEnabled(True)

            # Get the frame rate of the video using OpenCV
            video = cv2.VideoCapture(fileName)
            self.frame_rate = video.get(cv2.CAP_PROP_FPS)
            video.release()

            # Update the timecode with the correct frame rate
            self.updateTimecode()
            self.videoWidget.update()  # Force update to redraw the green box

    def loadSubtitles(self):
        # Load subtitle file in JSON format
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
            self.subtitleList.setItemWidget(item, widget)

        # Connect double-click event to open edit dialog
        self.subtitleList.itemDoubleClicked.connect(self.editSubtitle)

    def editSubtitle(self, item):
        row = self.subtitleList.row(item)
        subtitle = self.subtitles[row]

        if not hasattr(self, 'edit_dialog') or not self.edit_dialog.isVisible():
            self.edit_dialog = EditSubtitleDialog(subtitle, self)
            if self.edit_dialog.exec():
                updated_values = self.edit_dialog.getValues()

                # Update the subtitle in the list
                self.subtitles[row] = updated_values

                # Refresh the list to show updated values
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
        # Find the correct subtitle for the current position (in ms)
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
        # Skip forward by 5 seconds
        self.mediaPlayer.setPosition(self.mediaPlayer.position() + 5000)

    def backward(self):
        # Skip backward by 5 seconds
        self.mediaPlayer.setPosition(self.mediaPlayer.position() - 5000)

    def stepFrameForward(self):
        # Step one frame forward and pause
        self.pauseVideo()
        new_position = self.mediaPlayer.position() + int(1000 / self.frame_rate)
        self.mediaPlayer.setPosition(new_position)
        self.updateTimecode(new_position)

    def stepFrameBackward(self):
        # Step one frame backward and pause
        self.pauseVideo()
        new_position = self.mediaPlayer.position() - int(1000 / self.frame_rate)
        self.mediaPlayer.setPosition(new_position)
        self.updateTimecode(new_position)

    def setPositionAndPause(self):
        # Set position to the value from the slider when released and pause
        self.mediaPlayer.setPosition(self.slider.value())
        self.pauseVideo()  # Keep the video paused

    def updatePositionWhileSliding(self, position):
        # Update the timecode label as the slider moves
        self.slider.setValue(position)
        self.updateTimecode(position)

    def pauseVideo(self):
        # Pause video when slider is pressed or stepping frames
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.mediaPlayer.pause()

    def updatePosition(self, position):
        # Update slider and timecode based on the current position
        self.slider.setValue(position)
        self.updateTimecode(position)

    def updateDuration(self, duration):
        # Set the slider range based on the video duration
        self.slider.setRange(0, duration)

    def updateButtons(self, status):
        # Update button icons based on playback state
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))


    def updateTimecode(self, position=None):
        if position is None:
            position = self.mediaPlayer.position()

        # Convert position (in ms) to HH:MM:SS:FF
        time = QTime(0, 0, 0).addMSecs(position)
        hours = time.hour()
        minutes = time.minute()
        seconds = time.second()
        milliseconds = time.msec()

        # Convert milliseconds to frames based on frame rate
        frames = int((milliseconds / 1000) * self.frame_rate)

        timecode = f'{hours:02}:{minutes:02}:{seconds:02}:{frames:02} ({int(self.frame_rate)}fps)'
        self.timecodeLabel.setText(timecode)

        # Update subtitle display
        self.currentSubtitle = self.getSubtitleForTime(position)
        self.subtitleOverlay.setSubtitle(self.currentSubtitle)
        self.highlightCurrentSubtitle(position)

class VideoWidget(QVideoWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subtitle = ""

    def setSubtitle(self, subtitle):
        self.subtitle = subtitle
        self.update()  # Ensure the widget is updated when the subtitle changes

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)

        # Draw subtitle text over the video
        if self.subtitle:
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.setFont(QFont("Courier", 20, QFont.Weight.Bold))
            text_rect = QRect(0, self.height() - 60, self.width(), 50)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.subtitle)

        painter.end()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())
