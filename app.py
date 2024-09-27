import os
import sys
import json
import cv2

import numpy as np
import matplotlib.pyplot as plt

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices, QAudioSink
from PyQt6.QtMultimediaWidgets import QVideoWidget

from pydub import AudioSegment
from io import BytesIO
from multiprocessing import Process

from gen_subs import *

if getattr(sys, 'frozen', False):
    runpath = os.path.dirname(sys.executable)
else:
    runpath = os.path.abspath(os.path.dirname(__file__))

max_subtitle_length = 2000

def crop_subtitle(subtitle):
    if len(subtitle) >= max_subtitle_length:
        return subtitle[:max_subtitle_length] + "..."
    else:
        return subtitle

class SpinnerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.fonts = ConfigureFonts()

        self.setWindowTitle("Generating Subtitles")
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(400, 250)  # Set fixed width and height

        # Create a vertical layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the contents vertically

        # Create and set up the animated spinner
        self.spinnerLabel = QLabel("Generating Subtitles...")
        spinner_font = QFont(self.fonts.font)
        spinner_font.setPointSize(24)
        self.spinnerLabel.setFont(spinner_font)
        layout.addWidget(self.spinnerLabel, alignment=Qt.AlignmentFlag.AlignCenter)

        self.movieLabel = QLabel()
        self.movie = QMovie(os.path.join(runpath, "static", "spinner.gif"))  # Path to your animated GIF
        self.movieLabel.setMovie(self.movie)
        self.movieLabel.setFixedSize(160, 120)  # Set size for the spinner
        self.movieLabel.setScaledContents(True)
        self.movie.start()
        layout.addWidget(self.movieLabel, alignment=Qt.AlignmentFlag.AlignCenter)

        # Add the cancel button
        self.cancelButton = QPushButton("Cancel")
        self.styleButton(self.cancelButton)
        self.cancelButton.clicked.connect(self.cancel)
        layout.addWidget(self.cancelButton, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setStyleSheet("background-color: #002031;")
        #002031

        self.setLayout(layout)

    def styleButton(self, button):
        width = 100 # Doubled the width for Sub IN/OUT buttons
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

    def cancel(self):
        self.reject()  # Close the dialog when canceled

    def closeEvent(self, event):
        # Prevent closing the dialog
        event.ignore()

class SubtitleWorker:
    def __init__(self, file_path):
        self.file_path = file_path
        self.process = None

    def start(self):
        # Start the external process (replace `make_subtitles` with your actual script)
        self.process = Process(target=make_subtitles, args=(self.file_path,))
        self.process.start()

    def is_finished(self):
        # Check if the process has finished
        return self.process and not self.process.is_alive()

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.join()
            print("Process terminated.")

class ConfigureFonts():
    def __init__(self):
        # Load and set the custom font
        font_id = QFontDatabase.addApplicationFont(
            os.path.join(runpath, "fonts", "Louis George Cafe.ttf")
        )
        if font_id == -1:
            print("Failed to load the custom font. Falling back to default.")
            font_family = QApplication.font().family()
        else:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self.font = QFont(font_family)

        # Load and set the custom font
        mono_font_id = QFontDatabase.addApplicationFont(
            os.path.join(runpath, "fonts", "ConsolaMono-Book.ttf")
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
    def __init__(self, subtitle, video_duration_ms, parent=None):
        fonts = ConfigureFonts()

        super().__init__(parent)
        self.setWindowTitle("Edit Subtitle")
        self.resize(400, 200)

        self.video_duration_ms = video_duration_ms  # Video duration in milliseconds

        # Create start time and end time editors
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

        new_font = QFont(fonts.font)
        new_font.setPointSize(24)
        self.text_edit.setFont(new_font)

        # Create nudge buttons for start time
        start_nudge_layout = QHBoxLayout()
        nudge_back_start_btn = QPushButton("- Nudge")
        nudge_back_start_btn.clicked.connect(self.nudgeStartBack)
        nudge_forward_start_btn = QPushButton("+ Nudge")
        nudge_forward_start_btn.clicked.connect(self.nudgeStartForward)
        start_nudge_layout.addWidget(self.start_time_edit)
        start_nudge_layout.addWidget(nudge_back_start_btn)
        start_nudge_layout.addWidget(nudge_forward_start_btn)

        # Create nudge buttons for end time
        end_nudge_layout = QHBoxLayout()
        nudge_back_end_btn = QPushButton("- Nudge")
        nudge_back_end_btn.clicked.connect(self.nudgeEndBack)
        nudge_forward_end_btn = QPushButton("+ Nudge")
        nudge_forward_end_btn.clicked.connect(self.nudgeEndForward)
        end_nudge_layout.addWidget(self.end_time_edit)
        end_nudge_layout.addWidget(nudge_back_end_btn)
        end_nudge_layout.addWidget(nudge_forward_end_btn)

        layout = QFormLayout()
        layout.addRow(QLabel("Start Time:", font=fonts.font), start_nudge_layout)
        layout.addRow(QLabel("End Time:", font=fonts.font), end_nudge_layout)
        layout.addRow(QLabel("Text:", font=fonts.font), self.text_edit)

        # OK and Cancel buttons
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        ok_button.setFont(fonts.font)
        cancel_button.setFont(fonts.font)

        layout.addRow(ok_button, cancel_button)
        self.setLayout(layout)
        self.text_edit.setFocus()

    # Helper function to get milliseconds from QTime
    def time_to_milliseconds(self, qtime):
        return QTime(0, 0, 0).msecsTo(qtime)

    def milliseconds_to_time(self, ms):
        return QTime(0, 0, 0).addMSecs(int(ms))

    # Function to nudge start time back by 500ms
    def nudgeStartBack(self):
        current_time_ms = self.time_to_milliseconds(self.start_time_edit.time())
        new_time_ms = max(current_time_ms - 500, 0)  # Ensure time doesn't go below 0
        self.start_time_edit.setTime(self.milliseconds_to_time(new_time_ms))

    # Function to nudge start time forward by 500ms
    def nudgeStartForward(self):
        current_time_ms = self.time_to_milliseconds(self.start_time_edit.time())
        new_time_ms = min(current_time_ms + 500, self.video_duration_ms)
        self.start_time_edit.setTime(self.milliseconds_to_time(new_time_ms))

    # Function to nudge end time back by 500ms
    def nudgeEndBack(self):
        current_time_ms = self.time_to_milliseconds(self.end_time_edit.time())
        new_time_ms = max(current_time_ms - 500, 0)  # Ensure time doesn't go below 0
        self.end_time_edit.setTime(self.milliseconds_to_time(new_time_ms))

    # Function to nudge end time forward by 500ms
    def nudgeEndForward(self):
        current_time_ms = self.time_to_milliseconds(self.end_time_edit.time())
        new_time_ms = min(current_time_ms + 500, self.video_duration_ms)
        self.end_time_edit.setTime(self.milliseconds_to_time(new_time_ms))

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

        self.start_label = QLabel(f'{start} --> {end}')
        self.start_label.setFont(self.fonts.font)
        self.subtitle_label = QLabel(text.strip())
        self.subtitle_label.setFont(self.fonts.font)
        self.subtitle_label.setWordWrap(True)

        self.start_label.setStyleSheet("font-size: 14px; color: gray;")
        self.subtitle_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")

        layout.addWidget(self.start_label)
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
        self.subtitleBox.setWordWrap(True)
        self.subtitleBox.setFixedHeight(70)

        # Open Button
        openButton = QPushButton(" Video")
        openButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        openButton.setIconSize(QSize(16, 16))
        openButton.clicked.connect(self.openFile)
        openButton.setFont(self.fonts.font)
        self.styleButton(openButton, double_width=True)

        # Play Button
        self.playButton = QPushButton()
        self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.playButton.clicked.connect(self.playPause)
        self.styleButton(self.playButton)

        # Frame-by-Frame Buttons
        frameForwardButton = QPushButton("+ 10")
        frameForwardButton.clicked.connect(self.stepFrameForward)
        frameForwardButton.setFont(self.fonts.font)
        self.styleButton(frameForwardButton, double_width=False)

        frameBackwardButton = QPushButton("- 10")
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

        genSubsButton = QPushButton("AI Subtitles")
        genSubsButton.clicked.connect(self.generateSubtitles)
        genSubsButton.setFont(self.fonts.font)
        self.styleButton(genSubsButton, double_width=True)

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
        # buttonLayout.addWidget(loadSubtitlesButton)
        buttonLayout.addWidget(frameBackwardButton)
        buttonLayout.addWidget(backButton)
        buttonLayout.addWidget(self.playButton)
        buttonLayout.addWidget(forwardButton)
        buttonLayout.addWidget(frameForwardButton)
        # buttonLayout.addWidget(subInButton)
        # buttonLayout.addWidget(subOutButton)
        buttonLayout.addWidget(genSubsButton)

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
        # layout.addWidget(self.selectedSubtitleBox)
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
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.updateTimecode)
        self.timer.start()

        self.frame_rate = 25  # Default frame rate
        self.subtitles = []  # Store subtitles from JSON
        self.currentSubtitle = ""
        self.selectedSubtitle = None
        # self.allow_snapping = False

        # Define a shortcut for the space bar
        space_shortcut = QShortcut(QKeySequence("Space"), self)
        space_shortcut.activated.connect(self.playPause)  # Bind the space bar to play/pause

        self.subtitleBox.mousePressEvent = self.onSubtitleClicked  # Link mouse press event to single click handler
        self.subtitleBox.mouseDoubleClickEvent = self.onSubtitleDoubleClicked

        self.mediaPlayer.playbackStateChanged.connect(self.updateButtons)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.playPause()  # Space bar to toggle play/pause
        elif event.key() == Qt.Key.Key_Left:
            self.backward()  # Left arrow to rewind
        elif event.key() == Qt.Key.Key_Right:
            self.forward()  # Right arrow to fast forward

    def adjustFontSizeToFit(self, text):
        """
        Adjust the font size of the subtitle text to fit within the QLabel box.
        Reset the font size to 24 before adjusting, and then shrink if necessary.
        """
        font = self.subtitleBox.font()
        font.setPointSize(24)  # Reset to default size (24)
        self.subtitleBox.setFont(font)  # Apply the reset font to the subtitle box
        font_metrics = QFontMetrics(font)

        available_width = self.subtitleBox.width() - 10  # Adjust for padding
        available_height = self.subtitleBox.height()

        # Initialize line1 and line2
        line1 = text
        line2 = ""

        # Split text into two lines
        words = text.split()
        if len(words) > 1:
            # Try splitting the text into two roughly equal parts
            mid = len(words) // 2
            line1 = " ".join(words[:mid])
            line2 = " ".join(words[mid:])
            two_line_text = f"{line1}\n{line2}"
        else:
            # If only one word, use it as is
            two_line_text = text

        # Check if the two-line text fits
        while font.pointSize() > 8:  # Minimum font size to avoid unreadable text
            font_metrics = QFontMetrics(font)

            # Calculate the width and height of the two-line text
            text_width = max(font_metrics.horizontalAdvance(line1), font_metrics.horizontalAdvance(line2))
            text_height = font_metrics.lineSpacing() * 2 if line2 else font_metrics.lineSpacing()

            # If the two-line text fits within the box, stop reducing the font size
            if text_width <= available_width and text_height <= available_height:
                self.subtitleBox.setFont(font)
                self.subtitleBox.setText(two_line_text)
                return

            # If it doesn't fit, reduce the font size
            font.setPointSize(font.pointSize() - 1)

        # If the text is still too big after reducing, just set the text with the smallest font size
        self.subtitleBox.setFont(font)
        self.subtitleBox.setText(two_line_text)

    def question_box(self, title, question):
        reply = QMessageBox.question(
            self, title, question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            return True
        else:
            return False

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

               # Get the total number of frames
            frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)

            # Calculate video duration in milliseconds
            self.duration = (frame_count / self.frame_rate) * 1000 if self.frame_rate > 0 else 0

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
            widget = SubtitleWidget(
                subtitle["start"],
                subtitle["end"],
                crop_subtitle(["text"][:max_subtitle_length])
            )
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
        Update the timecode and display the currently playing subtitle.
        """
        if position is None:
            position = self.mediaPlayer.position()

        time = QTime(0, 0, 0).addMSecs(position)
        timecode = f'{time.hour():02}:{time.minute():02}:{time.second():02},{time.msec():03}'
        self.timecodeLabel.setText(timecode)

        # Update the displayed subtitle text in the subtitle box
        subtitle_text = self.getSubtitleForTime(position)
        self.adjustFontSizeToFit(crop_subtitle(subtitle_text))
        self.subtitleBox.setText(crop_subtitle(subtitle_text))

    def onSubtitleClicked(self, event):
        """
        Handle single click on the currently playing subtitle.
        Update the selected subtitle box to show the current subtitle's start and end time.
        """
        current_position = self.mediaPlayer.position()
        subtitle = self.getSubtitleForTime(current_position, return_full_subtitle=True)
        if subtitle:
            self.selectedSubtitle = subtitle

    def onSubtitleDoubleClicked(self, event):
        """
        Handle double-click on the currently playing subtitle.
        Open the EditSubtitleDialog for the current subtitle.
        """
        current_position = self.mediaPlayer.position()
        subtitle = self.getSubtitleForTime(current_position, return_full_subtitle=True)
        if subtitle:
            self.editSubtitleForCurrent(subtitle)

    def editSubtitleForCurrent(self, subtitle):
        """
        Open the edit subtitle dialog for the given subtitle.
        """
        dialog = EditSubtitleDialog(subtitle, video_duration_ms=self.duration)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            updated_values = dialog.getValues()
            # Update the current subtitle with the new values
            subtitle.update(updated_values)
            self.saveSubtitles()  # Save the updated subtitles
            self.populateSubtitleList()

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

    # Helper function to get milliseconds from QTime
    def time_to_milliseconds(self, qtime):
        return QTime(0, 0, 0).msecsTo(qtime)

    def milliseconds_to_time(self, ms):
        return QTime(0, 0, 0).addMSecs(int(ms))

    def saveSubtitles(self):
        """
        Save subtitles to the JSON file, ensuring no overlaps.
        """
        if self.subtitleFilePath:
            try:
                # Sort the subtitles by their start times (in milliseconds)
                self.subtitles.sort(
                    key=lambda sub: self.time_to_milliseconds(
                        QTime.fromString(sub['start'], 'hh:mm:ss.zzz')
                    )
                )

                # Ensure no overlaps
                for i in range(len(self.subtitles) - 1):
                    current_sub = self.subtitles[i]
                    next_sub = self.subtitles[i + 1]

                    # Convert start and end times to milliseconds
                    current_end_ms = self.time_to_milliseconds(
                        QTime.fromString(current_sub['end'], 'hh:mm:ss.zzz')
                    )
                    next_start_ms = self.time_to_milliseconds(
                        QTime.fromString(next_sub['start'], 'hh:mm:ss.zzz')
                    )

                    # If current subtitle's end time overlaps with the next subtitle's start time, truncate it
                    if current_end_ms >= next_start_ms:
                        truncated_end_ms = max(next_start_ms - 1, 0)  # Ensure end is slightly before the next start
                        current_sub['end'] = self.milliseconds_to_time(truncated_end_ms).toString('hh:mm:ss.zzz')

                # Save the subtitles to file
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

    def editSubtitle(self, item):
        """
        Edit a subtitle, then save the subtitles to the JSON file.
        """
        row = self.subtitleList.row(item)
        subtitle = self.subtitles[row]

        dialog = EditSubtitleDialog(subtitle, video_duration_ms=self.duration)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            updated_values = dialog.getValues()
            self.subtitles[row] = updated_values
            self.saveSubtitles()  # Save the updated subtitles
            self.populateSubtitleList()

    def playPause(self):
        """
        Toggles between play and pause.
        Re-enables snapping when the video is playing.
        """
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.mediaPlayer.pause()
            current_position = self.mediaPlayer.position()
            self.highlightCurrentSubtitle(current_position)
        else:
            self.mediaPlayer.play()

    def forward(self):
        self.mediaPlayer.setPosition(self.mediaPlayer.position() + 500)

    def backward(self):
        self.mediaPlayer.setPosition(self.mediaPlayer.position() - 500)

    def stepFrameForward(self):
        self.pauseVideo()
        new_position = self.mediaPlayer.position() + (int(1000 / self.frame_rate) * 10)
        self.mediaPlayer.setPosition(new_position)
        self.updateTimecode(new_position)

    def stepFrameBackward(self):
        self.pauseVideo()
        new_position = self.mediaPlayer.position() - (int(1000 / self.frame_rate) * 10)
        self.mediaPlayer.setPosition(new_position)
        self.updateTimecode(new_position)

    def pauseVideo(self):
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.mediaPlayer.pause()

    def updatePositionWhileSliding(self, position):
        """Called while the slider is being moved."""
        self.slider.setValue(position)
        self.updateTimecode(position)
        current_position = self.mediaPlayer.position()
        self.highlightCurrentSubtitle(current_position)
        self.scrubAudio(position, scrubbing=True)  # Short scrubbing while sliding

    def setPositionAndPause(self):
        """Called when the slider is released, and video pauses."""
        self.mediaPlayer.setPosition(self.slider.value())
        self.pauseVideo()
        current_position = self.mediaPlayer.position()
        self.highlightCurrentSubtitle(current_position)
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

        self.currentSubtitle = self.getSubtitleForTime(position)
        # self.subtitleBox.setText(self.currentSubtitle)
        self.adjustFontSizeToFit(crop_subtitle(self.currentSubtitle))
        self.subtitleBox.setText(crop_subtitle(self.currentSubtitle))

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

    def getSubtitleForTime(self, position, return_full_subtitle=False):
        """
        Retrieve the subtitle for the current playhead position.

        :param position: The current video position in milliseconds.
        :param return_full_subtitle: If True, return the full subtitle object. If False, return only the subtitle text.
        :return: The subtitle text or the full subtitle object.
        """
        current_time = QTime(0, 0, 0).addMSecs(position)
        for subtitle in self.subtitles:
            start_time = QTime.fromString(subtitle['start'], 'hh:mm:ss.zzz')
            end_time = QTime.fromString(subtitle['end'], 'hh:mm:ss.zzz')
            if start_time <= current_time <= end_time:
                return subtitle if return_full_subtitle else subtitle['text']
        return None if return_full_subtitle else ""  # Return empty string for text if no subtitle is found

    def updateButtons(self, status=None):
        """
        Updates the play/pause button icon based on the current playback state.
        """
        if self.mediaPlayer.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.playButton.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

    def generateSubtitles(self):
        if not self.currentFilePath:
            print("No video loaded")
            return

        if len(self.subtitleList) > 0:
            if not self.question_box(
                "Overwrite Subtitles",
                "Subtitles exist, overwrite?"
            ):
                return

        try:
            self.spinner = SpinnerDialog(self)  # Create the spinner dialog
            self.spinner.show()  # Show the dialog

            # Create the worker and start the external process
            self.worker = SubtitleWorker(self.currentFilePath)
            self.worker.start()

            # Create a QTimer to check periodically if the process has finished
            self.poll_timer = QTimer(self)
            self.poll_timer.timeout.connect(self.checkProcessCompletion)
            self.poll_timer.start(500)  # Check every 500 milliseconds

            # Connect the cancel button to stop the worker
            self.spinner.cancelButton.clicked.connect(self.worker.stop)
        except Exception as e:
            print(f"Error: {e}")

    def checkProcessCompletion(self):
        """Periodically checks if the subtitle generation process has finished."""
        if self.worker.is_finished():
            self.poll_timer.stop()  # Stop the timer
            self.onSubtitlesGenerated()  # Process completion callback


    def onSubtitlesGenerated(self):
        try:
            self.spinner.accept()

            self.subtitleFilePath = os.path.splitext(self.currentFilePath)[0] + ".json"

            # Clear the subtitle playlist when loading a new video
            self.subtitles = []
            self.populateSubtitleList()

            if os.path.exists(self.subtitleFilePath):
                self.loadSubtitles()
        except Exception as e:
            print(e)
            return

if __name__ == '__main__':
    app = QApplication(sys.argv)
    player = VideoPlayer()
    player.show()
    sys.exit(app.exec())
