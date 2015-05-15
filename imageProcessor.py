"""
    This file contains the image processor class
    This class gets data from the camera and does any needed image processing
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
from pymba import *
import os
import cv2
import numpy as np
import Image
import time
import shutil

# Custom imports
import settings

#####################################
# Global Variables
#####################################
camera_id_string = "DEV_000F3101DE9F"
capture_x_resolution = 2000  # These values are slightly lower than the possible resolution of the camera
capture_y_resolution = 2000  # but makes doing the composite image extremely easy later


#####################################
# Image Processor Class Definition
#####################################
class ImageProcessor(QtCore.QThread):

    images_ready_signal = QtCore.pyqtSignal()
    well_image_ready_signal = QtCore.pyqtSignal()
    camera_status_changed_signal = QtCore.pyqtSignal(str)

    local_file_cleanup_started = QtCore.pyqtSignal()
    local_file_cleanup_finished = QtCore.pyqtSignal()

    saving_composite_image_signal = QtCore.pyqtSignal()
    composite_image_saved_signal = QtCore.pyqtSignal()

    no_connection_to_remote_server_signal = QtCore.pyqtSignal()
    copying_plate_to_server_signal = QtCore.pyqtSignal()
    copying_plate_finished_signal = QtCore.pyqtSignal()

    def __init__(self, parent):
        QtCore.QThread.__init__(self)

        # Local class variables and class instantiations ##########
        self.master = parent

        self.settings = settings.program_settings

        self.overlay_offset_x = 1604
        self.overlay_offset_y = 1604

        self.composite_x_size = (11*self.settings.stitch_offset_x)+2000
        self.composite_y_size = (7*self.settings.stitch_offset_y)+2000

        self.output_filename = "A1"

        self.composite_image_PIL = None # Image.new('RGB', (self.composite_x_size, self.composite_y_size))

        self.should_clean_output_folder = False
        self.should_try_to_copy = False

        # Flags used to avoid between thread race conditions
        self.grab_well_image = False

        # Camera connection containers and instantiations
        self.vimba = Vimba()
        self.vimba_system = None
        self.camera = None
        self.frame = None

        # Raw Image Data Containers
        self.raw_image_data = None
        self.composite_raw_data = np.zeros((400, 600, 3), np.uint8)
        self.full_well_raw_data = None
        self.well_preview_raw_data = None
        self.live_view_raw_data = None

        # Display QImage Containers
        self.composite_QImage = None
        self.full_well_QImage = None
        self.well_preview_QImage = None
        self.live_view_QImage = None

        # Setup for locally used classes ##########
        self.vimba.startup()
        self.vimba_system = self.vimba.getSystem()

        # Thread run flags ##########
        self.not_abort = True

        self.connect_to_camera_flag = True
        self.wait_for_run_display_flag = False
        self.cycle_run_display_flag = False
        self.cycle_stop_flag = False

        # Class status flags ##########
        self.camera_connected = False

        # Final calls to start thread and setup class ##########
        self.connect_signals_to_slots()
        self.start()

    def connect_signals_to_slots(self):
        self.master.application_exiting_signal.connect(self.on_application_exiting_slot)

        self.images_ready_signal.connect(self.master.on_images_ready_signal_slot)
        self.camera_status_changed_signal.connect(self.master.on_camera_status_changed_slot)

        self.local_file_cleanup_started.connect(self.master.on_cleaning_up_files_slot)
        self.saving_composite_image_signal.connect(self.master.on_message_box_saving_composite_slot)
        self.copying_plate_to_server_signal.connect(self.master.on_copying_plate_to_server_slot)
        self.no_connection_to_remote_server_signal.connect(self.master.on_cannot_connect_to_remote_server_slot)

    def run(self):
        while self.not_abort:
            if self.connect_to_camera_flag:
                self.connect_to_camera()
                if not self.camera_connected:
                    self.camera_status_changed_signal.emit("Disconnected")
                    pass  # Show camera error images
                else:
                    self.camera_status_changed_signal.emit("Connected")
                    self.connect_to_camera_flag = False
                    self.wait_for_run_display_flag = True

            elif self.wait_for_run_display_flag:
                self.wait_for_run_display()

            elif self.cycle_run_display_flag:
                self.cycle_run_display()
            elif self.cycle_stop_flag:
                self.coordinated_cycle_stop()

            self.msleep(125)  # This shouldn't be less than 125 to avoid overloading the camera when getting frames


        print "Image Processing Thread Exiting..."

    def connect_to_camera(self):
        if self.vimba_system.GeVTLIsPresent:  # If cameras exist
            self.vimba_system.runFeatureCommand("GeVDiscoveryAllOnce")  # Discover all network cameras
            self.msleep(250)  # Needed so the feature has time to discover any cameras on the network before connecting

        # Attempt simple connection to camera
        try:
            self.camera = self.vimba.getCamera(camera_id_string)  # Attempt to get the desired camera
            self.camera.openCamera()  # If we were able to get it, try to open it
            self.camera_connected = True  # Looks like we're good to go, the camera is connected
        except VimbaException, e:
            print "Connect to camera error: " + e.message
            return

        # Camera connected, try to adjust settings
        try:
            # Streaming settings
            self.camera.StreamBytesPerSecond = 115000000

            # White balance settings
            self.camera.BalanceRatioAbs = .9
            self.camera.BalanceRatioSelector = 'Red'
            self.camera.BalanceWhiteAuto = 'Off'

            # Image settings
            self.camera.Width = 2000
            self.camera.Height = 2000
            self.camera.PixelFormat = 'BGR8Packed'
            self.camera.AcquisitionMode = 'SingleFrame'

            self.msleep(1)  # Wait for all settings to be made on the camera before attempting streaming

        except VimbaException, e:
            print "Error configuring camera properties: " + e.message

        # Settings configured, put camera into capture mode and set up containers
        try:
            self.frame = self.camera.getFrame()
            self.frame.announceFrame()
            self.camera.startCapture()
        except VimbaException, e:
            print "Error setting up camera for capture: " + e.message

    def quick_reconnect_camera(self):
        # Attempt simple connection to camera
        try:
            self.camera.openCamera()  # If we were able to get it, try to open it
            self.camera_connected = True  # Looks like we're good to go, the camera is connected
        except VimbaException, e:
            print "Connect to camera error: " + e.message
            return

        # Camera connected, try to adjust settings
        try:
            # Streaming settings
            self.camera.StreamBytesPerSecond = 115000000

            # White balance settings
            self.camera.BalanceRatioSelector = 'Red'
            self.camera.BalanceWhiteAutoAdjustTol = 5
            self.camera.BalanceWhiteAutoRate = 100
            self.camera.BalanceWhiteAuto = 'Continuous'

            # Image settings
            self.camera.Width = 2000
            self.camera.Height = 2000
            self.camera.PixelFormat = 'BGR8Packed'
            self.camera.AcquisitionMode = 'SingleFrame'

            self.msleep(250)  # Wait for all settings to be made on the camera before attempting streaming

        except VimbaException, e:
            print "Error configuring camera properties: " + e.message

        # Settings configured, put camera into capture mode and set up containers
        try:
            self.frame = self.camera.getFrame()
            self.frame.announceFrame()
            self.camera.startCapture()
        except VimbaException, e:
            print "Error setting up camera for capture: " + e.message

    def get_frame(self):
        try:
            self.frame.queueFrameCapture()
            self.camera.runFeatureCommand('AcquisitionStart')
            self.camera.runFeatureCommand('AcquisitionStop')
            self.frame.waitFrameCapture(1000)
            return 1
        except VimbaException, e:
            # print "Get Frame Error: " + e.message
            # print "Reconnecting to camera"
            self.disconnect_from_camera()
            # self.connect_to_camera()
            self.quick_reconnect_camera()
            return 0
        except WindowsError, e:
            print "Windows Error: " + e.message
            return 0

    def wait_for_run_display(self):
        ret = self.get_frame()
        if ret:
            self.raw_image_data = np.ndarray(buffer = self.frame.getBufferByteData(), dtype = np.uint8,
                                             shape = (self.frame.height, self.frame.width, self.frame.pixel_bytes))
            self.live_view_raw_data = cv2.resize(self.raw_image_data, (240, 240))

            height, width = self.live_view_raw_data.shape[:2]
            self.live_view_QImage = QtGui.QImage(self.live_view_raw_data,
                                                 width,
                                                 height,
                                                 QtGui.QImage.Format_RGB888)

            self.images_ready_signal.emit()

    def cycle_run_display(self):
        if self.grab_well_image:
            for i in range(0, 4):
                while (not self.get_frame()) and self.not_abort:
                    self.msleep(10)
            self.raw_image_data = np.ndarray(buffer=self.frame.getBufferByteData(), dtype=np.uint8,
                                             shape=(self.frame.height, self.frame.width, self.frame.pixel_bytes))
            # WELL PREVIEW PORTION ##########
            self.full_well_raw_data = self.raw_image_data

            self.save_well_image_to_disk()

            self.full_well_raw_data = cv2.resize(self.full_well_raw_data, (240, 240))
            height, width = self.full_well_raw_data.shape[:2]
            self.full_well_QImage = QtGui.QImage(self.full_well_raw_data,
                                                 width,
                                                 height,
                                                 QtGui.QImage.Format_RGB888)

            self.well_image_ready_signal.emit()
            self.grab_well_image = False
        else:
            while not self.get_frame():
                self.msleep(10)
            self.raw_image_data = np.ndarray(buffer=self.frame.getBufferByteData(), dtype=np.uint8,
                                             shape=(self.frame.height, self.frame.width, self.frame.pixel_bytes))

        # LIVE VIEW PORTION ##########
        # Create a re-sized version of data for live view display
        self.live_view_raw_data = cv2.resize(self.raw_image_data, (240, 240))

        # Convert this live view image data to a QImage for display on the gui
        height, width = self.live_view_raw_data.shape[:2]
        self.live_view_QImage = QtGui.QImage(self.live_view_raw_data,
                                             width,
                                             height,
                                             QtGui.QImage.Format_RGB888)

        # height, width = self.composite_raw_data.shape[:2]
        # self.composite_QImage = QtGui.QImage(self.composite_raw_data,
        #                                      width,
        #                                      height,
        #                                      QtGui.QImage.Format_RGB888)

        self.images_ready_signal.emit()

    @staticmethod
    def get_folder_size_in_rounded_gb(path):
        total_size = 0
        for dir_path, dir_names, file_names in os.walk(path):
            for f in file_names:
                fp = os.path.join(dir_path, f)
                total_size += os.path.getsize(fp)
        return int(total_size/(1 << 30))

    @staticmethod
    def delete_oldest_folder_in_path(path):
        oldest_path = -1
        oldest_time = -1
        for sub_dir in os.listdir(path):
            temp_path = path + "\\" + sub_dir

            if oldest_path == -1 and oldest_time == -1:
                oldest_path = temp_path
                oldest_time = os.path.getmtime(temp_path)
            else:
                if os.path.getmtime(temp_path) < oldest_time:
                    oldest_path = temp_path
                    oldest_time = os.path.getmtime(temp_path)

        print "Removing " + oldest_path + " with date " + time.ctime(oldest_time)
        shutil.rmtree(oldest_path)

    def perform_folder_cleanup(self, path):
        if self.get_folder_size_in_rounded_gb(path) > self.settings.local_path_max_size_GB:
            self.local_file_cleanup_started.emit()
            while self.get_folder_size_in_rounded_gb(path) > (self.settings.local_path_max_size_GB / 2):
                self.delete_oldest_folder_in_path(path)
            self.local_file_cleanup_finished.emit()

    def save_well_image_to_disk(self):
        if self.should_clean_output_folder:
            self.perform_folder_cleanup(self.settings.local_output_path)
            self.should_clean_output_folder = False

        root_path_string = self.settings.local_output_path + "\\" + str(self.settings.plate_id) + "\\" + \
            self.settings.well_images_folder_name

        full_path_string = root_path_string + "\\" + self.output_filename + ".png"
        if not os.path.isdir(root_path_string):
            os.makedirs(root_path_string)

        temp_rgb = cv2.cvtColor(self.raw_image_data, cv2.COLOR_BGR2RGB)

        # print full_path_string
        cv2.imwrite(full_path_string, temp_rgb)

        self.stitch_well_to_composite(temp_rgb)

    def stitch_well_to_composite(self, rgb_cv_image):
        rgb_cv_image = cv2.cvtColor(rgb_cv_image, cv2.COLOR_RGB2RGBA)
        temp_image = Image.fromarray(rgb_cv_image)

        self.composite_image_PIL.paste(temp_image, self.coordinates_from_name())

        scaled = self.composite_image_PIL.resize((600, 400))

        temp_cv = np.array(scaled)
        temp_cv = cv2.cvtColor(temp_cv, cv2.COLOR_RGBA2BGR)

        height, width = temp_cv.shape[:2]
        self.composite_QImage = QtGui.QImage(temp_cv,
                                             width,
                                             height,
                                             QtGui.QImage.Format_RGB888)

    def coordinates_from_name(self):
        y = ord(self.output_filename[:1])-65  # Values 1-12 turn into 0-11
        x = int(self.output_filename[1:])-1  # Values A-H turn into 0-8
        # print str(x) + " : " + str(y)

        x_value = x * self.settings.stitch_offset_x
        y_value = y * self.settings.stitch_offset_y

        return x_value, y_value

    def disconnect_from_camera(self):
        # print "Called"
        # print "crd flag: " + str(self.cycle_run_display_flag)
        if self.camera_connected and (self.wait_for_run_display_flag or self.cycle_run_display_flag) and self.not_abort:
            try:
                self.camera.endCapture()
                self.camera.revokeAllFrames()
                self.camera.closeCamera()
                # print "Camera connection closed..."
            except VimbaException, e:
                pass
                # print "Disconnect from camera error: " + e.message
        elif (not self.not_abort) and self.camera_connected:
            try:
                self.camera.closeCamera()
                self.vimba.shutdown()
            except VimbaException, e:
                pass
                # print "Disconnect from camera error: " + e.message
        else:
            pass
            # print "Nothing Happened"

    def on_coordinated_cycle_signal_slot(self):
        self.composite_image_PIL = None
        self.composite_image_PIL = Image.new('RGB', (self.composite_x_size, self.composite_y_size))
        self.composite_image_PIL.paste((0, 0, 0), (0, 0, self.composite_x_size, self.composite_y_size))

        self.composite_raw_data = np.zeros((400, 600, 3), np.uint8)

        self.should_clean_output_folder = True
        self.should_try_to_copy = False

        self.output_filename = "A1"

        self.wait_for_run_display_flag = False
        self.cycle_run_display_flag = True

    def save_composite_image(self):
        root_path_string = self.settings.local_output_path + "\\" + str(self.settings.plate_id) + "\\" + \
            self.settings.composite_image_folder_name

        full_path_string = root_path_string + "\\" + "composite_image" + ".png"
        if not os.path.isdir(root_path_string):
            os.makedirs(root_path_string)
        print "Saving composite image..."
        self.saving_composite_image_signal.emit()
        start_time = time.clock()
        self.composite_image_PIL.save(full_path_string)
        end_time = time.clock()
        print "Composite image saved in " + str(end_time-start_time) + " seconds..."
        self.composite_image_saved_signal.emit()

    def copy_plate_to_server(self):
        root_path_string = self.settings.local_output_path + "\\" + str(self.settings.plate_id)
        remote_path_string = self.settings.remote_output_path + "\\" + str(self.settings.plate_id)

        if not os.path.isdir(self.settings.remote_output_path[:3]):
            self.no_connection_to_remote_server_signal.emit()
            while not self.should_try_to_copy:
                self.msleep(300)

        self.copying_plate_to_server_signal.emit()

        try:
            if os.path.isdir(remote_path_string):
                shutil.rmtree(remote_path_string)

            shutil.copytree(root_path_string, remote_path_string)
        except:
            print "Failed to copy files to remote server!!!!"

        self.copying_plate_finished_signal.emit()

    def coordinated_cycle_stop(self):
        # self.save_composite_image()
        self.copy_plate_to_server()

        self.composite_image_PIL = None

        self.cycle_stop_flag = False
        self.wait_for_run_display_flag = True

    def on_well_image_request_signal_slot(self):
        self.grab_well_image = True

    def on_application_exiting_slot(self):
        self.not_abort = False
        self.msleep(350)  # Needed to avoid windows access violation when camera has closed but thread is still running
        self.composite_image_PIL = None
        self.disconnect_from_camera()

    def on_output_filename_changed_signal_slot(self, name):
        self.output_filename = str(name)

    def on_coordinated_cycle_stop_slot(self):
        self.cycle_run_display_flag = False
        self.cycle_stop_flag = True

    def on_ready_to_try_copying_after_fail_slot(self):
        self.should_try_to_copy = True


