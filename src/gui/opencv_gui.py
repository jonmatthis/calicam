# At this point I can't even recall where I copied this code from, but it is what
# actually works and drives home to me that I need to develop a better understanding
# of threads, signals, slots, events, all that as it relates to GUI development

# Moving on to pythonguis.com tutorials for just that. But this code works...

import queue
import sys
from pathlib import Path

import cv2

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, 
    QLabel, QLineEdit, QCheckBox, QScrollArea,
    QVBoxLayout, QHBoxLayout, QGridLayout)
from PyQt6.QtMultimedia import QMediaPlayer, QMediaCaptureSession, QVideoFrame
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QImage, QPixmap


# Append main repo to top of path to allow import of backend
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.concurrency_tutorial.video_stream_widget import VideoCaptureWidget

class MainWindow(QWidget):
    def __init__(self, vid_cap_widget, mp_q):
        super(MainWindow, self).__init__()
        self.q = mp_q
        self.vid_cap_widget = vid_cap_widget

        self.VBL = QVBoxLayout()

        self.FeedLabel = QLabel()
        self.VBL.addWidget(self.FeedLabel)

        self.CancelBTN = QPushButton("Cancel")
        self.CancelBTN.clicked.connect(self.CancelFeed)
        self.VBL.addWidget(self.CancelBTN)

        self.MediapipeToggle = QCheckBox("Show Mediapipe Overlay")
        self.MediapipeToggle.setCheckState(Qt.CheckState.Checked)
        self.MediapipeToggle.stateChanged.connect(self.toggle_mediapipe)

        # self.VBL.addWidget(self.mediapipeLabel)
        self.VBL.addWidget(self.MediapipeToggle)
        self.setLayout(self.VBL)

        self.vid_display = VideoDisplayWidget(vid_cap_widget)
        self.vid_display.start()
        self.vid_display.ImageUpdate.connect(self.ImageUpdateSlot)
        

    def ImageUpdateSlot(self, Image):
        self.FeedLabel.setPixmap(QPixmap.fromImage(Image))

    def CancelFeed(self):
        self.vid_display.stop()
        self.vid_cap_widget.capture.release()

    def toggle_mediapipe(self, s):
        print("Toggle Mediapipe")
        if str(s) == "0":    # Unchecked
            self.q.put(False)
        if str(s) == "2":    # Checked
            self.q.put(True)

class VideoDisplayWidget(QThread):

    ImageUpdate = pyqtSignal(QImage)
    
    def __init__(self, vid_cap_widget):
        super(VideoDisplayWidget,self).__init__()

        self.vid_cap_widget = vid_cap_widget

    def run(self):
        self.ThreadActive = True

        while self.ThreadActive:
            try:    # takes a moment for capture widget to spin up...don't error out
                self.vid_cap_widget.grab_frame()
                frame = self.vid_cap_widget.frame
                Image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                FlippedImage = cv2.flip(Image, 1)
                qt_frame = QImage(FlippedImage.data, FlippedImage.shape[1], FlippedImage.shape[0], QImage.Format.Format_RGB888)
                Pic = qt_frame.scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio)
                self.ImageUpdate.emit(Pic)

            except AttributeError:
                pass
    def stop(self):
        self.ThreadActive = False
        self.quit()

if __name__ == "__main__":
    # create a camera widget to pull in a thread of frames
    # these are currently processed by mediapipe but don't have to be
    q = queue.Queue()   
    capture_widget = VideoCaptureWidget(0,1080,640, q)

    App = QApplication(sys.argv)
    Root = MainWindow(capture_widget, q)
    Root.show()
    sys.exit(App.exec())