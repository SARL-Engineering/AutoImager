from PyQt4 import QtCore, QtGui
import sys
import os


class MyQDirModel(QtGui.QDirModel):
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
            if self.filePath(self_index) in MyQDirModel.checked:
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
                MyQDirModel.checked.append(str(self.filePath(self_index)))
                return True
            else:
                MyQDirModel.checked.remove(str(self.filePath(self_index)))
                return True

        else:
            return QtGui.QDirModel.setData(self, self_index, value, role)

if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    tree = QtGui.QTreeView()


    local_path = "E:\\AutoImagerPlates"
    remote_path = "C:\\Users\\Public\\Pictures\\Sample Pictures"

    root_local = QtCore.QModelIndex()

    filters = QtCore.QDir.Dirs | QtCore.QDir.Readable | QtCore.QDir.NoDotAndDotDot
    dir_model = MyQDirModel(local_path, remote_path)
    dir_model.setData(root_local, QtCore.Qt.Checked, QtCore.Qt.CheckStateRole)
    dir_model.setFilter(filters)
    dir_model.setReadOnly(True)


    tree.setModel(dir_model)
    tree.setRootIndex(dir_model.index("E:\\AutoImagerPlates"))
    tree.setColumnHidden(1, True)
    tree.setColumnHidden(2, True)
    tree.setColumnHidden(3, True)
    tree.show()

    app.exec_()

    #tree.setModel(dir_model)
    tree.setRootIndex(dir_model.index("C:\\Users\\Public\\Pictures\\Sample Pictures"))
    # tree.setColumnHidden(1, True)
    # tree.setColumnHidden(2, True)
    # tree.setColumnHidden(3, True)
    tree.show()

    app.exec_()
    print dir_model.checked



# import win32com.client # Imports dll library
# nik = win32com.client.Dispatch("Nikon.TiScope.NikonTi") #Connects to dll
# nik.Device = nik.Devices(1) # Connects to the first device (0 is simulated)
#
# nik.ZDrive.Position = 0 # 1 micrometer is 40 ticks
# nik.YDrive.Position = 0 # 1 micrometer is 10 ticks
# nik.XDrive.Position = 0 # 1 micrometer is 10 ticks
# nik.NosePiece.Position = 1 # 1X Objective
# nik.LightPathDrive.Position = 2 # L100
# nik.DiaLamp.Value = 24
# nik.DiaLamp.On()
# nik.ZDrive.Position = 0 # 1 micrometer is 40 ticks
# nik.YDrive.Position = 0 # 1 micrometer is 10 ticks
# nik.XDrive.Position = 0 # 1 micrometer is 10 ticks
#
#
# nik.NosePiece.Position = 1 # 1X Objective
# nik.NosePiece.Position = 2 # 2X Objective
# nik.NosePiece.Position = 3 # 4X Objective
# nik.NosePiece.Position = 4 # NO Objective
#
# nik.LightPathDrive.Position = 1 # Eyepiece
# nik.LightPathDrive.Position = 2 # L100
# nik.LightPathDrive.Position = 3 # R100
# nik.LightPathDrive.Position = 4 # L80

# Scope Pieces Name Definitions
# scope_hub_name = 'Hub'
# scope_lamp_name = 'Lamp'
# scope_nosepiece_name = 'NosePiece'
# scope_lightpath_name = 'LightPath'
# scope_zdrive_name = 'ZDrive'
# scope_xydrive_name = 'XYDrive'
#
# import MMCorePy
# import time
#
#
#
# mmc = MMCorePy.CMMCore()
#
# mmc.loadDevice(scope_hub_name, 'NikonTI', 'TIScope')
# mmc.loadDevice(scope_xydrive_name, 'NikonTI', 'TIXYDrive')
# mmc.initializeAllDevices()
#
# while True:
#     print mmc.getSystemState()
#     time.sleep(.5)




