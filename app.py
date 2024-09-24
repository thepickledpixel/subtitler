import os
import sys
import json
import cv2  # For reading frame rate
from PyQt6.QtWidgets import *
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices, QAudioSink
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl, Qt, QTimer, QTime, QByteArray, QSize
from PyQt6.QtGui import *

import numpy as np
import matplotlib.pyplot as plt
from pydub import AudioSegment
from io import BytesIO


if getattr(sys, 'frozen', False):
    runpath = os.path.dirname(sys.executable)
else:
    runpath = os.path.abspath(os.path.dirname(__file__))

class ConfigureFonts():
    def __init__(self):
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

        # Load and set the custom font
        mono_font_id = QFontDatabase.addApplicationFont(
            os.path.join(runpath, "ConsolaMono-Book.ttf")
        )
        if mono_font_id == -1:
            print("Failed to load the custom font. Falling back to default.")
            mono_font_family = QApplication.font().family()
        else:
            mono_font_family = QFontDatabase.applicationFontFamilies(mono_font_id)[0]
        self.mono_font = QFont(mono_font_family)

class AddSubtitleDialog(QDialog):
    def __init__(self, start_time, default_end_time, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Subtitle")
        self.resize(400, 300)

        fonts = ConfigureFonts()

        new_font = QFont(fonts.font)  # Copy the current font
        new_font.setPointSize(24)

        self.start_time_edit = QTimeEdit(QTime.fromString(start_time, 'hh:mm:ss.zzz'))
        self.end_time_edit = QTimeEdit(QTime.fromString(default_end_time, 'hh:mm:ss.zzz'))
        self.start_time_edit.setDisplayFormat("hh:mm:ss.zzz")
        self.end_time_edit.setDisplayFormat("hh:mm:ss.zzz")
        self.end_time_edit.setFont(fonts.font)
        self.start_time_edit.setFont(fonts.font)

        self.text_edit = QTextEdit()
        self.text_edit.setFixedWidth(300)
        self.text_edit.setFixedHeight(200)
        self.text_edit.setFont(new_font)
        self.text_edit.setWordWrapMode(QTextOption.WrapMode.WordWrap)

        self.auto_end_checkbox = QCheckBox("Auto-adjust end time based on 1 sec/word")
        self.auto_end_checkbox.setChecked(True)

        layout = QFormLayout()
        layout.addRow(QLabel("Start Time:", font=fonts.font), self.start_time_edit)
        layout.addRow(QLabel("End Time:", font=fonts.font), self.end_time_edit)
        layout.addRow(QLabel("Subtitle Text:", font=fonts.font), self.text_edit)
        layout.addRow(self.auto_end_checkbox)

        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        ok_button.setFont(fonts.font)
        cancel_button.setFont(fonts.font)

        layout.addRow(ok_button, cancel_button)
        self.setLayout(layout)
        self.text_edit.setFocus()

    def getValues(self):
        return {
            'start': self.start_time_edit.time().toString('hh:mm:ss.zzz'),
            'end': self.end_time_edit.time().toString('hh:mm:ss.zzz'),
            'text': self.text_edit.toPlainText(),
            'auto_end': self.auto_end_checkbox.isChecked()
        }

class EditSubtitleDialog(QDialog):
    def __init__(self, subtitle, parent=None):

        fonts = ConfigureFonts()

        super().__init__(parent)
        self.setWindowTitle("Edit Subtitle")
        self.resize(400, 200)

        self.start_time_edit = QTimeEdit(QTime.fromString(subtitle['start'], 'hh:mm:ss.zzz'))
        self.end_time_edit = QTimeEdit(QTime.fromString(subtitle['end'], 'hh:mm:ss.zzz'))
        self.start_time_edit.setDisplayFormat("hh:mm:ss.zzz")
        self.start_time_edit.setFont(fonts.font)
        self.end_time_edit.setDisplayFormat("hh:mm:ss.zzz")
        self.end_time_edit.setFont(fonts.font)

        self.text_edit = QTextEdit(subtitle['text'])
        self.start_time_edit.setFixedWidth(150)
        self.end_time_edit.setFixedWidth(150)

        self.text_edit.setFixedWidth(400)
        self.text_edit.setFixedHeight(200)

        new_font = QFont(fonts.font)  # Copy the current font
        new_font.setPointSize(24)

        self.text_edit.setFont(new_font)

        layout = QFormLayout()
        layout.addRow(QLabel("Start Time:", font=fonts.font), self.start_time_edit)
        layout.addRow(QLabel("End Time:", font=fonts.font), self.end_time_edit)
        layout.addRow(QLabel("Text:", font=fonts.font), self.text_edit)

        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        ok_button.setFont(fonts.font)
        cancel_button.setFont(fonts.font)

        layout.addRow(ok_button, cancel_button)
        self.setLayout(layout)
        self.text_edit.setFocus()

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

        self.fonts = ConfigureFonts()

        self.start_label = QLabel(f'Start: {start}')
        self.end_label = QLabel(f'End: {end}')
        self.subtitle_label = QLabel(text)
        self.subtitle_label.setFont(self.fonts.font)

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

        self.fonts = ConfigureFonts()

        # Initialize video widget
        self.videoWidget = QVideoWidget()
        self.videoWidget.setStyleSheet("background-color: dark grey;")

        # Media Player
        self.mediaPlayer = QMediaPlayer(self)
        self.audioOutput = QAudioOutput(self)
        self.mediaPlayer.setAudioOutput(self.audioOutput)

        # Subtitle Display Box
        self.subtitleBox = QLabel("")
        self.subtitleBox.setStyleSheet("background-color: dark grey; color: white; padding: 5px;")
        subtitle_font = self.fonts.font
        subtitle_font.setPointSize(24)
        self.subtitleBox.setFont(subtitle_font)
        self.subtitleBox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitleBox.setFixedHeight(50)

        # Additional selected subtitle display box
        self.selectedSubtitleBox = QLabel("")
        self.selectedSubtitleBox.setStyleSheet("background-color: dark grey; color: white; padding: 5px;")
        self.selectedSubtitleBox.setFont(self.fonts.mono_font)
        self.selectedSubtitleBox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selectedSubtitleBox.setFixedHeight(50)

        # Open Button
        openButton = QPushButton("Video")
        openButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        openButton.setIconSize(QSize(16, 16))
        openButton.clicked.connect(self.openFile)
        openButton.setFont(self.fonts.font)
        self.styleButton(openButton, double_width=True)

        loadSubtitlesButton = QPushButton("Subtitles")
        loadSubtitlesButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        loadSubtitlesButton.setIconSize(QSize(16, 16))
        loadSubtitlesButton.clicked.connect(self.loadSubtitlesManually)
        loadSubtitlesButton.setFont(self.fonts.font)
        self.styleButton(loadSubtitlesButton, double_width=True)

        # Play Button
        self.playButton = QPushButton()
        self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.playButton.clicked.connect(self.playPause)
        self.styleButton(self.playButton)

        # Frame-by-Frame Buttons
        frameForwardButton = QPushButton("+ 1")
        frameForwardButton.clicked.connect(self.stepFrameForward)
        frameForwardButton.setFont(self.fonts.font)
        self.styleButton(frameForwardButton, double_width=False)

        frameBackwardButton = QPushButton("- 1")
        frameBackwardButton.clicked.connect(self.stepFrameBackward)
        frameBackwardButton.setFont(self.fonts.font)
        self.styleButton(frameBackwardButton, double_width=False)

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
        subInButton = QPushButton("Subtitle IN")
        subInButton.clicked.connect(self.setInPoint)
        subInButton.setFont(self.fonts.font)
        self.styleButton(subInButton, double_width=True)

        subOutButton = QPushButton("Subtitle OUT")
        subOutButton.clicked.connect(self.setOutPoint)
        subOutButton.setFont(self.fonts.font)
        self.styleButton(subOutButton, double_width=True)

        # Timecode Label
        self.timecodeLabel = QLabel("00:00:00,000")
        self.timecodeLabel.setStyleSheet("background-color: dark grey; color: white; padding: 0 10px;")
        timecode_font = QFont(self.fonts.mono_font)
        timecode_font.setPointSize(24)
        self.timecodeLabel.setFont(timecode_font)
        self.timecodeLabel.setFixedHeight(50)
        self.timecodeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

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

        # Add and Delete buttons for subtitles
        addSubtitleButton = QPushButton("Add Subtitle")
        addSubtitleButton.clicked.connect(self.addSubtitle)
        addSubtitleButton.setFont(self.fonts.font)
        self.styleButton(addSubtitleButton, double_width=True)
        addSubtitleButton.setFixedWidth(200)

        deleteSubtitleButton = QPushButton("Remove Subtitle")
        deleteSubtitleButton.clicked.connect(self.deleteSubtitle)
        deleteSubtitleButton.setFont(self.fonts.font)
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

        # Store the current file path and duration
        self.currentFilePath = None
        self.subtitleFilePath = None
        self.duration = 0

        self.setLayout(layout)
        self.setWindowTitle("Smart Subs")
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
        self.allow_snapping = False

        self.mediaPlayer.playbackStateChanged.connect(self.updateButtons)

    def openFile(self):
        """
        Open a video file and load the corresponding subtitle file if it exists,
        or create an empty subtitle file if it doesn't.
        """
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Media File", "", "Video Files (*.mp4 *.avi *.mkv *.mov)")
        if fileName:
            self.currentFilePath = fileName
            self.mediaPlayer.setSource(QUrl.fromLocalFile(fileName))
            self.playButton.setEnabled(True)

            video = cv2.VideoCapture(fileName)
            self.frame_rate = video.get(cv2.CAP_PROP_FPS)
            video.release()

            self.subtitleFilePath = os.path.splitext(fileName)[0] + ".json"

            # Clear the subtitle playlist when loading a new video
            self.subtitles = []  # Clear the subtitle data
            self.populateSubtitleList()  # Clear the UI list

            if os.path.exists(self.subtitleFilePath):
                self.loadSubtitles()
            else:
                self.saveSubtitles()

    def populateSubtitleList(self):
        """
        Populate the subtitle list widget from the subtitles.
        Clears the list if no subtitles are available.
        """
        self.subtitleList.clear()  # Clear the list first
        for index, subtitle in enumerate(self.subtitles):
            widget = SubtitleWidget(subtitle["start"], subtitle["end"], subtitle["text"])
            item = QListWidgetItem(self.subtitleList)
            item.setSizeHint(widget.sizeHint())
            item.setForeground(QColor('white'))
            self.subtitleList.setItemWidget(item, widget)

        # Ensure signals are connected properly
        try:
            self.subtitleList.itemDoubleClicked.disconnect(self.editSubtitle)
        except TypeError:
            pass
        self.subtitleList.itemDoubleClicked.connect(self.editSubtitle)

    def updateTimecode(self, position=None):
        """
        Update the timecode and highlight the currently playing subtitle.
        """
        if position is None:
            position = self.mediaPlayer.position()

        time = QTime(0, 0, 0).addMSecs(position)
        timecode = f'{time.hour():02}:{time.minute():02}:{time.second():02},{time.msec():03}'
        self.timecodeLabel.setText(timecode)

        # Ensure snapping is enabled and the subtitles are highlighted
        if self.allow_snapping:
            self.highlightCurrentSubtitle(position)

        # Update the displayed subtitle
        self.currentSubtitle = self.getSubtitleForTime(position)
        self.subtitleBox.setText(self.currentSubtitle)


    def highlightCurrentSubtitle(self, position):
        """
        Highlight the current subtitle in the subtitle list based on the playhead position.
        """
        current_time = QTime(0, 0, 0).addMSecs(position)
        for index, subtitle in enumerate(self.subtitles):
            start_time = QTime.fromString(subtitle['start'], 'hh:mm:ss.zzz')
            end_time = QTime.fromString(subtitle['end'], 'hh:mm:ss.zzz')
            if start_time <= current_time <= end_time:
                self.subtitleList.setCurrentRow(index)
                break

    def loadSubtitles(self):
        """
        Load subtitles from the JSON file.
        """
        if self.subtitleFilePath:
            try:
                with open(self.subtitleFilePath, 'r') as file:
                    self.subtitles = json.load(file)
                    self.populateSubtitleList()
            except Exception as e:
                print(f"Error loading subtitles: {e}")

    def styleButton(self, button, double_width=False):
        width = 100 if double_width else 50  # Doubled the width for Sub IN/OUT buttons
        height = 40
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
        button.setFixedSize(width, height)
#
    def addSubtitle(self):
        """
        Add a new subtitle, then save the subtitles to the JSON file.
        """
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
            self.saveSubtitles()  # Save the updated subtitles

    def deleteSubtitle(self):
        """
        Delete a subtitle, then save the subtitles to the JSON file.
        """
        selected_row = self.subtitleList.currentRow()
        if selected_row >= 0:
            del self.subtitles[selected_row]
            self.populateSubtitleList()
            self.saveSubtitles()  # Save the updated subtitles

    def loadSubtitlesManually(self):
        """
        Manually load subtitles via the button.
        """
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Subtitles File", "", "Subtitle Files (*.json)")
        if fileName:
            self.subtitleFilePath = fileName  # Set the subtitle file path to the manually loaded file
            self.loadSubtitles()  # Load the selected subtitle file

    def saveSubtitles(self):
        """
        Save subtitles to the JSON file.
        """
        if self.subtitleFilePath:
            try:
                with open(self.subtitleFilePath, 'w') as file:
                    json.dump(self.subtitles, file, indent=4)
                print(f"Subtitles saved to {self.subtitleFilePath}")
            except Exception as e:
                print(f"Error saving subtitles: {e}")

    def populateSubtitleList(self):
        """
        Populate the subtitle list widget from the subtitles.
        Clears the list if no subtitles are available.
        """
        self.subtitleList.clear()  # Clear the list first
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
        """
        Select a subtitle from the playlist and display it in the selectedSubtitleBox.
        Disable snapping temporarily, and re-enable it after a short delay or when the video is playing.
        """
        row = self.subtitleList.row(item)
        subtitle = self.subtitles[row]
        self.selectedSubtitle = subtitle
        self.allow_snapping = False

        # Display the selected subtitle in the additional subtitle box
        select_subtitle_font = QFont(self.fonts.mono_font)
        select_subtitle_font.setPointSize(16)
        self.selectedSubtitleBox.setFont(select_subtitle_font)
        self.selectedSubtitleBox.setText(f"Selected: {subtitle['start']} --> {subtitle['end']}: {subtitle['text']}")

    #     # Re-enable snapping after 2 seconds (or a custom delay)
    #     QTimer.singleShot(5000, lambda: self.setSnapping(True))
    #
    # def setSnapping(self, enable):
    #     """Utility function to toggle snapping."""
    #     self.allow_snapping = enable


    def editSubtitle(self, item):
        """
        Edit a subtitle, then save the subtitles to the JSON file.
        """
        row = self.subtitleList.row(item)
        subtitle = self.subtitles[row]

        edit_dialog = EditSubtitleDialog(subtitle, self)
        result = edit_dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            updated_values = edit_dialog.getValues()
            self.subtitles[row] = updated_values
            self.populateSubtitleList()
            self.saveSubtitles()  # Save the updated subtitles

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
        """
        Toggles between play and pause.
        Re-enables snapping when the video is playing.
        """
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.mediaPlayer.pause()
        else:
            self.mediaPlayer.play()
            self.allow_snapping = True  # Re-enable snapping when the video plays


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

    def updatePositionWhileSliding(self, position):
        """Called while the slider is being moved."""
        self.slider.setValue(position)
        self.updateTimecode(position)
        self.scrubAudio(position, scrubbing=True)  # Short scrubbing while sliding

    def setPositionAndPause(self):
        """Called when the slider is released, and video pauses."""
        self.mediaPlayer.setPosition(self.slider.value())
        self.pauseVideo()
        self.scrubAudio(self.slider.value(), scrubbing=False)  # Longer scrubbing on slider release
        # self.allow_snapping = True  # Re-enable snapping after slider release

    def scrubAudio(self, position, scrubbing=True):
        """
        Plays a short or longer snippet of audio depending on whether the user is scrubbing or has released the slider,
        and returns the playhead back to the original position after playing the audio.
        """
        # Store the current playhead position
        self.original_position = self.mediaPlayer.position()

        # Set the media player to the current position for scrubbing
        self.mediaPlayer.setPosition(position)
        self.audioOutput.setVolume(0.7)  # Set the volume for scrubbing

        # Play audio snippet
        self.mediaPlayer.play()

        # After playing the audio snippet, return the playhead to the original position
        snippet_duration = 300 if scrubbing else 300  # Shorter when scrubbing, longer on release
        QTimer.singleShot(snippet_duration, self.returnPlayheadToOriginal)

    def returnPlayheadToOriginal(self):
        """
        Pauses the media player and returns the playhead to the original position.
        """
        # Pause the media player to stop both audio and video
        self.mediaPlayer.pause()

        # Return the playhead back to the original position
        self.mediaPlayer.setPosition(self.original_position)


    def updatePosition(self, position):
        self.slider.setValue(position)
        self.updateTimecode(position)

    def updateDuration(self, duration):
        self.slider.setRange(0, duration)

    def updateTimecode(self, position=None):
        """
        Update the timecode and highlight the currently playing subtitle.
        """
        if position is None:
            position = self.mediaPlayer.position()

        time = QTime(0, 0, 0).addMSecs(position)
        timecode = f'{time.hour():02}:{time.minute():02}:{time.second():02},{time.msec():03}'
        self.timecodeLabel.setText(timecode)

        if self.allow_snapping:
            self.highlightCurrentSubtitle(position)

        self.currentSubtitle = self.getSubtitleForTime(position)
        self.subtitleBox.setText(self.currentSubtitle)

    def highlightCurrentSubtitle(self, position):
        """
        Highlight the current subtitle in the subtitle list based on the playhead position.
        """
        current_time = QTime(0, 0, 0).addMSecs(position)
        for index, subtitle in enumerate(self.subtitles):
            start_time = QTime.fromString(subtitle['start'], 'hh:mm:ss.zzz')
            end_time = QTime.fromString(subtitle['end'], 'hh:mm:ss.zzz')
            if start_time <= current_time <= end_time:
                self.subtitleList.setCurrentRow(index)
                break

    def getSubtitleForTime(self, position):
        """
        Retrieve the subtitle text for the given playhead position.
        """
        current_time = QTime(0, 0, 0).addMSecs(position)
        for subtitle in self.subtitles:
            start_time = QTime.fromString(subtitle['start'], 'hh:mm:ss.zzz')
            end_time = QTime.fromString(subtitle['end'], 'hh:mm:ss.zzz')
            if start_time <= current_time <= end_time:
                return subtitle['text']
        return ""

    def updateButtons(self, status=None):
        """
        Updates the play/pause button icon based on the current playback state.
        """
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())
