"""
    This file contains the microscope interface class
    This class interfaces with and controls the Nikon Eclipse Ti microscope
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
# Things to do
#####################################
# TODO: Add handling of lost microscope during run
# TODO: Add special opencv tools to auto-calibrate well A1 position
# TODO: Add in settings

#####################################
# Imports
#####################################
# Python native imports
from PyQt4 import QtCore
import pythoncom
import win32com.client
import os
import time

#####################################
# Global Variables
#####################################
# Light Path Numerical Definitions
light_path_eye = 1
light_path_ll00 = 2
light_path_r100 = 3
light_path_l80 = 4

# Nose Piece Objective Numerical Definitions
nose_piece_1x_objective = 1
nose_piece_2x_objective = 2
nose_piece_4x_objective = 3

# Scope Pieces Name Definitions


#####################################
# Microscope Interface Class Definition
#####################################
class MicroscopeInterface(QtCore.QThread):

    power_cycle_message_box_signal = QtCore.pyqtSignal()

    microscope_status_changed_signal = QtCore.pyqtSignal(str)
    desired_move_complete = QtCore.pyqtSignal()

    output_name_changed_signal = QtCore.pyqtSignal(str)

    def __init__(self, parent):
        QtCore.QThread.__init__(self)

        self.master = parent

        os.popen("taskkill /im NikonTiS.exe /F")
        time.sleep(1)

        self.interface = None

        self.a1_x = -47742
        self.a1_y = 30885

        self.curr_x = -1
        self.curr_y = -1

        self.x_dir = 1

        self.allowable_error_xy = 8

        self.x_position = None
        self.y_position = None
        self.requested_z_position = None

        self.requested_light_intensity = None
        self.requested_objective = None

        # Flags to keep threads synced
        self.xy_done_power_cycling = False

        # Thread run flags
        self.not_abort = True

        self.connect_to_microscope_flag = True
        self.initialize_microscope_flag = False
        self.test_movement_flag = False
        self.setup_for_well_captures_flag = False
        self.user_xy_power_message_flag = False
        self.well_capture_move_requested_flag = False

        self.kill_thread = False

        # Class status flags
        self.interface_connected = False
        self.scope_hub_connected = False
        self.scope_lamp_connected = False
        self.scope_nosepiece_connected = False
        self.scope_lightpath_connected = False
        self.scope_zdrive_connected = False
        self.scope_xydrive_connected = False
        self.scope_connected_successfully = False

        self.scope_initialized = False

        self.connect_signals_to_slots()
        self.start(QtCore.QThread.TimeCriticalPriority)

    def connect_signals_to_slots(self):
        # self.master.capture_wells_button.clicked.connect(self.on_capture_wells_pressed)
        self.power_cycle_message_box_signal.connect(self.master.on_message_box_power_cycle_signal_slot)

        self.microscope_status_changed_signal.connect(self.master.on_microscope_status_changed_slot)

        self.output_name_changed_signal.connect(self.master.ip.on_output_filename_changed_signal_slot)

        self.master.application_exiting_signal.connect(self.on_application_exiting_slot)

    def run(self):
        while self.not_abort:
            # Connects the microscope to the application ##########
            if self.connect_to_microscope_flag:
                lamp_error = self.connect_to_microscope()
                if lamp_error == 25001:
                    self.connect_to_microscope()

                if not self.scope_connected_successfully:
                    self.microscope_status_changed_signal.emit("Disconnected")
                    self.show_scope_connection_error_dialog()
                else:
                    self.connect_to_microscope_flag = False
                    self.initialize_microscope_flag = True

            # Initializes the microscope back to defaults on imaging run ##########
            elif self.initialize_microscope_flag:
                self.initialize_microscope()
                if not self.scope_initialized:
                    print "How in the world did that happen......."
                else:
                    self.initialize_microscope_flag = False
                    self.microscope_status_changed_signal.emit("Connected")

            elif self.test_movement_flag:
                self.move_sequence_test()

            elif self.setup_for_well_captures_flag:
                self.setup_for_well_captures()
            elif self.user_xy_power_message_flag:
                self.user_xy_power_message()
            elif self.well_capture_move_requested_flag:
                self.well_capture_move_requested_follow_through()
            elif self.kill_thread:
                if self.scope_initialized:
                    self.deinitialize_microscope()
                self.not_abort = False
            else:
                pass  # Thread is running with nothing to do yet

            self.msleep(10)

        print "Microscope Interface Thread Exiting..."

    def connect_to_microscope(self):
        if not self.interface_connected:
            pythoncom.CoInitialize()
            self.interface = win32com.client.Dispatch("Nikon.TiScope.NikonTi")
            self.interface.Device = self.interface.Devices(1)
            self.interface.Device.WaitForDevice(10000)
            self.msleep(350)
        # TODO: New check to make sure all parts are connected
        self.scope_connected_successfully = True

    def initialize_microscope(self):
        self.interface.NosePiece.Position = nose_piece_1x_objective
        self.interface.Device.WaitForDevice(10000)
        self.msleep(100)

        self.move_to_z_position(2000)
        self.msleep(100)

        self.move_to_position(self.a1_x, self.a1_y)
        self.msleep(100)

        self.interface.LightPathDrive.Position = light_path_ll00
        self.interface.Device.WaitForDevice(10000)

        self.msleep(100)

        if not self.interface.DiaLamp.IsControlled():
            self.interface.DiaLamp.IsControlled = 1
            self.interface.Device.WaitForDevice(10000)

        self.msleep(100)

        self.interface.DiaLamp.On()
        self.interface.Device.WaitForDevice(10000)

        self.msleep(100)

        self.interface.DiaLamp.Value = 24
        self.interface.Device.WaitForDevice(10000)

        self.msleep(100)

        self.scope_initialized = True

    def deinitialize_microscope(self):
        self.interface.LightPathDrive.Position = light_path_eye
        self.interface = None

    def user_xy_power_message(self):

        self.move_to_position(self.a1_x, self.a1_y)
        self.power_cycle_message_box_signal.emit()

        while not self.xy_done_power_cycling:
            self.msleep(50)

        self.move_to_position(self.a1_x, self.a1_y)
        self.desired_move_complete.emit()
        self.user_xy_power_message_flag = False

    def show_scope_connection_error_dialog(self):
        pass

    def move_to_position(self, x, y):
        self.interface.Device.WaitForDevice(10000)

        x_position = int(int(self.interface.XDrive.Position) / 10)
        while x_position != x:
            try:
                self.interface.XDrive.Position = int(x)*10
                self.interface.Device.WaitForDevice(10000)
            except Exception, e:
                print "Exception moving X."
            x_position = int(int(self.interface.XDrive.Position) / 10)
            self.interface.Device.WaitForDevice(10000)
            self.msleep(150)

        y_position = int(int(self.interface.YDrive.Position) / 10)
        while y_position != y:
            try:
                self.interface.YDrive.Position = int(y)*10
                self.interface.Device.WaitForDevice(10000)
            except Exception, e:
                print "Exception moving Y."
            y_position = int(int(self.interface.YDrive.Position) / 10)
            self.interface.Device.WaitForDevice(10000)
            self.msleep(150)

        self.x_position = x
        self.y_position = y

    def move_to_z_position(self, z):
        z_position = int(int(self.interface.ZDrive.Position) / 40)
        while z_position != z:
            try:
                self.interface.ZDrive.Position = int(z) * 40
                self.interface.Device.WaitForDevice(10000)
            except Exception, e:
                print e
                print "Exception moving Z."
            z_position = int(int(self.interface.ZDrive.Position) / 10)
            self.interface.Device.WaitForDevice(10000)
            self.msleep(150)

    def wait_for_xy_stage(self):
        pass

    def move_to_relative_position(self, x, y):
        new_x = self.x_position + int(x)
        new_y = self.y_position + int(y)
        self.move_to_position(new_x, new_y)

    def get_position(self):
        pass

    def move_sequence_test(self):
        self.test_movement_flag = False

    def well_capture_move_requested_follow_through(self):

        if (self.curr_x == 0) and (self.curr_y == 0):
            self.move_to_relative_position(9000, 0)
            self.curr_x += 1
        elif (self.curr_x == 11) and (self.x_dir == 1):
            self.move_to_relative_position(0, -9000)
            self.curr_y += 1
            self.x_dir = 0
        elif (self.curr_x == 0) and (self.x_dir == 0):
            self.move_to_relative_position(0, -9000)
            self.curr_y += 1
            self.x_dir = 1
        elif self.x_dir:
            self.move_to_relative_position(9000, 0)
            self.curr_x += 1
        elif not self.x_dir:
            self.move_to_relative_position(-9000, 0)
            self.curr_x -= 1

        self.output_name_changed_signal.emit(chr(self.curr_y+65) + str(self.curr_x+1))
        self.desired_move_complete.emit()
        self.well_capture_move_requested_flag = False

    def on_well_capture_move_requested_slot(self, x, y):
        self.well_capture_move_requested_flag = True

    def on_coordinated_cycle_signal_slot(self):
        self.setup_for_well_captures_flag = True
        self.user_xy_power_message_flag = True

    def setup_for_well_captures(self):
        self.curr_x = 0
        self.curr_y = 0
        self.x_dir = 1
        self.setup_for_well_captures_flag = False

    def on_application_exiting_slot(self):
        self.kill_thread = True

    def on_capture_wells_pressed(self):
        self.test_movement_flag = True

    def on_message_box_done_signal_slot(self):
        self.xy_done_power_cycling = True
