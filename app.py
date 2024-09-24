import os
import sys
import json
import cv2  # For reading frame rate
from PyQt6.QtWidgets import *
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl, Qt, QTimer, QTime
from PyQt6.QtGui import *

if getattr(sys, 'frozen', False):
    runpath = os.path.dirname(sys.executable)
else:
    runpath = os.path.abspath(os.path.dirname(__file__))

class AddSubtitleDialog(QDialog):
    def __init__(self, start_time, default_end_time, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Subtitle")
        self.resize(400, 300)

        self.start_time_edit = QTimeEdit(QTime.fromString(start_time, 'hh:mm:ss.zzz'))
        self.end_time_edit = QTimeEdit(QTime.fromString(default_end_time, 'hh:mm:ss.zzz'))
        self.start_time_edit.setDisplayFormat("hh:mm:ss.zzz")
        self.end_time_edit.setDisplayFormat("hh:mm:ss.zzz")

        self.text_edit = QTextEdit()
        self.text_edit.setFixedWidth(300)
        self.text_edit.setFixedHeight(200)
        self.text_edit.setWordWrapMode(QTextOption.WrapMode.WordWrap)

        self.auto_end_checkbox = QCheckBox("Auto-adjust end time based on 1 sec/word")
        self.auto_end_checkbox.setChecked(True)

        layout = QFormLayout()
        layout.addRow("Start Time:", self.start_time_edit)
        layout.addRow("End Time:", self.end_time_edit)
        layout.addRow("Subtitle Text:", self.text_edit)
        layout.addRow(self.auto_end_checkbox)

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

        # Load and set the custom font
        font_id = QFontDatabase.addApplicationFont(
            os.path.join(runpath, "Louis George Cafe.ttf")
        )
        if font_id == -1:
            print("Failed to load the custom font. Falling back to default.")
            font_family = QApplication.font().family()
        else:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self.font = QFont(font_family)

        self.start_label = QLabel(f'Start: {start}')
        self.end_label = QLabel(f'End: {end}')
        self.subtitle_label = QLabel(text)
        self.subtitle_label.setFont(self.font)

        self.start_label.setStyleSheet("font-size: 12px; color: gray;")
        self.end_label.setStyleSheet("font-size: 12px; color: gray;")
        self.subtitle_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")

        layout.addWidget(self.start_label)
        layout.addWidget(self.end_label)
        layout.addWidget(self.subtitle_label)

        self.setLayout(layout)


class VideoPlayer(QWidget):
    def __init__(self):
        super().__init__()

        # Load and set the custom font
        font_id = QFontDatabase.addApplicationFont(
            os.path.join(runpath, "Louis George Cafe.ttf")
        )
        if font_id == -1:
            print("Failed to load the custom font. Falling back to default.")
            font_family = QApplication.font().family()
        else:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self.font = QFont(font_family)

        # Initialize video widget
        self.videoWidget = QVideoWidget()
        self.videoWidget.setStyleSheet("background-color: black;")

        # Media Player
        self.mediaPlayer = QMediaPlayer(self)
        self.audioOutput = QAudioOutput(self)
        self.mediaPlayer.setAudioOutput(self.audioOutput)

        # Subtitle Display Box
        self.subtitleBox = QLabel("Subtitles will be displayed here.")
        self.subtitleBox.setStyleSheet("background-color: black; color: white; padding: 5px;")
        self.subtitleBox.setFont(QFont("Courier New", 24))
        self.subtitleBox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitleBox.setFixedHeight(50)

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
        loadSubtitlesButton.setFont(self.font)
        self.styleButton(loadSubtitlesButton, double_width=True)

        # Play Button
        self.playButton = QPushButton()
        self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.playButton.clicked.connect(self.playPause)
        self.styleButton(self.playButton)

        # Frame-by-Frame Buttons
        frameForwardButton = QPushButton("+ Frame")
        frameForwardButton.clicked.connect(self.stepFrameForward)
        frameForwardButton.setFont(self.font)
        self.styleButton(frameForwardButton, double_width=True)

        frameBackwardButton = QPushButton("- Frame")
        frameBackwardButton.clicked.connect(self.stepFrameBackward)
        frameBackwardButton.setFont(self.font)
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

        # Set In and Set Out buttons (renamed to Sub IN and Sub OUT, and doubled in width)
        subInButton = QPushButton("Set Subtitle IN")
        subInButton.clicked.connect(self.setInPoint)
        subInButton.setFont(self.font)
        self.styleButton(subInButton, double_width=True)

        subOutButton = QPushButton("Sub Subtitle OUT")
        subOutButton.clicked.connect(self.setOutPoint)
        subOutButton.setFont(self.font)
        self.styleButton(subOutButton, double_width=True)

        # Timecode Label
        self.timecodeLabel = QLabel("00:00:00:000")
        self.timecodeLabel.setStyleSheet("background-color: black; color: white; padding: 0 10px;")
        self.timecodeLabel.setFont(QFont("Courier New", 16))
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
        buttonLayout.addWidget(subInButton)
        buttonLayout.addWidget(subOutButton)

        # Layout for transport buttons and timecode
        bottomLayout = QHBoxLayout()
        bottomLayout.addLayout(buttonLayout)
        bottomLayout.addWidget(self.timecodeLabel)

        # Subtitle Playlist
        self.subtitleList = QListWidget()

        # Add and Delete buttons for subtitles (reduced size)
        addSubtitleButton = QPushButton("Add Subtitle")
        addSubtitleButton.clicked.connect(self.addSubtitle)  # Correctly defined now
        addSubtitleButton.setFont(self.font)
        self.styleButton(addSubtitleButton, double_width=True)
        addSubtitleButton.setFixedWidth(200)

        deleteSubtitleButton = QPushButton("Remove Subtitle")
        deleteSubtitleButton.clicked.connect(self.deleteSubtitle)
        deleteSubtitleButton.setFont(self.font)
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
        subtitleLayout.addLayout(subtitleButtonLayout)
        subtitleWidget = QWidget()
        subtitleWidget.setLayout(subtitleLayout)
        splitter.addWidget(subtitleWidget)
        splitter.setSizes([800, 300])

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(splitter)
        layout.addWidget(self.subtitleBox)
        layout.addWidget(self.selectedSubtitleBox)
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
        self.subtitles = []  # Store subtitles from JSON
        self.currentSubtitle = ""
        self.selectedSubtitle = None
        self.allow_snapping = True

    def styleButton(self, button, double_width=False):
        width = 150 if double_width else 40  # Doubled the width for Sub IN/OUT buttons
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

    def addSubtitle(self):
        current_timecode = self.mediaPlayer.position()
        start_time = QTime(0, 0, 0).addMSecs(current_timecode).toString('hh:mm:ss.zzz')
        default_end_time = QTime(0, 0, 0).addMSecs(current_timecode + 2000).toString('hh:mm:ss.zzz')

        add_subtitle_dialog = AddSubtitleDialog(start_time, default_end_time, self)
        result = add_subtitle_dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            values = add_subtitle_dialog.getValues()
            text = values['text']
            start_time = values['start']

            if values['auto_end']:
                num_words = len(text.split())
                end_time_ms = current_timecode + num_words * 1000
                end_time = QTime(0, 0, 0).addMSecs(end_time_ms).toString('hh:mm:ss.zzz')
            else:
                end_time = values['end']

            new_subtitle = {"start": start_time, "end": end_time, "text": text}
            self.subtitles.append(new_subtitle)
            self.populateSubtitleList()

    def deleteSubtitle(self):
        selected_row = self.subtitleList.currentRow()
        if selected_row >= 0:
            del self.subtitles[selected_row]
            self.populateSubtitleList()

    def openFile(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Media File", "", "Video Files (*.mp4 *.avi *.mkv *.mov)")
        if fileName != '':
            self.mediaPlayer.setSource(QUrl.fromLocalFile(fileName))
            self.playButton.setEnabled(True)

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
            item.setForeground(QColor('white'))
            self.subtitleList.setItemWidget(item, widget)

        try:
            self.subtitleList.itemDoubleClicked.disconnect(self.editSubtitle)
        except TypeError:
            pass  # Signal was not connected before, so nothing to disconnect

        self.subtitleList.itemDoubleClicked.connect(self.editSubtitle)
        self.subtitleList.itemClicked.connect(self.selectSubtitle)

    def selectSubtitle(self, item):
        row = self.subtitleList.row(item)
        subtitle = self.subtitles[row]
        self.selectedSubtitle = subtitle
        self.allow_snapping = False

        self.selectedSubtitleBox.setText(f"{subtitle['start']} --> {subtitle['end']}: {subtitle['text']}")

    def editSubtitle(self, item):
        row = self.subtitleList.row(item)
        subtitle = self.subtitles[row]

        edit_dialog = EditSubtitleDialog(subtitle, self)
        result = edit_dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            updated_values = edit_dialog.getValues()
            self.subtitles[row] = updated_values
            self.populateSubtitleList()

    def setInPoint(self):
        if self.selectedSubtitle:
            current_timecode = self.mediaPlayer.position()
            new_start_time = QTime(0, 0, 0).addMSecs(current_timecode).toString('hh:mm:ss.zzz')
            self.selectedSubtitle['start'] = new_start_time
            self.populateSubtitleList()
            self.selectedSubtitleBox.setText(f"{self.selectedSubtitle['start']} --> {self.selectedSubtitle['end']}: {self.selectedSubtitle['text']}")

    def setOutPoint(self):
        if self.selectedSubtitle:
            current_timecode = self.mediaPlayer.position()
            new_end_time = QTime(0, 0, 0).addMSecs(current_timecode).toString('hh:mm:ss.zzz')
            self.selectedSubtitle['end'] = new_end_time
            self.populateSubtitleList()
            self.selectedSubtitleBox.setText(f"{self.selectedSubtitle['start']} --> {self.selectedSubtitle['end']}: {self.selectedSubtitle['text']}")

    def playPause(self):
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.allow_snapping = True

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

    def pauseVideo(self):
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.mediaPlayer.pause()

    def setPositionAndPause(self):
        self.mediaPlayer.setPosition(self.slider.value())
        self.pauseVideo()
        self.allow_snapping = True

    def updatePositionWhileSliding(self, position):
        self.slider.setValue(position)
        self.updateTimecode(position)

    def updatePosition(self, position):
        self.slider.setValue(position)
        self.updateTimecode(position)

    def updateDuration(self, duration):
        self.slider.setRange(0, duration)

    def updateTimecode(self, position=None):
        if position is None:
            position = self.mediaPlayer.position()

        time = QTime(0, 0, 0).addMSecs(position)
        timecode = f'{time.hour():02}:{time.minute():02}:{time.second():02}:{time.msec():03}'
        self.timecodeLabel.setText(timecode)

        if self.allow_snapping:
            self.highlightCurrentSubtitle(position)

        self.currentSubtitle = self.getSubtitleForTime(position)
        self.subtitleBox.setText(self.currentSubtitle)

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

    def updateButtons(self, status):
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())
