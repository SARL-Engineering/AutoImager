"""
    This file contains the compositer class
    This class takes a folder with well images and stitches them together into one giant image
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
import os
import Image
import time
import numpy as np
import cv2

# Custom imports
import settings

#####################################
# Global Variables
#####################################

position_dictionary = {
    "A1": "A1"
}

#####################################
# Settings Class Definition
#####################################
class CompositerQDirModel(QtGui.QDirModel):
    checked = []

    true_local_path = None
    true_remote_path = None

    local_folder_names = []
    remote_folder_names = []

    def __init__(self, local, remote):
        QtGui.QDirModel.__init__(self)
        self.true_local_path = local
        self.true_remote_path = remote
        self.update_folder_names()

    def update_folder_names(self):
        self.local_folder_names = []
        self.remote_folder_names = []

        forward_slash_local = self.true_local_path.replace("\\", "/")
        forward_slash_remote = self.true_remote_path.replace("\\", "/")

        for folder_name in os.listdir(self.true_local_path):
            self.local_folder_names.append(forward_slash_local + "/" + folder_name)

        for folder_name in os.listdir(self.true_remote_path):
            self.remote_folder_names.append(forward_slash_remote + "/" + folder_name)

    def data(self, self_index, role=QtCore.Qt.DisplayRole):
        if self_index.isValid() and (self_index.column() == 0) and (role == QtCore.Qt.CheckStateRole):
            # the item is checked only if we have stored its path
            if self.filePath(self_index) in CompositerQDirModel.checked:
                return QtCore.Qt.Checked
            else:
                if self.is_in_names_array(self.filePath(self_index)):
                    return QtCore.Qt.Unchecked
        return QtGui.QDirModel.data(self, self_index, role)

    def is_in_names_array(self, path):
        path = str(path)
        for name in self.local_folder_names:
            if name == path:
                return True

        for name in self.remote_folder_names:
            if name == path:
                return True
        return False

    def flags(self, self_index):
        if (self_index.column() == 0) and self.is_in_names_array(self.filePath(self_index)):
            return QtGui.QDirModel.flags(self, self_index) | QtCore.Qt.ItemIsUserCheckable
        else:
            return QtGui.QDirModel.flags(self, self_index)

    def setData(self, self_index, value, role=QtCore.Qt.EditRole):
        if self_index.isValid() and (self_index.column() == 0) and role == QtCore.Qt.CheckStateRole:
            # store checked paths, remove unchecked paths
            if value == QtCore.Qt.Checked:
                CompositerQDirModel.checked.append(str(self.filePath(self_index)))
                return True
            else:
                CompositerQDirModel.checked.remove(str(self.filePath(self_index)))
                return True

        else:
            return QtGui.QDirModel.setData(self, self_index, value, role)


#####################################
# Settings Class Definition
#####################################
class Compositer(QtCore.QThread):
    compositer_plate_id_changed_signal = QtCore.pyqtSignal(str)

    compositer_qimage_ready_signal = QtCore.pyqtSignal()

    saving_composite_image_signal = QtCore.pyqtSignal()
    composite_image_saved_signal = QtCore.pyqtSignal()

    def __init__(self, parent):
        QtCore.QThread.__init__(self)
        self.master = parent

        self.settings = settings.program_settings

        self.local_master_path = self.settings.local_output_path
        self.temp_master_path = self.settings.compositer_temp_path

        self.well_images_folder_name = self.settings.well_images_folder_name
        self.composite_images_folder_name = self.settings.composite_image_folder_name

        self.composite_image_PIL = None
        self.compositer_QImage = None

        self.tree = self.master.compositer_tree_view

        self.model_index = QtCore.QModelIndex()
        self.model_filters = QtCore.QDir.Dirs | QtCore.QDir.Readable | QtCore.QDir.NoDotAndDotDot
        self.cdm = CompositerQDirModel(self.local_master_path, self.temp_master_path)
        self.cdm.setData(self.model_index, QtCore.Qt.Checked, QtCore.Qt.CheckStateRole)
        self.cdm.setFilter(self.model_filters)
        self.cdm.setSorting(QtCore.QDir.Time)
        self.cdm.setReadOnly(True)

        self.tree.setModel(self.cdm)
        self.show_local_list()

        self.not_abort = True

        self.process_composites_flag = False

        self.connect_signals_to_slots()
        self.start()

    def connect_signals_to_slots(self):
        self.master.application_exiting_signal.connect(self.on_application_exiting_slot)
        self.master.tabWidget.currentChanged.connect(self.on_tab_changed_while_compositing_slot)

        self.master.compositer_combo_box.currentIndexChanged.connect(self.on_combo_box_changed_slot)

        self.master.make_composites_push_button.clicked.connect(self.on_make_composites_pressed_slot)
        self.master.cancel_composites_push_button.clicked.connect(self.on_cancel_composites_pressed_slot)

        self.compositer_plate_id_changed_signal.connect(self.master.on_compositer_plate_id_changed_slot)

        self.compositer_qimage_ready_signal.connect(self.master.on_compositer_image_ready_slot)

        self.saving_composite_image_signal.connect(self.master.on_message_box_saving_composite_slot)

    def run(self):
        while self.not_abort:
            if self.process_composites_flag:
                self.process_composites()
            self.msleep(150)

        print "Compositer Thread Exiting..."

    def coordinates_from_path(self, root, full_path):
        fixed_root = root.replace("/", "\\")
        full_path = full_path.replace(fixed_root, "")
        full_path = full_path.replace("\\", "")
        plate_name = full_path.replace(".png", "")
        # print plate_name
        y = ord(plate_name[:1])-65  # Values A-H turn into 0-8
        x = int(plate_name[1:])-1  # Turns values into index
        # print str(x) + " : " + str(y)

        x_value = x * self.settings.stitch_offset_x
        y_value = y * self.settings.stitch_offset_y

        return x_value, y_value

    def check_if_valid(self, path):
        #TODO Check that the folder exists and has the right number of images
        return os.path.isdir(path)

    def create_stitched_QImage(self):
        scaled = self.composite_image_PIL.resize((600,400))
        temp_cv = np.array(scaled)
        temp_cv = cv2.cvtColor(temp_cv, cv2.COLOR_RGBA2RGB)

        height, width = temp_cv.shape[:2]
        self.compositer_QImage = QtGui.QImage(temp_cv,
                                             width,
                                             height,
                                             QtGui.QImage.Format_RGB888)
        self.compositer_qimage_ready_signal.emit()

    def create_composite_for_path(self, path):
        well_images_path = path + "\\" + self.settings.well_images_folder_name
        images = [os.path.join(well_images_path, fn) for fn in next(os.walk(well_images_path))[2]]
        for image_path in images:
            temp_image = Image.open(image_path)
            self.composite_image_PIL.paste(temp_image, self.coordinates_from_path(well_images_path, image_path))
            self.create_stitched_QImage()

        if not os.path.isdir(path + "\\" + self.settings.composite_image_folder_name):
            os.makedirs(path + "\\" + self.settings.composite_image_folder_name)

        print "Saving composite image..."
        start_time = time.clock()
        path_to_save = path + "\\" + self.settings.composite_image_folder_name + "\\" + "composite_image.png"
        # print "Saving to: " + path_to_save
        self.saving_composite_image_signal.emit()
        self.composite_image_PIL.save(path_to_save)
        self.composite_image_saved_signal.emit()
        end_time = time.clock()
        print "Composite image saved in " + str(end_time-start_time) + " seconds..."

    def process_composites(self):
        for path in self.cdm.checked:
            self.composite_image_PIL.paste((0, 0, 0), (0, 0, self.settings.stitched_x_size, self.settings.stitched_y_size))
            # print "Compositing for path: " + path
            well_images_path = path.replace("/", "\\")
            self.compositer_plate_id_changed_signal.emit(well_images_path.split("\\")[-1])
            # print well_images_path
            if self.check_if_valid(well_images_path):
                self.create_composite_for_path(well_images_path)
            else:
                print "Could not create composite for path: " + str(path)
        self.composite_image_PIL = None
        self.clear_checked_array()
        self.process_composites_flag = False

    def show_local_list(self):
        self.tree.setRootIndex(self.cdm.index(self.local_master_path))
        self.tree.setHeaderHidden(True)
        self.tree.setColumnWidth(0, 300)
        self.tree.setColumnHidden(1, True)
        self.tree.setColumnHidden(2, True)

    def show_temp_list(self):
        self.tree.setRootIndex(self.cdm.index(self.temp_master_path))
        self.tree.setHeaderHidden(True)
        self.tree.setColumnHidden(1, True)
        self.tree.setColumnWidth(0, 300)
        self.tree.setColumnHidden(2, True)

    def on_make_composites_pressed_slot(self):
        self.composite_image_PIL = None
        self.composite_image_PIL = Image.new('RGB', (self.settings.stitched_x_size, self.settings.stitched_y_size))
        self.composite_image_PIL.paste((0, 0, 0), (0, 0, self.settings.stitched_x_size, self.settings.stitched_y_size))
        self.process_composites_flag = True

    def on_cancel_composites_pressed_slot(self):

        self.composite_image_PIL = None
        self.process_composites_flag = False

    def clear_checked_array(self):
        for i in range(len(self.cdm.checked)):
            del(self.cdm.checked[0])
        self.cdm.refresh()

    def on_tab_changed_while_compositing_slot(self):
        if self.process_composites_flag:
            self.master.tabWidget.setCurrentIndex(1)

    def on_combo_box_changed_slot(self, i):
        if i == 0:
            self.show_local_list()
        elif i == 1:
            self.show_temp_list()
        self.clear_checked_array()

    def on_application_exiting_slot(self):
        self.not_abort = False