import os
import glob
import unittest
import json
import logging
import vtk
import qt
import ctk
import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

import numpy as np
rng = np.random.default_rng()

try:
  import pandas as pd
except:
  slicer.util.pip_install('pandas')
  import pandas as pd

try:
  import nrrd
except:
  slicer.util.pip_install('pynrrd')
  import nrrd

import math
import time
import datetime
import random


#
# SegmentationComparison
#

class SegmentationComparison(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "SegmentationComparison"
    self.parent.categories = ["Ultrasound"]
    self.parent.dependencies = []
    self.parent.contributors = ["Tamas Ungi (Queen's University)"]
    self.parent.helpText = """
This module is for comparing volumes, and contains a built-in survey portion to record the preferences of the user.
See more information in <a href="https://github.com/keiranbarr/SegmentationComparison">module documentation</a>.
"""
    self.parent.acknowledgementText = """
This work was partially supported by the Queen's High School Internship in Computing
"""

    # Additional initialization step after application startup is complete
    slicer.app.connect("startupCompleted()", registerSampleData)

#
# Register sample data sets in Sample Data module
#


def registerSampleData():
  """
  Add data sets to Sample Data module.
  """
  # It is always recommended to provide sample data for users to make it easy to try the module,
  # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

  import SampleData
  iconsPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons')

  # To ensure that the source code repository remains small (can be downloaded and installed quickly)
  # it is recommended to store data sets that are larger than a few MB in a Github release.

  # SegmentationComparison1
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='SegmentationComparison',
    sampleName='SegmentationComparison1',
    # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
    # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
    thumbnailFileName=os.path.join(iconsPath, 'SegmentationComparison1.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
    fileNames='SegmentationComparison1.nrrd',
    # Checksum to ensure file integrity. Can be computed by this command:
    #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
    checksums='SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95',
    # This node name will be used when the data set is loaded
    nodeNames='SegmentationComparison1'
  )

  # SegmentationComparison2
  SampleData.SampleDataLogic.registerCustomSampleDataSource(
    # Category and sample name displayed in Sample Data module
    category='SegmentationComparison',
    sampleName='SegmentationComparison2',
    thumbnailFileName=os.path.join(iconsPath, 'SegmentationComparison2.png'),
    # Download URL and target file name
    uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
    fileNames='SegmentationComparison2.nrrd',
    checksums='SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97',
    # This node name will be used when the data set is loaded
    nodeNames='SegmentationComparison2'
  )


# https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#override-application-close-behavior
class CloseApplicationEventFilter(qt.QWidget):
  def eventFilter(self, object, event):
    if event.type() == qt.QEvent.Close:
      event.accept()
      return True
    return False


#
# SegmentationComparisonWidget
#


class SegmentationComparisonWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  LAST_INPUT_PATH_SETTING = "SegmentationComparison/LastInputPath"
  LAST_OUTPUT_PATH_SETTING = "SegmentationComparison/LastOutputPath"
  LAST_CSV_PATH_SETTING = "SegmentationComparison/LastCSVPath"
  THRESHOLD_SLIDER_MIDDLE_VALUE = 0.5  # range 0..1
  ICON_SIZE_MID = 42
  ICON_SIZE = 54

  LAYOUT_DUAL_3D = 876
  LAYOUT_DUAL_MULTIPLE_2D = 877

  THRESHOLD_SLIDER_RESOLUTION = 300  # Must be positive integer

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    slicer.mymod = self  # for debugging in Slicer
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False
    self.sceneImporting = False

    self.comparisonResultsTable = None  # Only use this while importing saved scene from file!
    self.eloHistoryTable = None
    self.lastLeftForegroundOpacity = 0
    self.lastRightForegroundOpacity = 0

    # Shortcuts
    self.shortcutD = qt.QShortcut(slicer.util.mainWindow())
    self.shortcutD.setKey(qt.QKeySequence("d"))

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    uiWidget = slicer.util.loadUI(
      self.resourcePath('UI/SegmentationComparison.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = SegmentationComparisonLogic()

    # Connections

    # These connections ensure that we update parameter node when scene is closed

    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    # Observers for beginning and end of loading a previously saved scene

    self.removeObservers(self.onSceneImportStart)
    self.addObserver(slicer.mrmlScene, slicer.vtkMRMLScene.StartImportEvent, self.onSceneImportStart)
    self.removeObservers(self.onSceneImportEnd)
    self.addObserver(slicer.mrmlScene, slicer.vtkMRMLScene.EndImportEvent, self.onSceneImportEnd)

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).

    # Left side opacity slider

    self.ui.leftThresholdSlider.setMinimum(0)
    self.ui.leftThresholdSlider.setMaximum(self.THRESHOLD_SLIDER_RESOLUTION)
    self.ui.leftThresholdSlider.connect("valueChanged(int)", self.onLeftSliderChanged)
    self.ui.leftThresholdSlider.setValue(int(self.THRESHOLD_SLIDER_RESOLUTION * self.THRESHOLD_SLIDER_MIDDLE_VALUE))

    thresholdPercentage = self.getThresholdPercentage(self.ui.leftThresholdSlider.value)
    self.ui.thresholdPercentageLabel.text = str(int(thresholdPercentage)) + "%"

    # Right side opacity slider

    self.ui.rightThresholdSlider.setMinimum(0)
    self.ui.rightThresholdSlider.setMaximum(self.THRESHOLD_SLIDER_RESOLUTION)
    self.ui.rightThresholdSlider.connect("valueChanged(int)", self.onRightSliderChanged)
    self.ui.rightThresholdSlider.setValue(int(self.THRESHOLD_SLIDER_RESOLUTION * self.THRESHOLD_SLIDER_MIDDLE_VALUE))

    rightThresholdPercentage = self.getThresholdPercentage(self.ui.rightThresholdSlider.value)
    self.ui.rightThresholdLabel.text = str(int(rightThresholdPercentage)) + "%"

    # Other widgets

    self.ui.linkThresholdsButton.connect('toggled(bool)', self.onLinkOpacitiesToggled)

    lastInputPath = slicer.util.settingsValue(self.LAST_INPUT_PATH_SETTING, "")
    if lastInputPath != "":
      self.ui.inputDirectorySelector.directory = lastInputPath

    lastOutputPath = slicer.util.settingsValue(self.LAST_OUTPUT_PATH_SETTING, "")
    if lastOutputPath != "":
      self.ui.outputDirectorySelector.directory = lastOutputPath

    # Make some collapsible buttons exclusive

    self.ui.inputsCollapsibleButton.connect('contentsCollapsed(bool)', self.onInputsCollapsed)
    self.ui.comparisonCollapsibleButton.connect('contentsCollapsed(bool)', self.onComparisonCollapsed)
    self.ui.inputsCollapsibleButton.collapsed = False
    self.ui.comparisonCollapsibleButton.collapsed = True

    # Set up button connections and icons

    self.ui.inputTypeButtonGroup.connect("buttonClicked(QAbstractButton*)", self.onInputTypeChanged)
    self.ui.csvPathSelector.connect("currentPathChanged(const QString)", self.onCSVPathChanged)
    self.ui.clearCSVPathButton.connect("clicked()", self.onClearButtonPressed)
    self.ui.inputDirectorySelector.connect("directoryChanged(const QString)", self.onInputVolumeDirectorySelected)
    inputPushButton = self.ui.inputDirectorySelector.findChild("QPushButton")
    inputPushButton.setIconSize(qt.QSize(self.ICON_SIZE_MID, self.ICON_SIZE_MID))
    self.ui.loadButton.connect('clicked()', self.onLoadButton)
    self.ui.loadButton.setIconSize(qt.QSize(self.ICON_SIZE_MID, self.ICON_SIZE_MID))

    self.ui.inputsCollapsibleButton.setIconSize(qt.QSize(self.ICON_SIZE, self.ICON_SIZE))
    self.ui.comparisonCollapsibleButton.setIconSize(qt.QSize(self.ICON_SIZE, self.ICON_SIZE))
    self.ui.settingsCollapsibleButton.setIconSize(qt.QSize(self.ICON_SIZE, self.ICON_SIZE))

    self.ui.toggleOverlayPushButton.connect("clicked()", self.onOverlayToggled)
    self.ui.resetCameraButton.connect('clicked()', self.onResetCameraButton)
    self.ui.resetCameraButton.setIconSize(qt.QSize(self.ICON_SIZE_MID, self.ICON_SIZE_MID))
    self.ui.leftBetterButton.connect('clicked()', self.onLeftBetterClicked)
    self.ui.leftBetterButton.setIconSize(qt.QSize(int(self.ICON_SIZE * 1.5), self.ICON_SIZE))
    self.ui.leftBetterButton.setText("")
    self.ui.rightBetterButton.connect('clicked()', self.onRightBetterClicked)
    self.ui.rightBetterButton.setIconSize(qt.QSize(int(self.ICON_SIZE * 1.5), self.ICON_SIZE))
    self.ui.rightBetterButton.setText("")
    self.ui.equalButton.connect('clicked()', self.onEqualClicked)
    self.ui.equalButton.setIconSize(qt.QSize(self.ICON_SIZE, self.ICON_SIZE))
    self.ui.equalButton.setText("")
    self.ui.saveButton.connect('clicked()', self.onSaveButton)
    self.ui.saveButton.setIconSize(qt.QSize(self.ICON_SIZE, self.ICON_SIZE))

    # Add icons to buttons

    settings = slicer.app.userSettings()
    styleSetting = settings.value("Styles/Style")
    if styleSetting[:4].lower() == "dark":
      self.ui.loadButton.setIcon(qt.QIcon(self.logic.resourcePath("Icons/input_dark_48px.svg")))
      self.ui.leftBetterButton.setIcon(qt.QIcon(self.logic.resourcePath("Icons/left_side_better_dark_72px.svg")))
      self.ui.rightBetterButton.setIcon(qt.QIcon(self.logic.resourcePath("Icons/right_side_better_dark_72px.svg")))
      self.ui.equalButton.setIcon(qt.QIcon(self.logic.resourcePath("Icons/equal_dark_48px.svg")))
      self.ui.saveButton.setIcon(qt.QIcon(self.logic.resourcePath("Icons/save_alt_dark_48px.svg")))
    else:
      self.ui.loadButton.setIcon(qt.QIcon(self.logic.resourcePath("Icons/input_48px.svg")))
      self.ui.leftBetterButton.setIcon(qt.QIcon(self.logic.resourcePath("Icons/left_side_better_72px.svg")))
      self.ui.rightBetterButton.setIcon(qt.QIcon(self.logic.resourcePath("Icons/right_side_better_72px.svg")))
      self.ui.equalButton.setIcon(qt.QIcon(self.logic.resourcePath("Icons/equal_48px.svg")))
      self.ui.saveButton.setIcon(qt.QIcon(self.logic.resourcePath("Icons/save_alt_48px.svg")))

    # Settings

    self.ui.outputDirectorySelector.connect("directoryChanged(const QString)", self.onOutputDirectorySelected)

    showIds = slicer.util.settingsValue(self.logic.SHOW_IDS_SETTING, self.logic.SHOW_IDS_DEFAULT, converter=slicer.util.toBool)
    self.ui.displayIdCheckBox.checked = showIds
    self.ui.displayIdCheckBox.connect("stateChanged(int)", self.onDisplayIdChecked)

    fov = slicer.util.settingsValue(self.logic.CAMERA_FOV_SETTING, self.logic.CAMERA_FOV_DEFAULT, converter=int)
    self.ui.fovSpinBox.value = fov
    self.ui.fovSpinBox.connect("valueChanged(int)", self.onFovValueChanged)

    self.ui.resetSettingsButton.connect("clicked()", self.onResetSettingsClicked)

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()

    self.addCustomLayouts()

  def addCustomLayouts(self):
    layoutLogic = slicer.app.layoutManager().layoutLogic()

    dual3dLayout = \
      """
      <layout type="horizontal">
        <item>
          <view class="vtkMRMLViewNode" singletontag="1">
            <property name="viewLabel" action="default">1</property>
          </view>
        </item>
        <item>
          <view class="vtkMRMLViewNode" singletontag="2" type="secondary">
            <property name="viewlabel" action="default">2</property>
          </view>
        </item>
      </layout>
      """
    if not layoutLogic.GetLayoutNode().SetLayoutDescription(self.LAYOUT_DUAL_3D, dual3dLayout):
      layoutLogic.GetLayoutNode().AddLayoutDescription(self.LAYOUT_DUAL_3D, dual3dLayout)

    # Add custom layout to standard layout selector menu
    mainWindow = slicer.util.mainWindow()
    viewToolBar = mainWindow.findChild('QToolBar', 'ViewToolBar')
    layoutMenu = viewToolBar.widgetForAction(viewToolBar.actions()[0]).menu()
    layoutSwitchActionParent = layoutMenu

    layoutSwitchAction = layoutSwitchActionParent.addAction("3D segmentation comparison")
    layoutSwitchAction.setData(self.LAYOUT_DUAL_3D)
    layoutSwitchAction.setIcon(qt.QIcon(':Icons/Go.png'))
    layoutSwitchAction.setToolTip('Dual 3D comparison')

    # Dual layout with 6 2D slices in each
    dual2dLayout = \
      """
      <layout type="horizontal">
        <item>
          <layout type="vertical">
            <item>
              <layout type="horizontal">
                <item>
                  <view class="vtkMRMLSliceNode" singletontag="11">
                    <property name="orientation" action="default">Axial</property>
                    <property name="viewlabel" action="default">11</property>
                    <property name="viewcolor" action="default">#F34A33</property>
                  </view>
                </item>
                <item>
                  <view class="vtkMRMLSliceNode" singletontag="12">
                    <property name="orientation" action="default">Axial</property>
                    <property name="viewlabel" action="default">12</property>
                    <property name="viewcolor" action="default">#F34A33</property>
                  </view>
                </item>
                <item>
                  <view class="vtkMRMLSliceNode" singletontag="13">
                    <property name="orientation" action="default">Axial</property>
                    <property name="viewlabel" action="default">13</property>
                    <property name="viewcolor" action="default">#F34A33</property>
                  </view>
                </item>
              </layout>
            </item>
            <item>
              <layout type="horizontal">
                <item>
                  <view class="vtkMRMLSliceNode" singletontag="14">
                    <property name="orientation" action="default">Axial</property>
                    <property name="viewlabel" action="default">14</property>
                    <property name="viewcolor" action="default">#F34A33</property>
                  </view>
                </item>
                <item>
                  <view class="vtkMRMLSliceNode" singletontag="15">
                    <property name="orientation" action="default">Axial</property>
                    <property name="viewlabel" action="default">15</property>
                    <property name="viewcolor" action="default">#F34A33</property>
                  </view>
                </item>
                <item>
                  <view class="vtkMRMLSliceNode" singletontag="16">
                    <property name="orientation" action="default">Axial</property>
                    <property name="viewlabel" action="default">16</property>
                    <property name="viewcolor" action="default">#F34A33</property>
                  </view>
                </item>
              </layout>
            </item>
          </layout>
        </item>
        <item>
          <layout type="vertical">
            <item>
              <layout type="horizontal">
                <item>
                  <view class="vtkMRMLSliceNode" singletontag="21">
                    <property name="orientation" action="default">Axial</property>
                    <property name="viewlabel" action="default">21</property>
                    <property name="viewcolor" action="default">#6EB14B</property>
                  </view>
                </item>
                <item>
                  <view class="vtkMRMLSliceNode" singletontag="22">
                    <property name="orientation" action="default">Axial</property>
                    <property name="viewlabel" action="default">22</property>
                    <property name="viewcolor" action="default">#6EB14B</property>
                  </view>
                </item>
                <item>
                  <view class="vtkMRMLSliceNode" singletontag="23">
                    <property name="orientation" action="default">Axial</property>
                    <property name="viewlabel" action="default">23</property>
                    <property name="viewcolor" action="default">#6EB14B</property>
                  </view>
                </item>
              </layout>
            </item>
            <item>
              <layout type="horizontal">
                <item>
                  <view class="vtkMRMLSliceNode" singletontag="24">
                    <property name="orientation" action="default">Axial</property>
                    <property name="viewlabel" action="default">24</property>
                    <property name="viewcolor" action="default">#6EB14B</property>
                  </view>
                </item>
                <item>
                  <view class="vtkMRMLSliceNode" singletontag="25">
                    <property name="orientation" action="default">Axial</property>
                    <property name="viewlabel" action="default">25</property>
                    <property name="viewcolor" action="default">#6EB14B</property>
                  </view>
                </item>
                <item>
                  <view class="vtkMRMLSliceNode" singletontag="26">
                    <property name="orientation" action="default">Axial</property>
                    <property name="viewlabel" action="default">26</property>
                    <property name="viewcolor" action="default">#6EB14B</property>
                  </view>
                </item>
              </layout>
            </item>
          </layout>
        </item>
      </layout>
      """
    if not layoutLogic.GetLayoutNode().SetLayoutDescription(self.LAYOUT_DUAL_MULTIPLE_2D, dual2dLayout):
      layoutLogic.GetLayoutNode().AddLayoutDescription(self.LAYOUT_DUAL_MULTIPLE_2D, dual2dLayout)

    layoutSwitchAction = layoutSwitchActionParent.addAction("2D segmentation comparison")
    layoutSwitchAction.setData(self.LAYOUT_DUAL_MULTIPLE_2D)
    layoutSwitchAction.setIcon(qt.QIcon(':Icons/Go.png'))
    layoutSwitchAction.setToolTip('Dual 2D comparison')

  def onResetSettingsClicked(self):
    logging.info("onResetSettingsClicked()")
    self.ui.displayIdCheckBox.checked = self.logic.SHOW_IDS_DEFAULT
    self.ui.fovSpinBox.value = self.logic.CAMERA_FOV_DEFAULT

  def onFovValueChanged(self, value):
    logging.info("onFovValueChanged({})".format(value))
    settings = slicer.app.userSettings()
    settings.setValue(self.logic.CAMERA_FOV_SETTING, str(value))
    self.logic.prepareDisplay(self.ui.leftThresholdSlider.value, self.ui.rightThresholdSlider.value)

  def onDisplayIdChecked(self, checked):
    logging.info("onDisplayIdChecked({})".format(checked))
    settings = slicer.app.userSettings()
    if checked != 0:
      settings.setValue(self.logic.SHOW_IDS_SETTING, "true")
      settings.setValue(self.logic.SHOW_SLICE_ANNOTATIONS_SETTING, 1)
    else:
      settings.setValue(self.logic.SHOW_IDS_SETTING, "false")
      settings.setValue(self.logic.SHOW_SLICE_ANNOTATIONS_SETTING, 0)
    self.logic.prepareDisplay(self.ui.leftThresholdSlider.value, self.ui.rightThresholdSlider.value)

  def onInputsCollapsed(self, collapsed):
    if collapsed == False:
      self.ui.comparisonCollapsibleButton.collapsed = True

  def onComparisonCollapsed(self, collapsed):
    if collapsed == False:
      self.ui.inputsCollapsibleButton.collapsed = True

  def onInputTypeChanged(self, button):
    layoutManager = slicer.app.layoutManager()
    if button == self.ui.threeDRadioButton:
      self._parameterNode.SetParameter(self.logic.INPUT_TYPE, "3D")

      layoutManager.setLayout(self.LAYOUT_DUAL_3D)
      viewNode1 = slicer.mrmlScene.GetSingletonNode("1", "vtkMRMLViewNode")
      viewNode1.SetOrientationMarkerType(viewNode1.OrientationMarkerTypeHuman)
      viewNode1.SetOrientationMarkerSize(viewNode1.OrientationMarkerSizeSmall)

      viewNode2 = slicer.mrmlScene.GetSingletonNode("2", "vtkMRMLViewNode")
      viewNode2.SetOrientationMarkerType(viewNode2.OrientationMarkerTypeHuman)
      viewNode2.SetOrientationMarkerSize(viewNode2.OrientationMarkerSizeSmall)

      self.ui.toggleOverlayPushButton.enabled = False
      self.disconnectKeyboardShortcut()
    else:
      self._parameterNode.SetParameter(self.logic.INPUT_TYPE, "2D")

      # Prevent user from changing slices in 2D views
      layoutManager.setLayout(self.LAYOUT_DUAL_MULTIPLE_2D)
      for i in range(1, 3):
        for j in range(1, 7):
          sliceName = str(i) + str(j)
          interactorStyle = layoutManager.sliceWidget(sliceName).sliceView().sliceViewInteractorStyle()
          interactorStyle.SetActionEnabled(interactorStyle.BrowseSlice, False)
      
      # Enable overlay toggle
      self.ui.toggleOverlayPushButton.enabled = True
      self.connectKeyboardShortcut()

  # set the output directory to the input directory as a default
  def onInputVolumeDirectorySelected(self, selectedPath):
    logging.info(f"onInputVolumeDirectorySelected({selectedPath})")
    settings = qt.QSettings()
    settings.setValue(self.LAST_INPUT_PATH_SETTING, selectedPath)

    if not self.ui.csvPathSelector.currentPath:
      self.ui.outputDirectorySelector.directory = selectedPath
      settings.setValue(self.LAST_OUTPUT_PATH_SETTING, selectedPath)

    self.updateParameterNodeFromGUI()

  def onCSVPathChanged(self, selectedPath):
    if selectedPath:
      logging.info(f"onCSVPathChanged({selectedPath}")
      settings = qt.QSettings()
      settings.setValue(self.LAST_CSV_PATH_SETTING, selectedPath)
      # Change output csv save path to match loaded csv
      lastOutputPath = os.path.abspath(os.path.join(selectedPath, os.pardir))
      self.ui.outputDirectorySelector.directory = lastOutputPath
      settings.setValue(self.LAST_OUTPUT_PATH_SETTING, lastOutputPath)

    self.updateParameterNodeFromGUI()

  def onClearButtonPressed(self):
    logging.info("onClearButtonPressed()")
    if self.ui.csvPathSelector.currentPath is None:
      return
    self.ui.csvPathSelector.currentPath = ""

  def onOutputDirectorySelected(self, selectedPath):
    logging.info(f"onOutputDirectorySelected({selectedPath})")
    settings = qt.QSettings()
    settings.setValue(self.LAST_OUTPUT_PATH_SETTING, selectedPath)
    self.updateParameterNodeFromGUI()

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()

  def enter(self):
    """
    Called each time the user opens this module.
    """
    # Make sure parameter node exists and observed
    self.initializeParameterNode()
    slicer.util.setDataProbeVisible(False)  # We don't use data probe, and it takes valuable space from widget.

    if self._parameterNode.GetParameter(self.logic.INPUT_TYPE) == "3D":
      slicer.app.layoutManager().setLayout(self.LAYOUT_DUAL_3D)  # Setting this layout creates all views automatically

      viewNode1 = slicer.mrmlScene.GetSingletonNode("1", "vtkMRMLViewNode")
      viewNode1.SetOrientationMarkerType(viewNode1.OrientationMarkerTypeHuman)
      viewNode1.SetOrientationMarkerSize(viewNode1.OrientationMarkerSizeSmall)

      viewNode2 = slicer.mrmlScene.GetSingletonNode("2", "vtkMRMLViewNode")
      viewNode2.SetOrientationMarkerType(viewNode2.OrientationMarkerTypeHuman)
      viewNode2.SetOrientationMarkerSize(viewNode2.OrientationMarkerSizeSmall)
    else:
      slicer.app.layoutManager().setLayout(self.LAYOUT_DUAL_MULTIPLE_2D)
      self.connectKeyboardShortcut()

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(
      self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    slicer.util.setDataProbeVisible(True)
    self.disconnectKeyboardShortcut()

  def onSceneStartClose(self, caller, event):
    """
    Called just before the scene is closed.
    """
    # Parameter node will be reset, do not use it anymore
    self.setParameterNode(None)

  def onSceneEndClose(self, caller, event):
    """
    Called just after the scene is closed.
    """
    # If this module is shown while the scene is closed then recreate a new parameter node immediately
    if self.parent.isEntered:
      self.initializeParameterNode()

  def onSceneImportStart(self, caller=None, event=None):
    self.sceneImporting = True
    parameterNode = self.getParameterNode()
    self.comparisonResultsTable = parameterNode.GetNodeReference(self.logic.SURVEY_RESULTS_TABLE)
    self.eloHistoryTable = parameterNode.GetNodeReference(self.logic.ELO_HISTORY_TABLE)

  def onSceneImportEnd(self, caller=None, event=None):
    qt.QTimer.singleShot(0, self.finishImportingScene)  # Put this call in Qt event loop so it is not executed too early

  def finishImportingScene(self):
    """
    Call this function to handle duplicate nodes after loading a scene from files.
    :returns: None
    """
    parameterNode = self.getParameterNode()

    # Keep new tables and remove old ones, because this module only handles one session at a time

    currentResultsTable = parameterNode.GetNodeReference(self.logic.SURVEY_RESULTS_TABLE)
    if self.comparisonResultsTable != currentResultsTable:
      slicer.mrmlScene.RemoveNode(self.comparisonResultsTable)
      self.comparisonResultsTable = currentResultsTable

    currentEloHistoryTable = parameterNode.GetNodeReference(self.logic.ELO_HISTORY_TABLE)
    if self.eloHistoryTable != currentEloHistoryTable:
      slicer.mrmlScene.RemoveNode(self.eloHistoryTable)
      self.eloHistoryTable = currentEloHistoryTable

    self.sceneImporting = False

  def initializeParameterNode(self):
    """
    Ensure parameter node exists and observed.
    """
    # Parameter node stores all user choices in parameter values, node selections, etc.
    # so that when the scene is saved and reloaded, these settings are restored.

    self.setParameterNode(self.logic.getParameterNode())

  def setParameterNode(self, inputParameterNode):
    """
    Set and observe parameter node.
    Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
    """

    if inputParameterNode:
      self.logic.setDefaultParameters(inputParameterNode)

    # Unobserve previously selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.

    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    self._parameterNode = inputParameterNode

    if self._parameterNode is not None:
      self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    self.updateGUIFromParameterNode()  # Initial GUI update

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    self._updatingGUIFromParameterNode = True  # Prevent recursion

    leftSliderValue = self.logic.getParameter(self.logic.LEFT_OPACITY_THRESHOLD) * self.THRESHOLD_SLIDER_RESOLUTION
    self.ui.leftThresholdSlider.value = leftSliderValue
    rightSliderValue = self.logic.getParameter(self.logic.RIGHT_OPACITY_THRESHOLD) * self.THRESHOLD_SLIDER_RESOLUTION
    self.ui.rightThresholdSlider.value = rightSliderValue
    self.ui.linkThresholdsButton.checked = self.logic.getParameter(self.logic.LINK_OPACITIES)

    self._updatingGUIFromParameterNode = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    leftSliderParameterValue = self.ui.leftThresholdSlider.value / self.THRESHOLD_SLIDER_RESOLUTION
    self._parameterNode.SetParameter(self.logic.LEFT_OPACITY_THRESHOLD, str(leftSliderParameterValue))
    rightSlicerParameterValue = self.ui.rightThresholdSlider.value / self.THRESHOLD_SLIDER_RESOLUTION
    self._parameterNode.SetParameter(self.logic.RIGHT_OPACITY_THRESHOLD, str(rightSlicerParameterValue))
    self._parameterNode.SetParameter(self.logic.LINK_OPACITIES, str(self.ui.linkThresholdsButton.checked))

    self._parameterNode.EndModify(wasModified)
  
  def connectKeyboardShortcut(self):
    self.shortcutD.connect("activated()", self.onOverlayToggled)

  def disconnectKeyboardShortcut(self):
    if self.shortcutD:
      self.shortcutD.activated.disconnect()

  # Threshold the selected volume(s)
  def onLeftSliderChanged(self, value):
    """
    Callback function for left side threshold slider.
    @param value: expected to have minimum value of 0.0, and maximum of logic.THRESHOLD_SLIDER_RESOLUTION
    @return: None
    """
    thresholdPercentage = self.getThresholdPercentage(value)
    self.ui.thresholdPercentageLabel.text = str(round(thresholdPercentage)) + "%"

    if self.ui.linkThresholdsButton.checked == True and self.ui.rightThresholdSlider.value != value:
      self.ui.rightThresholdSlider.value = value

    nextPair = self.logic.getNextPair()
    if nextPair is None:
      logging.info("Not updating volume rendering, because volumes are not displayed yet")
      return

    try:
      volumeName = self.logic.nameFromPatientSequenceAndModel(nextPair[0], nextPair[1])
      inputVolume = self._parameterNode.GetNodeReference(volumeName)
      if inputVolume is not None:
        self.logic.setVolumeOpacityThreshold(inputVolume, thresholdPercentage)
        self.logic.setSlicePredictionOpacity(1, thresholdPercentage)
      else:
        logging.warning("Volume not found by reference: {}".format(volumeName))
    except Exception as e:
      slicer.util.errorDisplay("Failed to threshold the selected volume(s): "+str(e))
      import traceback
      traceback.print_exc()

    self.updateParameterNodeFromGUI()

  def onRightSliderChanged(self, value):
    """
    Callback function for right side slider widget.
    :param value: new slider value
    :returns: None
    """
    thresholdPercentage = self.getThresholdPercentage(value)
    self.ui.rightThresholdLabel.text = str(round(thresholdPercentage)) + "%"

    if self.ui.linkThresholdsButton.checked == True and self.ui.leftThresholdSlider.value != value:
      self.ui.leftThresholdSlider.value = value

    nextPair = self.logic.getNextPair()
    if nextPair is None:
      logging.info("Not updating volume rendering, because volumes are not displayed yet")
      return

    try:
      volumeName = self.logic.nameFromPatientSequenceAndModel(nextPair[0], nextPair[2])
      inputVolume = self._parameterNode.GetNodeReference(volumeName)
      if inputVolume is not None:
        self.logic.setVolumeOpacityThreshold(inputVolume, thresholdPercentage)
        self.logic.setSlicePredictionOpacity(2, thresholdPercentage)
      else:
        logging.warning("Volume not found by reference: {}".format(volumeName))
    except Exception as e:
      slicer.util.errorDisplay("Failed to threshold the selected volume(s): "+str(e))
      import traceback
      traceback.print_exc()

    self.updateParameterNodeFromGUI()

  def getThresholdPercentage(self, value):
    """
    Returns the slider value as a percentage of the total range (0..100).
    @param value: slider value directly from slider widget
    @return: value scaled between 0 and 100.
    """
    minimumValue = self.ui.leftThresholdSlider.minimum
    maximumValue = self.ui.leftThresholdSlider.maximum
    thresholdPercentage = value / (maximumValue - minimumValue) * 100.0
    return thresholdPercentage

  def onLinkOpacitiesToggled(self, toggled):
    """
    Callback function for link button.
    :returns: None
    """
    self.logic.setParameter(self.logic.LINK_OPACITIES, toggled)

    if toggled:
      self.ui.rightThresholdSlider.value = self.ui.leftThresholdSlider.value
  
  def onOverlayToggled(self):
    leftOpacityCurrent = self.ui.leftThresholdSlider.value
    rightOpacityCurrent = self.ui.rightThresholdSlider.value

    if leftOpacityCurrent == 0 and rightOpacityCurrent == 0:
      # Bring back sliders to previous values
      self.ui.leftThresholdSlider.value = self.lastLeftForegroundOpacity
      self.ui.rightThresholdSlider.value = self.lastRightForegroundOpacity
    elif leftOpacityCurrent > 0 and rightOpacityCurrent == 0:
      # Hide left side
      self.lastLeftForegroundOpacity = leftOpacityCurrent
      self.ui.leftThresholdSlider.value = 0
    elif rightOpacityCurrent > 0 and leftOpacityCurrent == 0:
      # Hide right side
      self.lastRightForegroundOpacity = rightOpacityCurrent
      self.ui.rightThresholdSlider.value = 0
    else:
      self.lastLeftForegroundOpacity = leftOpacityCurrent
      self.lastRightForegroundOpacity = rightOpacityCurrent
      self.ui.leftThresholdSlider.value = 0
      self.ui.rightThresholdSlider.value = 0

  def onLoadButton(self):
    """
    Callback function for load button.
    :returns: None
    """
    logging.info("onLoadButton()")
    if self.logic.surveyStarted:
      confirmation = slicer.util.confirmYesNoDisplay("WARNING: This will delete all survey progress. Proceed?")
    else:
      confirmation = True

    if confirmation:
      waitDialog = qt.QDialog(slicer.util.mainWindow())
      waitDialog.setWindowTitle('SegmentationComparison')
      waitDialog.setModal(True)
      waitDialog.setWindowFlags(
        waitDialog.windowFlags() & ~qt.Qt.WindowCloseButtonHint & ~qt.Qt.WindowContextHelpButtonHint | qt.Qt.FramelessWindowHint)
      waitDialogLayout = qt.QHBoxLayout()
      waitDialogLayout.setContentsMargins(16, 16, 16, 16)
      label = qt.QLabel("Loading volumes. Please wait...", waitDialog)
      waitDialogLayout.addWidget(label)
      waitDialog.setLayout(waitDialogLayout)
      waitDialog.show()
      slicer.app.processEvents()

      try:
        qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
        # Reset the scene
        self.logic.resetScene()
        # Set parameter back to 2D since clearing the scene resets it to default
        if self.ui.twoDRadioButton.checked:
          self._parameterNode.SetParameter(self.logic.INPUT_TYPE, "2D")
        # Reset comparison counter
        self.logic.sessionComparisonCount = 0
        self.ui.sessionComparisonLabel.text = str(self.logic.sessionComparisonCount)

        self.logic.surveyStarted = True

        csvPath = self.ui.csvPathSelector.currentPath
        comparisonHistoryPath = None
        eloHistoryPath = None
        if csvPath:
          csvFileName = os.path.basename(csvPath)
          timestamp = csvFileName.split("_")[-1]
          csvRoot = os.path.abspath(os.path.join(csvPath, os.pardir))
          comparisonHistoryPath = os.path.join(csvRoot, "comparison_history_" + timestamp)
          eloHistoryPath = os.path.join(csvRoot, "elo_history_" + timestamp)

        self.logic.loadVolumes(self.ui.inputDirectorySelector.directory)
        self.logic.setSurveyHistory(comparisonHistoryPath)
        self.ui.totalComparisonLabel.text = str(self.logic.getTotalComparisonCount())
        self.logic.setEloHistoryTable(eloHistoryPath)
        self.logic.loadSurveyTable(csvPath)

        self.logic.updateNextPair(self.ui.csvPathSelector.currentPath == "")
        self.logic.prepareDisplay(self.ui.leftThresholdSlider.value, self.ui.rightThresholdSlider.value)

        self.ui.inputsCollapsibleButton.collapsed = True
        self.ui.comparisonCollapsibleButton.collapsed = False

      except Exception as e:
        qt.QApplication.restoreOverrideCursor()

        logging.error(str(e))
        slicer.util.errorDisplay(f"Failed to load: {str(e)}")
        import traceback
        traceback.print_exc()

      finally:
        qt.QApplication.restoreOverrideCursor()
        waitDialog.hide()
        waitDialog.deleteLater()

  def onResetCameraButton(self):
    logging.info("onResetCameraButton()")
    self.ui.leftThresholdSlider.value = self.THRESHOLD_SLIDER_MIDDLE_VALUE
    self.logic.prepareDisplay(self.ui.leftThresholdSlider.value, self.ui.rightThresholdSlider.value)

  def changeScene(self, score=0.5):
    """
    Change pair of images being evaluated.
    """
    self.logic.surveyStarted = True
    self.logic.sessionComparisonCount += 1

    self.logic.addRecordInTable(score)
    totalComparisonCount = self.logic.getTotalComparisonCount()
    self.ui.totalComparisonLabel.text = str(totalComparisonCount)
    self.ui.sessionComparisonLabel.text = str(self.logic.sessionComparisonCount)

    self.logic.hideCurrentVolumes()  # Hide current pair before selecting new pair

    self.logic.setNextPair(self.logic.getPairFromSurveyTable())

    if not self.logic.getNextPair():
      self.logic.updateNextPair(self.ui.csvPathSelector.currentPath == "")

    self.logic.prepareDisplay(self.ui.leftThresholdSlider.value, self.ui.rightThresholdSlider.value)

    self.onLeftSliderChanged(self.ui.leftThresholdSlider.value)
    self.onRightSliderChanged(self.ui.rightThresholdSlider.value)

  def onLeftBetterClicked(self):
    logging.info("Left side better clicked")
    self.logic.updateComparisonData(1.0)
    self.changeScene(1.0)

  def onEqualClicked(self):
    logging.info("Tie button clicked")
    self.logic.updateComparisonData(0.5)
    self.changeScene(0.5)

  def onRightBetterClicked(self):
    logging.info("Right side better clicked")
    self.logic.updateComparisonData(0.0)
    self.changeScene(0.0)

  def onSaveButton(self):
    logging.info("onSaveButton()")
    confirmation = slicer.util.confirmYesNoDisplay("Exit survey and save results?")
    try:
      if confirmation:
        # Save history as csv
        surveyTable = self._parameterNode.GetNodeReference(self.logic.SURVEY_RESULTS_TABLE)
        if (surveyTable.GetCellText(self.logic.getTotalComparisonCount(), self.logic.LEFT_MODEL_COL) == "" and
            surveyTable.GetCellText(self.logic.getTotalComparisonCount(), self.logic.RIGHT_MODEL_COL) == ""):
          surveyTable.RemoveRow(self.logic.getTotalComparisonCount())
        comparisonHistoryFilename = self.ui.outputDirectorySelector.directory + "/comparison_history_" + time.strftime("%Y%m%d-%H%M%S") + ".csv"
        slicer.util.saveNode(surveyTable, comparisonHistoryFilename)
        # Elo history
        eloHistoryTable = self._parameterNode.GetNodeReference(self.logic.ELO_HISTORY_TABLE)
        eloHistoryFilename = self.ui.outputDirectorySelector.directory + "/elo_history_" + time.strftime("%Y%m%d-%H%M%S") + ".csv"
        slicer.util.saveNode(eloHistoryTable, eloHistoryFilename)

        # Save pandas dataframe to csv
        resultsSavePath = self.ui.outputDirectorySelector.directory + "/elo_scores_" + time.strftime("%Y%m%d-%H%M%S") + ".csv"
        self.logic.getSurveyTable().to_csv(resultsSavePath, index=False)

        slicer.util.infoDisplay(f"Results successfully saved to: {resultsSavePath}")
        self.logic.surveyStarted = False
    except Exception as e:
      slicer.util.errorDisplay(f"Results could not be saved: {str(e)}")


#
# SegmentationComparisonLogic
#

class SegmentationComparisonLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  LEFT_MODEL_COL = 2
  RIGHT_MODEL_COL = 4
  DEFAULT_ELO = 1000
  K = 32
  EXP_SCALING_FACTOR = 0.01
  DF_COLUMN_NAMES = ["ModelName", "Elo", "GamesPlayed", "TimeLastPlayed"]

  WINDOW = 50
  IMAGE_INTENSITY_MAX = 310  # Some bug causes images to have values beyond 255. Once that is fixed, this can be set to 255.
  NUM_SLICES_PER_MODEL = 6

  SHOW_IDS_SETTING = "SegmentationComparison/ShowVolumeIds"
  SHOW_IDS_DEFAULT = False
  SHOW_SLICE_ANNOTATIONS_SETTING = "DataProbe/sliceViewAnnotations.bottomLeft"  # for some reason, enabled doesn't work
  SHOW_SLICE_ANNOTATIONS_DEFAULT = 0
  CAMERA_FOV_SETTING = "SegmentationComparison/CameraFov"
  CAMERA_FOV_DEFAULT = 1800

  # Module parameter names

  INPUT_TYPE = "InputType"  # 2D or 3D
  LEFT_OPACITY_THRESHOLD = "LeftOpacityThreshold"  # range 0..1
  RIGHT_OPACITY_THRESHOLD = "RightOpacityThreshold"  # range 0..1
  LINK_OPACITIES = "LinkOpacities"
  SURVEY_RESULTS_TABLE = "SurveyResultsTable"
  ELO_HISTORY_TABLE = "EloHistoryTable"
  SCANS_AND_MODELS_DICT = "ScansAndModelsDict"  # dict[modelName][scanName] = N serialized with json. N = number of games played.
  SURVEY_DATAFRAME = "SurveyDataFrame"
  NEXT_PAIR = "NextPair"  # list[volumeName, AiModelName1, AiModelName2]


  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)

    self.surveyStarted = False
    self.surveyFinished = False
    self.sessionComparisonCount = 0  # How many comparisons have happened in this Slicer session

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter(self.LEFT_OPACITY_THRESHOLD):
      parameterNode.SetParameter(self.LEFT_OPACITY_THRESHOLD, "0.5")

    if not parameterNode.GetParameter(self.RIGHT_OPACITY_THRESHOLD):
      parameterNode.SetParameter(self.RIGHT_OPACITY_THRESHOLD, "0.5")

    if not parameterNode.GetParameter(self.LINK_OPACITIES):
      parameterNode.SetParameter(self.LINK_OPACITIES, "True")
    
    if not parameterNode.GetParameter(self.INPUT_TYPE):
      parameterNode.SetParameter(self.INPUT_TYPE, "3D")

  def setSurveyHistory(self, comparisonHistoryPath):
    """
    Makes sure survey results table exists. If a previously saved file is specified, the table contents will be read from that
    file. Otherwise a new blank table will be created.
    :param comparisonHistoryPath: full path and file name for previously saved data, or leave blank
    :returns: None
    """
    parameterNode = self.getParameterNode()

    if parameterNode.GetNodeReference(self.SURVEY_RESULTS_TABLE) is not None:
      oldResultsTable = parameterNode.GetNodeReference(self.SURVEY_RESULTS_TABLE)
      slicer.mrmlScene.RemoveNode(oldResultsTable)

    if comparisonHistoryPath:  # Load corresponding comparison history csv
      surveyTable = slicer.util.loadTable(comparisonHistoryPath)
      surveyTable.SetName(self.SURVEY_RESULTS_TABLE)
      parameterNode.SetNodeReferenceID(self.SURVEY_RESULTS_TABLE, surveyTable.GetID())

    else:  # Reset survey table used to store survey results
      surveyTable = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLTableNode', self.SURVEY_RESULTS_TABLE)
      parameterNode.SetNodeReferenceID(self.SURVEY_RESULTS_TABLE, surveyTable.GetID())

      # Prepare data types for table columns
      indexCol = vtk.vtkIntArray()
      indexCol.SetName("Comparison")
      model1Col = vtk.vtkStringArray()
      model1Col.SetName("Model_L")
      score1Col = vtk.vtkDoubleArray()
      score1Col.SetName("Score_L")
      model2Col = vtk.vtkStringArray()
      model2Col.SetName("Model_R")
      score2Col = vtk.vtkDoubleArray()
      score2Col.SetName("Score_R")

      # Populate table with columns
      surveyTable.AddColumn(indexCol)
      surveyTable.AddColumn(model1Col)
      surveyTable.AddColumn(score1Col)
      surveyTable.AddColumn(model2Col)
      surveyTable.AddColumn(score2Col)

  def setEloHistoryTable(self, eloHistoryPath=None):
    """
    Removes existing Elo history table, creates a new one, and optionally populates it from file
    :param eloHistoryPath: full path to a previously saved Elo history table
    :returns: None
    """
    parameterNode = self.getParameterNode()

    currentEloHistoryTable = parameterNode.GetNodeReference(self.ELO_HISTORY_TABLE)
    if currentEloHistoryTable:
      slicer.mrmlScene.RemoveNode(currentEloHistoryTable)

    if eloHistoryPath:
      eloHistoryTable = slicer.util.loadTable(eloHistoryPath)
      eloHistoryTable.SetName(self.ELO_HISTORY_TABLE)
      parameterNode.SetNodeReferenceID(self.ELO_HISTORY_TABLE, eloHistoryTable.GetID())
    else:
      # Create a table to store Elo score evolution over time
      eloHistoryTable = parameterNode.GetNodeReference(self.ELO_HISTORY_TABLE)
      if eloHistoryTable == None:
        eloHistoryTable = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", self.ELO_HISTORY_TABLE)
        parameterNode.SetNodeReferenceID(self.ELO_HISTORY_TABLE, eloHistoryTable.GetID())

      eloHistoryTable.RemoveAllColumns()

      indexCol = vtk.vtkIntArray()
      indexCol.SetName("Comparison")
      eloHistoryTable.AddColumn(indexCol)

      scansAndModelsDict = self.getScansAndModelsDict()
      modelNames = scansAndModelsDict.keys()
      for modelName in modelNames:
        eloCol = vtk.vtkDoubleArray()
        eloCol.SetName(modelName)
        eloHistoryTable.AddColumn(eloCol)

  def loadSurveyTable(self, csvPath):
    scansAndModelsDict = self.getScansAndModelsDict()
    if csvPath:
      surveyDF = pd.read_csv(csvPath)

      # Catch errors in csv format or content
      if surveyDF.empty:
        raise Exception("CSV file is empty!")

      # Make sure required columns are in csv
      missingCols = []
      for col in self.DF_COLUMN_NAMES:
        if col not in surveyDF.columns.values:
          missingCols.append(col)
      if missingCols:
        raise Exception(f"CSV file is missing columns: {missingCols}.")

      # Make sure model names match

      modelNames = scansAndModelsDict.keys()
      csvModelNames = surveyDF["ModelName"].unique()
      if not (set(modelNames) == set(csvModelNames)):
        raise Exception("Model names in CSV do not match loaded volumes.")

      # Check for missing values in elo and games played columns
      nanCols = surveyDF.columns[surveyDF.isnull().any()].tolist()
      nanColNames = []
      for i in range(1, len(self.DF_COLUMN_NAMES) - 1):  # there is probably a better solution
        column = self.DF_COLUMN_NAMES[i]
        if column in nanCols:
          nanColNames.append(column)
      if nanColNames:
        raise Exception(f"CSV file contains missing values in columns: {nanColNames}.")

      surveyDF["TimeLastPlayed"] = pd.to_datetime(surveyDF["TimeLastPlayed"])

    else:
      # Create new dataframe with each row being one model
      data = {
        "ModelName": scansAndModelsDict.keys(),
        "Elo": self.DEFAULT_ELO,
        "GamesPlayed": 0,
        "TimeLastPlayed": None
      }
      surveyDF = pd.DataFrame(data)
      surveyDF["TimeLastPlayed"] = pd.to_datetime(surveyDF["TimeLastPlayed"])

    # Save dataframe to parameter node
    self.setSurveyTable(surveyDF)

  def setSurveyTable(self, surveyDF):
    """Save the contents of a dataframe in the parameter node in string format.
    :param surveyDF: pandas dataframe
    :return: None
    """
    parameterNode = self.getParameterNode()
    dataStr = surveyDF.to_json(date_format="iso")
    parameterNode.SetParameter(self.SURVEY_DATAFRAME, dataStr)

  def getSurveyTable(self):
    """Returns the dataframe representation of the survey dataframe.
    :return: pandas dataframe
    """
    parameterNode = self.getParameterNode()
    surveyDF = pd.read_json(parameterNode.GetParameter(self.SURVEY_DATAFRAME))
    surveyDF["TimeLastPlayed"] = pd.to_datetime(surveyDF["TimeLastPlayed"]).dt.tz_localize(None)
    return surveyDF

  def resourcePath(self, filename):
    moduleDir = os.path.dirname(slicer.util.modulePath(self.moduleName))
    return os.path.join(moduleDir, "Resources", filename)

  def resetScene(self):
    slicer.mrmlScene.Clear()

  def loadAndApplyTransforms(self, directory):
    """
    Deprecated. Prepare input volumes in correct position and orientation instead of using this function.
    This function was added in case volumes are not consistently oriented in anatomical coordinates.
    This would allow storing transforms (to RAS) for each volume.
    """
    transformsInDirectory = list(f for f in os.listdir(directory) if f.endswith(".h5"))

    if transformsInDirectory != []:
      # starts empty, but is used to track which volumes have had a transform applied
      transformsArray = np.full_like(self.volumesArray, "")

      # if it is named "DefaultTransform", then it is used as the default
      # otherwise if it is named according to the scene_model naming scheme, it is loaded instead
      for transformIndex, transformFile in enumerate(transformsInDirectory):
        name = str(os.path.basename(transformFile))
        # remove file extension
        name = name.replace('.h5','')

        # The transform to be applied to all volumes without a corresponding transform
        if name == "DefaultTransform":
          loadedTransform = slicer.util.loadTransform(directory + "/" + transformFile)

          for scene in range(self.volumesArray.shape[0]):
            for model in range(self.volumesArray.shape[1]):

              # if a transform has not yet been applied
              if transformsArray[scene][model] == "":
                volume = slicer.util.getNode(self.volumesArray[scene][model])

                volume.SetAndObserveTransformNodeID(loadedTransform.GetID())

                transformsArray[scene][model] = name
                
        # exception transform, will be applied to a specific volume
        elif name.startswith("Scene_") and name.endswith("_Transform"):
          sceneNumber = int(name.split("_")[1])
          modelNumber = int(name.split("_")[3])

          volume = slicer.util.getNode(self.volumesArray[sceneNumber][modelNumber])

          loadedTransform = slicer.util.loadTransform(directory + "/" + transformFile)
          volume.SetAndObserveTransformNodeID(loadedTransform.GetID())

          transformsArray[sceneNumber][modelNumber] = name

        # does not follow the naming scheme
        else:
          slicer.util.infoDisplay("A transform doesn't follow the naming scheme. Use DefaultTransform.h5 "
                                  "to set the default transform, and Scene_x_Model_y_Transform.h5 for "
                                  "specific volumes")

    else:
      logging.warning("No transforms found in selected folder. To add a transform, save them in the same folder as "
            "the volumes. Use this naming scheme: DefaultTransform.h5 to set the default transform, "
            "and Scene_x_Model_y_Transform.h5 for specific volumes")

  def loadVolumes(self, directory):
    # Load the volumes that will be compared.
    # Store a dictionary with patient_sequence names as keys and lists of AI models as elements.
    # For example, patient_sequence 405_axial was evaluated with the AI models UNet_1 and UNet_2.

    logging.info("Load button pressed, resetting the scene")
    parameterNode = self.getParameterNode()
    inputType = parameterNode.GetParameter(self.INPUT_TYPE)

    # List nrrd volumes in indicated directory
    print("Checking directory: " + directory)
    volumesInDirectory = glob.glob(os.path.join(directory, "*_*_*.nrrd"))

    if volumesInDirectory:
      print("Found volumes: " + str(volumesInDirectory))

      # Load found volumes and create dictionary with their data
      scansAndModelsDict = {}
      for volumeFile in volumesInDirectory:
        name = os.path.splitext(os.path.basename(volumeFile))[0]  # remove file extension
        patiendId, modelName, sequenceName = name.split('_')
        scanName = patiendId + "_" + sequenceName

        if modelName in scansAndModelsDict:
          scansAndModelsDict[modelName][scanName] = 0
        else:
          scansAndModelsDict[modelName] = {scanName: 0}
        
        # Load ultrasound sequence and predictions based on index file
        if inputType == "2D":
          parentDir = os.path.abspath(os.path.join(volumeFile, os.pardir))
          with open(os.path.join(parentDir, f"{scanName}_indices.json")) as f:
            indices = json.load(f)["indices"]

          # Load ultrasound frames if needed
          ultrasoundVolume = parameterNode.GetNodeReference(scanName)
          if not ultrasoundVolume:
            ultrasoundFilename = os.path.join(parentDir, f"{scanName}.nrrd")
            ultrasoundArray = nrrd.read(ultrasoundFilename)[0]
            ultrasoundArrayFromIndices = np.zeros((len(indices), ultrasoundArray.shape[1], ultrasoundArray.shape[2]))
            for i in range(len(indices)):
              ultrasoundArrayFromIndices[i] = np.flip(ultrasoundArray[indices[i], :, :, 0], axis=0)
            
            # Convert to slicer volume
            ultrasoundVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", scanName)
            slicer.util.updateVolumeFromArray(ultrasoundVolume, ultrasoundArrayFromIndices)
            parameterNode.SetNodeReferenceID(scanName, ultrasoundVolume.GetID())
          
          # Load segmentations
          predictionArray = nrrd.read(volumeFile)[0]
          predictionArrayFromIndices = np.zeros((len(indices), predictionArray.shape[1], predictionArray.shape[2]))
          for i in range(len(indices)):
            predictionArrayFromIndices[i] = np.flip(predictionArray[indices[i], :, :, 0], axis=0)
          predictionVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", name)
          slicer.util.updateVolumeFromArray(predictionVolume, predictionArrayFromIndices)
          predictionVolume.CreateDefaultDisplayNodes()
          predictionDisplayNode = predictionVolume.GetDisplayNode()
          predictionDisplayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeGreen")
          parameterNode.SetNodeReferenceID(name, predictionVolume.GetID())

        else:
          loadedVolume = slicer.util.loadVolume(volumeFile)
          loadedVolume.SetName(name)
          parameterNode.SetNodeReferenceID(name, loadedVolume.GetID())

      self.setScansAndModelsDict(scansAndModelsDict)
    else:
      slicer.util.errorDisplay("Ensure volumes follow the naming convention: "
                               "[patient_id]_[AI_model_name]_[sequence_name].nrrd")

  def setScansAndModelsDict(self, scansAndModelsDict):
    """
    Save the contents of a dict in the parameter node in string format.
    :param scansAndModelsDict: dict
    :returns: None
    """
    parameterNode = self.getParameterNode()
    s = json.dumps(scansAndModelsDict)
    parameterNode.SetParameter(self.SCANS_AND_MODELS_DICT, s)

  def getScansAndModelsDict(self):
    """
    Returns the dict representation of scans and models dict. Changing the dict will not update the parameter node.
    If you edit the contents of the dict, use setScansAndModelsDict to save the changes.
    :returns dict: scansAndModelsDict
    """
    parameterNode = self.getParameterNode()
    d = json.loads(parameterNode.GetParameter(self.SCANS_AND_MODELS_DICT))
    return d

  def calculateExpectedScores(self, leftElo, rightElo):
    leftExpected = 1 / (1 + 10 ** ((rightElo - leftElo) / 400))
    rightExpected = 1 / (1 + 10 ** ((leftElo - rightElo) / 400))
    return leftExpected, rightExpected

  def calculateScaledScore(self, diff, rmin=-4, rmax=4, tmin=0, tmax=1):
    """Linearly scales the difference in rating to lie in between 0 and 1.

        scaled rating difference = (diff - rmin) / (rmax - rmin) * (tmax - tmin) + tmin,
        where diff = measured difference in rating,
              rmin = minimum of original range (-4),
              rmax = maximum of original range (4),
              tmin = minimum of target range (0),
              tmax = maximum of target range (1)
    """
    return (diff - rmin) / (rmax - rmin) * (tmax - tmin) + tmin

  def calculateActualScores(self):
    surveyTable = self.getParameterNode().GetNodeReference(self.SURVEY_RESULTS_TABLE)
    leftRating = int(surveyTable.GetCellText(self.sessionComparisonCount - 1, self.LEFT_MODEL_COL))
    rightRating = int(surveyTable.GetCellText(self.sessionComparisonCount - 1, self.RIGHT_MODEL_COL))
    leftActual = self.calculateScaledScore(leftRating - rightRating)
    rightActual = self.calculateScaledScore(rightRating - leftRating)
    return leftActual, rightActual

  def calculateNewElo(self, current, actual, expected):
    return current + self.K * (actual - expected)

  def updateComparisonData(self, leftScore=0.5):
    if leftScore < 0.0 or leftScore > 1.0:
      logging.error("Score cannot be outside 0.0 and 1.0!")

    # Update elo scores
    nextPair = self.getNextPair()
    surveyDF = self.getSurveyTable()
    leftModel = nextPair[1]
    rightModel = nextPair[2]
    leftElo = surveyDF.query(f"ModelName == '{leftModel}'").iloc[0]["Elo"]
    rightElo = surveyDF.query(f"ModelName == '{rightModel}'").iloc[0]["Elo"]
    leftExpected, rightExpected = self.calculateExpectedScores(leftElo, rightElo)
    leftActual = leftScore
    rightActual = 1.0 - leftScore
    leftNewElo = self.calculateNewElo(leftElo, leftActual, leftExpected)
    rightNewElo = self.calculateNewElo(rightElo, rightActual, rightExpected)
    leftModelIdx = surveyDF.index[surveyDF["ModelName"] == leftModel][0]
    rightModelIdx = surveyDF.index[surveyDF["ModelName"] == rightModel][0]
    surveyDF.at[leftModelIdx, "Elo"] = leftNewElo
    surveyDF.at[rightModelIdx, "Elo"] = rightNewElo

    # Increment games played for each model/scan and update last time played
    scansAndModelsDict = self.getScansAndModelsDict()

    scan = nextPair[0]
    for i in range(1, len(nextPair)):
      model = nextPair[i]
      modelIdx = surveyDF.index[surveyDF["ModelName"] == model][0]
      surveyDF.at[modelIdx, "GamesPlayed"] += 1
      surveyDF.at[modelIdx, "TimeLastPlayed"] = datetime.datetime.now()
      scansAndModelsDict[model][scan] += 1

    self.setScansAndModelsDict(scansAndModelsDict)
    self.setSurveyTable(surveyDF)

    # Add a row to the elo history table

    parameterNode = self.getParameterNode()
    eloHistoryTable = parameterNode.GetNodeReference(self.ELO_HISTORY_TABLE)

    eloHistoryTable.AddEmptyRow()
    rowIdx = eloHistoryTable.GetNumberOfRows() - 1
    eloHistoryTable.SetCellText(rowIdx, 0, str(self.getTotalComparisonCount()))

    modelNames = scansAndModelsDict.keys()
    i = 0
    for modelName in modelNames:
      i += 1
      modelIdx = surveyDF.index[surveyDF["ModelName"] == modelName][0]
      eloHistoryTable.SetCellText(rowIdx, i, str(surveyDF.at[modelIdx, "Elo"]))

  def updateNextPair(self, isNewCsv):
    surveyDF = self.getSurveyTable()

    # Randomly choose first matchup
    if self.sessionComparisonCount == 0 and isNewCsv:
      models = surveyDF["ModelName"].tolist()
      nextModelPair = random.sample(models, 2)

    else:
      nextModelPair = []
      # Get list of models with minimum games played
      minGamesIndexes = surveyDF.index[surveyDF["GamesPlayed"] == surveyDF["GamesPlayed"].min()].tolist()

      if len(minGamesIndexes) == 1:
        # No ties
        leastModel = surveyDF.iloc[minGamesIndexes[0]]["ModelName"]
        nextModelPair.append(leastModel)
      else:
        # Pick first model with least recent date played
        minGamesDF = surveyDF.iloc[minGamesIndexes]
        leastModel = surveyDF.query(f"TimeLastPlayed == '{minGamesDF['TimeLastPlayed'].min()}'").iloc[0]["ModelName"]
        nextModelPair.append(leastModel)

      # Sample list of models with probability based on elo difference
      leastModelElo = surveyDF.query(f"ModelName == '{leastModel}'").iloc[0]["Elo"]
      eloDiffList = (surveyDF["Elo"] - leastModelElo).abs().tolist()
      if all(eloDiff == 0 for eloDiff in eloDiffList):
        validModel = False
        while not validModel:
          chosenModelIdx = rng.integers(0, len(eloDiffList))
          if surveyDF.iloc[chosenModelIdx]["ModelName"] != leastModel:
            validModel = True
      else:
        samplingWeights = self.getModelSamplingProbability(eloDiffList)
        chosenModelIdx = random.choices(list(enumerate(eloDiffList)), weights=samplingWeights)[0][0]
      closestEloModel = surveyDF.iloc[chosenModelIdx]["ModelName"]
      nextModelPair.append(closestEloModel)

    # Choose scan with least number of games
    minDictList = []
    scansAndModelsDict = self.getScansAndModelsDict()
    for model in nextModelPair:
      modelScans = scansAndModelsDict[model].items()
      # workaround to issue of scan getting picked when not the least played
      minDictList.append(min(random.sample(modelScans, len(modelScans)), key=lambda x: x[1]))
    minScan = min(minDictList, key=lambda x: x[1])[0]
    nextModelPair.insert(0, minScan)
    self.setNextPair(nextModelPair)

  def setNextPair(self, nextPair):
    """Save the contents of a list in the parameter node in string format.
    :param nextPair: list (format: list[volumeName, AiModelName1, AiModelName2])
    :returns: None
    """
    parameterNode = self.getParameterNode()
    pairStr = json.dumps(nextPair)
    parameterNode.SetParameter(self.NEXT_PAIR, pairStr)

  def getNextPair(self):
    """Returns the list representation of the next matchup, if it exists.
    :return: list if the matchup exists, else None
    """
    # TODO: is it better to catch a non-existing list here or where this method is called?
    nextPairStr = self.getParameterNode().GetParameter(self.NEXT_PAIR)
    if nextPairStr == "":
      return
    nextPair = json.loads(nextPairStr)
    return nextPair

  def setParameter(self, parameterName, value):
    """
    Converts parameter values to string and saves them to the parameter node.
    :param parameterName: name (string)
    :param value: value (in original type)
    :returns: None
    """
    parameterNode = self.getParameterNode()

    if parameterName == self.LINK_OPACITIES:
      if value:
        parameterNode.SetParameter(self.LINK_OPACITIES, "True")
      else:
        parameterNode.SetParameter(self.LINK_OPACITIES, "False")
    else:
      parameterNode.SetParameter(parameterName, str(value))

  def getParameter(self, parameterName):
    """
    Returns a parameter from the module parameter node converted to the intended type.
    :param parameterName: name of the parameter
    :returns: value of the parameter
    """
    parameterNode = self.getParameterNode()

    if parameterName == self.RIGHT_OPACITY_THRESHOLD or parameterName == self.LEFT_OPACITY_THRESHOLD:
      valueStr = parameterNode.GetParameter(parameterName)
      return float(valueStr)

    elif parameterName == self.LINK_OPACITIES:
      valueStr = parameterNode.GetParameter(parameterName)
      return True if valueStr.lower() == "true" else False

    else:
      logging.warning("Cannot find parameter name: {}".format(parameterName))
      return

  def getModelSamplingProbability(self, eloDiffList):
    probs = []
    for eloDiff in eloDiffList:
      if eloDiff == 0:
        probs.append(0)
      else:
        probs.append(math.exp(-self.EXP_SCALING_FACTOR * eloDiff))
    return probs

  def getTotalComparisonCount(self):
    """
    Returns the total number of rows in the survey results table.
    :returns: number of comparisons
    """
    resultsTable = self.getParameterNode().GetNodeReference(self.SURVEY_RESULTS_TABLE)
    if resultsTable is not None:
      return resultsTable.GetNumberOfRows()
    else:
      return 0

  def getPairFromSurveyTable(self):
    surveyTable = self.getParameterNode().GetNodeReference(self.SURVEY_RESULTS_TABLE)
    totalComparisonCount = surveyTable.GetNumberOfRows()
    leftScanName = surveyTable.GetCellText(totalComparisonCount, self.LEFT_MODEL_COL - 1)
    rightScanName = surveyTable.GetCellText(totalComparisonCount, self.RIGHT_MODEL_COL - 1)
    if leftScanName == "" and rightScanName == "":
      return
    leftModelName = leftScanName.split("_")[1]
    rightModelName = rightScanName.split("_")[1]
    scanName = leftScanName.split("_")[0] + "_" + leftScanName.split("_")[2]
    return [scanName, leftModelName, rightModelName]

  def centerAndRotateCamera(self, volume, viewNode):
    """
    Center camera of viewNode on volume specified.
    """
    imageData = volume.GetImageData()
    volumeCenter_Ijk = imageData.GetCenter()

    IjkToRasMatrix = vtk.vtkMatrix4x4()
    volume.GetIJKToRASMatrix(IjkToRasMatrix)
    volumeCenter_Ras = np.array(IjkToRasMatrix.MultiplyFloatPoint(np.append(volumeCenter_Ijk, [1])))
    volumeCenter_Ras = volumeCenter_Ras[:3]

    camerasLogic = slicer.modules.cameras.logic()
    cameraNode = camerasLogic.GetViewActiveCameraNode(viewNode)
    camera = cameraNode.GetCamera()

    fov = slicer.util.settingsValue(self.CAMERA_FOV_SETTING, self.CAMERA_FOV_DEFAULT, converter=int)

    camera.SetFocalPoint(volumeCenter_Ras)
    camera.SetViewUp([0, 0, 1])
    camera.SetPosition(volumeCenter_Ras + np.array([0, -fov, 0]))
    cameraNode.ResetClippingRange()

  def setVolumeRenderingProperty(self, volumeNode, window, level):
    """
    Manually define volume property for volume rendering. Volume intensity range is assumed to be [0..255].
    @param volumeNode: vtkMRMLScalarVolumeNode
    @param window: range of intensity to be displayed (max-min)
    @param level: center value of intensity range to be displayed
    @returns: display node for volume, or None on error
    """
    if volumeNode is None:
      logging.warning("setVolumeRenderingProperty() is called with invalid volumeNode")
      return None

    vrLogic = slicer.modules.volumerendering.logic()
    displayNode = vrLogic.GetFirstVolumeRenderingDisplayNode(volumeNode)

    if displayNode is None:
      volumeNode.CreateDefaultDisplayNodes()
      vrLogic.CreateDefaultVolumeRenderingNodes(volumeNode)
      displayNode = vrLogic.GetFirstVolumeRenderingDisplayNode(volumeNode)

    # Assuming that the displayable range is [0..255], and the range to display is [L-(W/2)..L+(W/2)]

    upper = min(self.IMAGE_INTENSITY_MAX + window, level + window/2)
    lower = max(-window, level - window/2)

    if upper <= lower:
      upper = lower + 1  # Make sure the displayed intensity range is valid.

    p0 = lower
    p1 = lower + (upper - lower)*0.15
    p2 = lower + (upper - lower)*0.4
    p3 = upper

    opacityTransferFunction = vtk.vtkPiecewiseFunction()
    opacityTransferFunction.AddPoint(p0, 0.0)
    opacityTransferFunction.AddPoint(p1, 0.2)
    opacityTransferFunction.AddPoint(p2, 0.6)
    opacityTransferFunction.AddPoint(p3, 1)

    colorTransferFunction = vtk.vtkColorTransferFunction()
    colorTransferFunction.AddRGBPoint(p0, 0.20, 0.00, 0.00)
    colorTransferFunction.AddRGBPoint(p1, 0.65, 0.45, 0.15)
    colorTransferFunction.AddRGBPoint(p2, 0.85, 0.75, 0.55)
    colorTransferFunction.AddRGBPoint(p3, 1.00, 1.00, 0.90)

    # The property describes how the data will look
    volumeProperty = displayNode.GetVolumePropertyNode().GetVolumeProperty()
    volumeProperty.SetColor(colorTransferFunction)
    volumeProperty.SetScalarOpacity(opacityTransferFunction)
    volumeProperty.ShadeOn()
    volumeProperty.SetInterpolationTypeToLinear()

    return displayNode

  def nameFromPatientSequenceAndModel(self, patientSequence, model):
    # Get the full volume name by combining elements of patientSequence and model
    patientId = patientSequence.split("_")[0]
    volumeName = str(patientId) + "_" + model + "_" + "_".join(patientSequence.split("_")[1:])
    return volumeName

  def hideCurrentVolumes(self):
    """
    Hides current pair of volumes.
    :returns: None
    """
    parameterNode = self.getParameterNode()
    nextPair = self.getNextPair()

    if parameterNode.GetParameter(self.INPUT_TYPE) == "3D":
      volumeRenderingLogic = slicer.modules.volumerendering.logic()

      volumeName1 = self.nameFromPatientSequenceAndModel(nextPair[0], nextPair[1])
      volumeNode1 = parameterNode.GetNodeReference(volumeName1)
      displayNode1 = volumeRenderingLogic.GetFirstVolumeRenderingDisplayNode(volumeNode1)
      displayNode1.SetVisibility(False)

      volumeName2 = self.nameFromPatientSequenceAndModel(nextPair[0], nextPair[2])
      volumeNode2 = parameterNode.GetNodeReference(volumeName2)
      displayNode2 = volumeRenderingLogic.GetFirstVolumeRenderingDisplayNode(volumeNode2)
      displayNode2.SetVisibility(False)

  def prepareDisplay(self, leftThreshold, rightThreshold):
    """
    Prepare views and show models in each view
    :param leftThreshold: intensity value around which opaque voxels should gradually transition to transparent, left side
    :param rightThreshold: threshold for right side volume
    :returns: None
    """
    parameterNode = self.getParameterNode()
    inputType = parameterNode.GetParameter(self.INPUT_TYPE)

    # Prevent errors from previous or next buttons when the volumes haven't been loaded in yet

    scansAndModelsDict = self.getScansAndModelsDict()
    if not scansAndModelsDict:
      logging.warning("Volumes not loaded yet")
      return
    nextPair = self.getNextPair()

    slicer.app.setRenderPaused(True)

    if inputType == "2D":
      # Set ultrasound frames as background in all slices
      scanNode = parameterNode.GetNodeReference(nextPair[0])
      slicer.util.setSliceViewerLayers(background=scanNode, fit=True)

    layoutManager = slicer.app.layoutManager()

    # Set up left side view

    volumeName1 = self.nameFromPatientSequenceAndModel(nextPair[0], nextPair[1])
    volumeNode1 = parameterNode.GetNodeReference(volumeName1)
    if inputType == "3D":
      viewNode1 = slicer.mrmlScene.GetSingletonNode("1", "vtkMRMLViewNode")
      viewNode1.LinkedControlOn()
      volumeDisplayNode1 = self.setVolumeRenderingProperty(volumeNode1, self.WINDOW, leftThreshold)
      volumeDisplayNode1.SetViewNodeIDs([viewNode1.GetID()])
      volumeDisplayNode1.SetVisibility(True)
      self.centerAndRotateCamera(volumeNode1, viewNode1)
    else:
      for i in range(self.NUM_SLICES_PER_MODEL):
        sliceTag = "1" + str(i + 1)
        sliceWidget = layoutManager.sliceWidget(sliceTag)
        sliceViewer = sliceWidget.mrmlSliceCompositeNode()
        sliceViewer.SetForegroundVolumeID(volumeNode1.GetID())
        sliceViewer.SetForegroundOpacity(leftThreshold / self.IMAGE_INTENSITY_MAX)
        sliceWidget.sliceLogic().SetSliceOffset(i)

    # Set up right side view

    volumeName2 = self.nameFromPatientSequenceAndModel(nextPair[0], nextPair[2])
    volumeNode2 = parameterNode.GetNodeReference(volumeName2)
    if inputType == "3D":
      viewNode2 = slicer.mrmlScene.GetSingletonNode("2", "vtkMRMLViewNode")
      viewNode2.LinkedControlOn()
      volumeDisplayNode2 = self.setVolumeRenderingProperty(volumeNode2, self.WINDOW, rightThreshold)
      volumeDisplayNode2.SetViewNodeIDs([viewNode2.GetID()])
      volumeDisplayNode2.SetVisibility(True)
      self.centerAndRotateCamera(volumeNode2, viewNode2)
    else:
      for i in range(self.NUM_SLICES_PER_MODEL):
        sliceTag = "2" + str(i + 1)
        sliceWidget = layoutManager.sliceWidget(sliceTag)
        sliceViewer = sliceWidget.mrmlSliceCompositeNode()
        sliceViewer.SetForegroundVolumeID(volumeNode2.GetID())
        sliceViewer.SetForegroundOpacity(rightThreshold / self.IMAGE_INTENSITY_MAX)
        sliceWidget.sliceLogic().SetSliceOffset(i)

    # Show volume IDs in views if setting is on
    showIds = slicer.util.settingsValue(self.SHOW_IDS_SETTING, False, converter=slicer.util.toBool)

    layoutManager = slicer.app.layoutManager()
    viewWidget1 = None
    viewWidget2 = None
    for viewNumber in range(layoutManager.threeDViewCount):
      threeDWidget = layoutManager.threeDWidget(viewNumber)
      viewNode = threeDWidget.mrmlViewNode()
      if viewNode.GetSingletonTag() == "1":
        viewWidget1 = threeDWidget
      elif viewNode.GetSingletonTag() == "2":
        viewWidget2 = threeDWidget
      else:
        pass

    if viewWidget1 is None:
      logging.error("View 1 not found!")
      return
    if viewWidget2 is None:
      logging.error("View 2 not found!")
      return

    if showIds:
      viewWidget1.threeDView().cornerAnnotation().SetText(vtk.vtkCornerAnnotation.UpperRight, volumeName1)
      viewWidget2.threeDView().cornerAnnotation().SetText(vtk.vtkCornerAnnotation.UpperRight, volumeName2)
    else:
      viewWidget1.threeDView().cornerAnnotation().SetText(vtk.vtkCornerAnnotation.UpperRight, "")
      viewWidget2.threeDView().cornerAnnotation().SetText(vtk.vtkCornerAnnotation.UpperRight, "")

    viewWidget1.threeDView().cornerAnnotation().GetTextProperty().SetColor(1, 1, 1)
    viewWidget2.threeDView().cornerAnnotation().GetTextProperty().SetColor(1, 1, 1)
  
    # Show/hide slice view annotations
    showSliceAnnotations = slicer.util.settingsValue(self.SHOW_SLICE_ANNOTATIONS_SETTING, self.SHOW_SLICE_ANNOTATIONS_DEFAULT, converter=int)
    sliceAnnotations = slicer.modules.DataProbeInstance.infoWidget.sliceAnnotations
    sliceAnnotations.bottomLeft = showSliceAnnotations
    sliceAnnotations.updateSliceViewFromGUI()

    slicer.app.setRenderPaused(False)

  def addRecordInTable(self, leftScore):
    nextPair = self.getNextPair()
    surveyTable = self.getParameterNode().GetNodeReference(self.SURVEY_RESULTS_TABLE)
    surveyTable.AddEmptyRow()
    rowIdx = surveyTable.GetNumberOfRows() - 1
    namesVolumesToDisplay = [self.nameFromPatientSequenceAndModel(nextPair[0], nextPair[1]),
                             self.nameFromPatientSequenceAndModel(nextPair[0], nextPair[2])]
    surveyTable.SetCellText(rowIdx, 0, str(rowIdx + 1))
    surveyTable.SetCellText(rowIdx, 1, namesVolumesToDisplay[0])
    surveyTable.SetCellText(rowIdx, 2, str(leftScore))
    surveyTable.SetCellText(rowIdx, 3, namesVolumesToDisplay[1])
    surveyTable.SetCellText(rowIdx, 4, str(1.0 - leftScore))

  def setVolumeOpacityThreshold(self, inputVolume, imageThresholdPercent):
    """
    Sets up volume rendering for specified volume with opacity threshold.
    @param inputVolume: vtkMRMLScalarVolumeNode
    @param imageThresholdPercent: opacity treshold in percentage [0..100] float
    @return: None
    """
    # [0..100] >> [0..MAX], where MAX is typically IMAGE_INTENSITY_MAX + 25, if intensity window is 50.

    maxThreshold = self.IMAGE_INTENSITY_MAX + self.WINDOW / 2.0
    imageThreshold = imageThresholdPercent * maxThreshold / 100.0

    window = self.WINDOW
    level = imageThreshold

    displayNode = self.setVolumeRenderingProperty(inputVolume, window, level)
    if not displayNode:
      logging.error("Could not set up volume rendering property!")
  
  def setSlicePredictionOpacity(self, side, imageThresholdPercent):
    layoutManager = slicer.app.layoutManager()
    for i in range(self.NUM_SLICES_PER_MODEL):
      sliceTag = str(side) + str(i + 1)
      sliceWidget = layoutManager.sliceWidget(sliceTag)
      sliceViewer = sliceWidget.mrmlSliceCompositeNode()
      sliceViewer.SetForegroundOpacity(imageThresholdPercent / 100)


#
# SegmentationComparisonTest
#

class SegmentationComparisonTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_SegmentationComparison1()

  def test_SegmentationComparison1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    # Get/create input data

    # Test the module logic

    self.delayDisplay('Test passed')
