import sys
import cv2  # For reading frame rate
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QSlider, QHBoxLayout, QVBoxLayout,
    QLabel, QFileDialog, QStyle
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl, Qt, QTimer, QTime, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QFont


class VideoPlayer(QWidget):
    def __init__(self):
        super().__init__()

        # Media Player
        self.mediaPlayer = QMediaPlayer(self)
        self.audioOutput = QAudioOutput(self)
        self.mediaPlayer.setAudioOutput(self.audioOutput)

        # Video Widget
        self.videoWidget = VideoWidget()
        self.videoWidget.setStyleSheet("background-color: black;")

        # Open Button with folder icon
        openButton = QPushButton()
        openButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        openButton.clicked.connect(self.openFile)
        self.styleButton(openButton, double_width=False)

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
        self.timecodeLabel.setFont(QFont("Courier", 16))  # Fixed-width font, adjusted size
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

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.videoWidget)
        layout.addWidget(self.slider)
        layout.addLayout(bottomLayout)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        self.setLayout(layout)

        self.setWindowTitle("Video Player")
        self.setGeometry(100, 100, 800, 600)

        # Media Player Settings
        self.mediaPlayer.setVideoOutput(self.videoWidget)
        self.mediaPlayer.mediaStatusChanged.connect(self.updateButtons)
        self.mediaPlayer.positionChanged.connect(self.updatePosition)
        self.mediaPlayer.durationChanged.connect(self.updateDuration)

        # Timer to update timecode
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.updateTimecode)
        self.timer.start()

        self.frame_rate = 24  # Default frame rate

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


class VideoWidget(QVideoWidget):
    def paintEvent(self, event):
        super().paintEvent(event)

        # Draw a green box in the center of the video widget (70% width, 80% height)
        painter = QPainter(self)
        green_pen = QPen(QColor(0, 255, 0), 4)  # Green pen with thickness 4
        painter.setPen(green_pen)

        width = int(self.width() * 0.7)
        height = int(self.height() * 0.8)

        # Center the rectangle
        rect_x = (self.width() - width) // 2
        rect_y = (self.height() - height) // 2

        rect = QRect(rect_x, rect_y, width, height)
        painter.drawRect(rect)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())
