"""
    This file contains the capture coordinator class
    This class handles the logic behind running a full plate capture and saving the data
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
from PyQt4 import QtCore, QtGui

# Custom imports
import settings

#####################################
# Global Variables
#####################################


#####################################
# CaptureCoordinator Class Definition
#####################################
class CaptureCoordinator(QtCore.QThread):

    coordinated_cycle_start = QtCore.pyqtSignal()
    coordinated_cycle_stop = QtCore.pyqtSignal()
    done_percentage_changed_signal = QtCore.pyqtSignal(int)

    request_microscope_move_signal = QtCore.pyqtSignal(int, int)
    request_camera_image_signal = QtCore.pyqtSignal()

    def __init__(self, parent):
        QtCore.QThread.__init__(self)

        self.master = parent

        self.settings = settings.program_settings

        self.temp_well_QImage = None

        # Special flags used to make sure threads don't have race conditions
        self.is_move_complete = False
        self.is_image_ready = False
        self.xy_done_power_cycling = True
        self.stop_pressed = False


        self.not_abort = True

        self.pre_run_check_flag = False
        self.well_capture_run_flag = False

        self.connect_signals_to_slots()
        self.start()

    def connect_signals_to_slots(self):
        # Connection for when the program exits
        self.master.application_exiting_signal.connect(self.on_application_exiting_slot)

        # Connections for thread control
        self.master.capture_wells_button.clicked.connect(self.on_capture_button_pressed)
        self.master.stop_capture_button.clicked.connect(self.on_stop_capture_button_clicked_slot)

        self.coordinated_cycle_start.connect(self.master.ip.on_coordinated_cycle_signal_slot)
        self.coordinated_cycle_start.connect(self.master.mi.on_coordinated_cycle_signal_slot)

        self.coordinated_cycle_stop.connect(self.master.ip.on_coordinated_cycle_stop_slot)

        # Microscope connections
        self.request_microscope_move_signal.connect(self.master.mi.on_well_capture_move_requested_slot)
        self.master.mi.desired_move_complete.connect(self.on_move_complete_signal_slot)

        # Camera connections
        self.request_camera_image_signal.connect(self.master.ip.on_well_image_request_signal_slot)
        self.master.ip.well_image_ready_signal.connect(self.on_image_ready_signal_slot)

# TODO: Add checks for whether camera is connected
# TODO: Add checks for whether microscope is connected
# TODO: Add checks for whether local path is set and accessible
# TODO: Add checks for whether remote path is set and accessible if auto upload is enabled
# TODO: Add checks for whether the plate ID has been entered
# TODO: Add signal / slot combos for getting images during well plate cycle (Use mutex so it isn't changed when copying)

    def run(self):
        while self.not_abort:
            if self.pre_run_check_flag:
                self.pre_run_check_flag = False
                if self.pre_run_check():
                    self.well_capture_run_flag = True
                else:
                    # TODO: Show error here
                    pass

            elif self.well_capture_run_flag:
                self.well_capture_run()
                # self.well_capture_run_flag = False

            self.msleep(100)

        print "Capture Coordinator Thread Exiting..."

    def pre_run_check(self):
        return 1

    def well_capture_run(self):
        self.stop_pressed = False

        if str(self.settings.plate_id) == "None":
            self.well_capture_run_flag = False
            print "Enter plate ID"
            return

        self.coordinated_cycle_start.emit()  # Tell all threads that we're starting
        self.xy_done_power_cycling = False
        self.is_move_complete = False

        while not self.xy_done_power_cycling:
            self.msleep(50)

        if self.stop_pressed:
            self.well_capture_run_flag = False
            return

        while not self.is_move_complete:
            self.msleep(50)

        self.msleep(self.settings.image_stabilization_delay)

        self.make_well_image_request()

        for i in range(0, 95, 1):
            if self.stop_pressed:
                break
            self.make_move_request(0, 0)
            self.make_well_image_request()
            self.done_percentage_changed_signal.emit((i/96.0)*100)
            self.msleep(self.settings.image_stabilization_delay)
        self.done_percentage_changed_signal.emit(100)
        self.coordinated_cycle_stop.emit()
        self.well_capture_run_flag = False

    def make_well_image_request(self):
        self.is_image_ready = False
        self.request_camera_image_signal.emit()  # Tell the image processing thread to store a well image
        while not self.is_image_ready:
            self.msleep(10)
        self.temp_well_QImage = self.master.ip.full_well_QImage  # Copy that image here

    def make_move_request(self, x, y):
        self.is_move_complete = False
        self.request_microscope_move_signal.emit(x, y)
        while not self.is_move_complete:
            self.msleep(10)

    def on_move_complete_signal_slot(self):
        self.is_move_complete = True

    def on_image_ready_signal_slot(self):
        self.is_image_ready = True

    def on_capture_button_pressed(self):
        self.pre_run_check_flag = True

    def on_application_exiting_slot(self):
        self.not_abort = False

    def on_message_box_done_signal_slot(self):
        self.xy_done_power_cycling = True

    def on_stop_capture_button_clicked_slot(self):
        self.stop_pressed = True