#!/usr/bin/env python

"""
    Main file used to launch the auto imager gui.
    No other files should be used for launching this application.
"""

__author__ = "Corwin Perren"
__copyright__ = "None"
__credits__ = [""]
__license__ = "GPL (GNU General Public License)"
__version__ = "1.0.0"
__maintainer__ = "Corwin Perren"
__email__ = "perrenc@onid.oregonstate.edu"
__status__ = "Development"

# This file is part of Auto Imager.
#
# Auto Imager is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Auto Imager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Auto Imager.  If not, see <http://www.gnu.org/licenses/>.

#####################################
# Imports
#####################################
# Python native imports
import sys
from PyQt4 import QtCore, QtGui, uic
import signal

# Custom imports
import imageProcessor
import microscopeInterface
import captureCoordinator
import compositer
import settings


#####################################
# Global Variables
#####################################
form_class = uic.loadUiType("AutoImagerForm.ui")[0]  # Load the UI


#####################################
# MyWindowClass Definition
#####################################
class MyWindowClass(QtGui.QMainWindow, form_class):
    """ This class interfaces with PyQt4 and it's form ui system to create the main gui. """

    application_exiting_signal = QtCore.pyqtSignal()
    message_box_done = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)

        self.settings = settings.program_settings

        self.ip = imageProcessor.ImageProcessor(self)
        self.mi = microscopeInterface.MicroscopeInterface(self)
        self.cc = captureCoordinator.CaptureCoordinator(self)
        self.comp = compositer.Compositer(self)

        self.tabWidget.setCurrentIndex(0)
        self.connect_signals_to_slots()

    def connect_signals_to_slots(self):
        self.plate_id_line_edit.textChanged.connect(self.on_plate_id_changed)
        self.message_box_done.connect(self.mi.on_message_box_done_signal_slot)
        self.message_box_done.connect(self.cc.on_message_box_done_signal_slot)
        self.cc.done_percentage_changed_signal.connect(self.imaging_done_progress_bar.setValue)

    def on_message_box_power_cycle_signal_slot(self):
        msg = QtGui.QMessageBox()
        msg.setWindowTitle("Nikon Stage Power-Cycle")
        msg.setText("If well A1 is not centered in the live image box, do the following:\n" +
                    "\n1. Power off the nikon stage power supply. (Lower of the two power supplies)" +
                    "\n3. Power on the nikon stage power supply." +
                    "\n4. Wait until the stage stops moving (Indicates complete calibration)" +
                    "\n5. Hit OK to begin capture.")
        msg.setDefaultButton(QtGui.QMessageBox.Yes)
        msg.setModal(True)
        msg.exec_()

        self.message_box_done.emit()

    def on_message_box_saving_composite_slot(self):
        msg = QtGui.QProgressDialog()
        msg.setWindowTitle("Saving Composite Image")
        msg.setLabelText("Saving composite image. This process can take up to three minutes.")
        msg.setMinimum(0)
        msg.setMaximum(0)
        msg.setModal(True)
        self.comp.composite_image_saved_signal.connect(msg.close)
        msg.exec_()

    def on_copying_plate_to_server_slot(self):
        msg = QtGui.QProgressDialog()
        msg.setWindowTitle("Copying To Server")
        msg.setLabelText("Copying plate images to server. \nPlease wait.")
        msg.setMinimum(0)
        msg.setMaximum(0)
        msg.setModal(True)
        self.ip.copying_plate_finished_signal.connect(msg.close)
        msg.exec_()

    def on_cleaning_up_files_slot(self):
        msg = QtGui.QProgressDialog()
        msg.setWindowTitle("Cleaning up Local Files")
        msg.setLabelText("Freeing up space on local drive. \nPlease wait.")
        msg.setMinimum(0)
        msg.setMaximum(0)
        msg.setModal(True)
        self.ip.local_file_cleanup_finished.connect(msg.close)
        msg.exec_()

    def on_cannot_connect_to_remote_server_slot(self):
        msg = QtGui.QMessageBox()
        msg.setWindowTitle("No Connection To Server!")
        msg.setText("A connection to the remote server could not be established!\n" +
                    "\nPlease open windows explorer and verify you can access the server directly." +
                    "\nOnce you've established connectivity through windows explorer, hit okay to continue.")
        msg.setDefaultButton(QtGui.QMessageBox.Yes)
        msg.setModal(True)
        msg.buttonClicked.connect(self.ip.on_ready_to_try_copying_after_fail_slot)
        msg.exec_()

    def on_microscope_status_changed_slot(self, status):
        if status == "Connected":
            self.microscope_status_label.setText("Connected")
            self.microscope_status_label.setStyleSheet("color: green")
        elif status == "Disconnected":
            self.microscope_status_label.setText("Disconnected")
            self.microscope_status_label.setStyleSheet("color: red")

    def on_camera_status_changed_slot(self, status):
        if status == "Connected":
            self.camera_status_label.setText("Connected")
            self.camera_status_label.setStyleSheet("color: green")
        elif status == "Disconnected":
            self.camera_status_label.setText("Disconnected")
            self.camera_status_label.setStyleSheet("color: red")

    def on_plate_id_changed(self, id):
        self.settings.set_setting_string("plate_id", id)
        self.settings.set_setting_string("plate_local_path_full", (str(self.settings.local_output_path) + "\\" + str(id)))
        self.settings.set_setting_string("plate_remote_path_full", (str(self.settings.remote_output_path) + "\\" + str(id)))

        self.local_path_line_edit.setText(self.settings.plate_local_path_full)
        self.remote_path_line_edit.setText(self.settings.plate_remote_path_full)

    def on_images_ready_signal_slot(self):
        try:
            self.live_view_image_label.setPixmap(QtGui.QPixmap.fromImage(self.ip.live_view_QImage))
        except:
            pass

        try:
            self.well_preview_image_label.setPixmap(QtGui.QPixmap.fromImage(self.ip.full_well_QImage))
        except:
            pass

        try:
            self.composite_image_label.setPixmap(QtGui.QPixmap.fromImage(self.ip.composite_QImage))
        except:
            pass

    def on_compositer_image_ready_slot(self):
        try:
            self.compositer_image_label.setPixmap(QtGui.QPixmap.fromImage(self.comp.compositer_QImage))
        except:
            pass

    def on_compositer_plate_id_changed_slot(self, id):
        id = str(id)
        self.plate_path_data_label.setText(id)

    def closeEvent(self, event):
        self.application_exiting_signal.emit()
        self.ip.wait()
        self.mi.wait()
        self.cc.wait()
        event.accept()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)  # This allows the keyboard interrupt kill to work  properly
    app = QtGui.QApplication(sys.argv)  # Create the base qt gui application
    myWindow = MyWindowClass(None)  # Make a window in this application using the pnp MyWindowClass
   # myWindow.setFixedSize(1400, 900)  # Set the window to a nice resolution for viewing (Good size for 1680x1050)
    myWindow.setWindowFlags(myWindow.windowFlags() |  # Sets the windows flags to:
                            QtCore.Qt.FramelessWindowHint)  # remove the border and frame on the application
    myWindow.statusBar().setSizeGripEnabled(False)  # Disable the option to resize the window
    myWindow.show()  # Show the window in the application
    app.exec_()  # Execute launching of the application