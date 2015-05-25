"""
    This file contains the settings class
    This class is what all the other classes use to get and store system settings
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

#####################################
# Global Variables
#####################################


#####################################
# Settings Class Definition
#####################################
class Settings(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)

        # Program Settings Containers ##########
        # Temporary Live Settings
        self.plate_id = None
        self.plate_local_path_full = None
        self.plate_remote_path_full = None

        self.image_stabilization_delay = 500

        # Settings tab settings
        # - General
        # -- Output Settings
        self.auto_upload = True
        # --- Folder Names
        # ---- Well Images
        self.well_images_folder_name = "well_images"
        # ---- Composite Image
        self.composite_image_folder_name = "composite_image"
        # ---- Logs
        self.logs_folder_name = "logs"
        # ---- Temp
        self.temp_folder_name = "temp"
        # --- Folder Names
        # ---- Local Root File Path
        self.local_output_path = "E:\\AutoImagerPlates"
        # ---- Remote Root File Path
        self.remote_output_path = "Z:\\HRIC_DATA"

        # - Microscope
        # -- Z Stage Focus Value
        self.z_focus_value = 2750  # This is in micrometers
        # -- Default Objective
        self.default_objective = 1
        # -- Default Light Path
        self.default_light_path = "L100"
        # -- Default Lamp Intensity
        self.default_lamp_intensity = 100

        # Maximum size for data dir
        self.local_path_max_size_GB = 50

        # Temp directory for compositer
        self.compositer_temp_path = "E:\\CompositerTemp"

        # Compositer and preview stitch offsets
        self.stitch_offset_x = 1605
        self.stitch_offset_y = 1600

        # Composite Image Size
        self.stitched_x_size = (11*self.stitch_offset_x)+2000
        self.stitched_y_size = (7*self.stitch_offset_y)+2000

    def set_setting_string(self, setting, value):
        mutex = QtCore.QMutex()
        if setting == "plate_id":
            mutex.lock()
            self.plate_id = value
            mutex.unlock()
        elif setting == "plate_local_path_full":
            mutex.lock()
            self.plate_local_path_full = value
            mutex.unlock()
        elif setting == "plate_remote_path_full":
            mutex.lock()
            self.plate_remote_path_full = value
            mutex.unlock()

    def set_setting_number(self):
        pass

    def set_setting_checked(self):
        pass

#####################################
# Settings Class Global Instantiation
#####################################
program_settings = Settings()