# Something is weird with the networking aspect, and shows up using allied vision's own viewer as well... Right now the
# method to fix the camera dropping out is to disconnect from the camera and run its init sequence again. Who knows why,
# but I'm thinking of trying a new ethernet switch, better ethernet cable, and making sure all the drivers on this
# machine are completely up to date. Hopefully, nothing more is needed than that.
#
#
# Defines for later
# camera_id_string = "50-0503317504"
# camera_id_string = '02-2171A-07704'
# camera_id_string = "DEV_000F3101DE9F"
#
# from pymba import *
# import time
# import cv2
# import numpy as np
#
# vimba = Vimba()  # Get instance of vimba
# vimba.startup()  # Start vimba instance
#
# system = vimba.getSystem()  # Get vimba system
#
# if system.GeVTLIsPresent:  # If cameras exist
#     system.runFeatureCommand("GeVDiscoveryAllOnce")  # Discover all network cameras
#     time.sleep(0.25)
#
# # cameraIds = vimba.getCameraIds()  # Get camera ID's for any found on network
# # print cameraIds[0]
# camera0 = vimba.getCamera(camera_id_string)  # Get the first camera in the ID list
# camera0.openCamera()  # Open the camera
# time.sleep(.25)
# #camera0.StreamBytesPerSecond = 100000000
# time.sleep(.25)
# camera0.Width = 2000
# time.sleep(.25)
# camera0.Height = 2000
# time.sleep(.25)
# camera0.PixelFormat = "BGR8Packed"
# time.sleep(.25)
# camera0.AcquisitionMode = 'SingleFrame'  # Set camera to single frame mode
# time.sleep(.25)
#
# frame0 = camera0.getFrame()    # creates a frame
# frame0.announceFrame()  # Announce frame (not sure what this does)
#
# camera0.startCapture()
#
#
#
# def get_frame():
#     frame0.queueFrameCapture()
#     camera0.runFeatureCommand('AcquisitionStart')
#     camera0.runFeatureCommand('AcquisitionStop')
#     frame0.waitFrameCapture(1000)
#     moreUsefulImgData = np.ndarray(buffer = frame0.getBufferByteData(), dtype = np.uint8, shape = (frame0.height, frame0.width, frame0.pixel_bytes))
#     print moreUsefulImgData.shape
#     moreUsefulImgData = cv2.resize(moreUsefulImgData, (800, 800))
#
#     return moreUsefulImgData
#     pass
#
# def run_this():
#     while True:
#         try:
#             temp = get_frame()
#             ret = 1
#         except:
#             ret = 0
#             camera0.endCapture()
#             camera0.revokeAllFrames()
#
#             # close camera
#             camera0.closeCamera()
#             time.sleep(.25)
#             camera0.openCamera()  # Open the camera
#             time.sleep(.25)
#             camera0.PixelFormat = "BGR8Packed"
#             time.sleep(.25)
#             camera0.AcquisitionMode = 'SingleFrame'  # Set camera to single frame mode
#             time.sleep(.25)
#             frame0 = camera0.getFrame()    # creates a frame
#             frame0.announceFrame()  # Announce frame (not sure what this does)
#
#             camera0.startCapture()
#             pass
#
#         if ret:
#             cv2.imshow('Test', temp)
#
#         results = cv2.waitKey(10)
#
#         if results == 27: # Escape key
#             return
#
#         # try:
#         #
#         # except Exception:
#         #     print "Lost Frame Here..."
#         #     pass
#
#
# if __name__ == "__main__":
#     run_this()
#
#     # clean up after capture
#     camera0.endCapture()
#     camera0.revokeAllFrames()
#
#     # close camera
#     camera0.closeCamera()
#
#     # shutdown Vimba
#     vimba.shutdown()




# # list camera features
# cameraFeatureNames = camera0.getFeatureNames()
# for name in cameraFeatureNames:
#     print 'Camera feature:', name
#
# # get the value of a feature
# print camera0.AcquisitionMode
#
# # set the value of a feature

#
# # create new frames for the camera

# frame1 = camera0.getFrame()    # creates a second frame
#
# # announce frame

#
# # capture a camera image

#
# # ...or use NumPy for fast image display (for use with OpenCV, etc)

#






#
# # Other Definitions Needed For Later
# num_pixels_per_mm = (1032/6.8)  # This is the the value for this specific camera
#
#
#
# # Light Path Numerical Definitions
# light_path_eye = 0
# light_path_ll00 = 1
# light_path_r100 = 2
# light_path_l80 = 3
#
# # Nose Piece Objective Numerical Definitions
# nose_piece_1x_objective = 0
# nose_piece_2x_objective = 1
# nose_piece_4x_objective = 2
#
#
#
# import MMCorePy
# import time
#
# mmc = MMCorePy.CMMCore()
#
# mmc.loadDevice('Scope', 'NikonTI', 'TIScope')
# mmc.loadDevice('Lamp', 'NikonTI', 'TIDiaLamp')
# mmc.loadDevice('NosePiece', 'NikonTI', 'TINosePiece')
# mmc.loadDevice('LightPath', 'NikonTI', 'TILightPath')
# mmc.loadDevice('ZDrive', 'NikonTI', 'TIZDrive')
# mmc.loadDevice('XYDrive', 'NikonTI', 'TIXYDrive')
#
# mmc.initializeAllDevices()
#
# # mmc.getXPosition('XYDrive')
# # mmc.getYPosition('XYDrive')
#
#
# mmc.setXYPosition('XYDrive', 0, 0)  # Set bed position to origin
# time.sleep(.2)
# mmc.setPosition('ZDrive', 0)  # Set optical focus position to internal origin (Note to not let this go above 40*4000)
# time.sleep(.2)
#
#
# mmc.setProperty('NosePiece', 'State', nose_piece_1x_objective)
# time.sleep(.2)
# mmc.setProperty('LightPath', 'State', light_path_ll00)  # Set optical output to acquisition camera
# time.sleep(.2)
#
# if mmc.getProperty('Lamp', 'ComputerControl') == "Off":
#     mmc.setProperty('Lamp', 'ComputerControl', "On")
#     mmc.unloadDevice('Lamp')
#     time.sleep(1)
#     mmc.loadDevice('Lamp', 'NikonTI', 'TIDiaLamp')
#     mmc.initializeDevice('Lamp')
#
#
# mmc.setProperty('Lamp', 'State', 1)
# mmc.setProperty('Lamp', 'Intensity', 24)  # Value from 1 to 24 for intensity (Map as 0-100% later)