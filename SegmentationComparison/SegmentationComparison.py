import os
import unittest
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
  THRESHOLD_SLIDER_MIDDLE_VALUE = 152
  ICON_SIZE_MID = 42
  ICON_SIZE = 54

  LAYOUT_DUAL_3D = 876

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False

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

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).

    self.ui.imageThresholdSliderWidget.setMinimum(0)
    self.ui.imageThresholdSliderWidget.setMaximum(self.logic.THRESHOLD_SLIDER_RESOLUTION)
    self.ui.imageThresholdSliderWidget.connect("valueChanged(int)", self.onThresholdSliderValueChanged)
    self.ui.imageThresholdSliderWidget.setValue(self.THRESHOLD_SLIDER_MIDDLE_VALUE)

    thresholdPercentage = self.getThresholdPercentage(self.ui.imageThresholdSliderWidget.value)
    self.ui.thresholdPercentageLabel.text = str(int(thresholdPercentage)) + "%"

    lastInputPath = slicer.util.settingsValue(self.LAST_INPUT_PATH_SETTING, "")
    if lastInputPath != "":
      self.ui.inputDirectorySelector.directory = lastInputPath

    lastOutputPath = slicer.util.settingsValue(self.LAST_OUTPUT_PATH_SETTING, "")
    if lastOutputPath != "":
      self.ui.outputDirectorySelector.directory = lastOutputPath

    # lastCSVPath = slicer.util.settingsValue(self.LAST_CSV_PATH_SETTING, "")
    # if lastCSVPath != "":
    #   self.ui.csvPathSelector.currentPath = lastCSVPath

    # Make some collapsible buttons exclusive

    self.ui.inputsCollapsibleButton.connect('contentsCollapsed(bool)', self.onInputsCollapsed)
    self.ui.comparisonCollapsibleButton.connect('contentsCollapsed(bool)', self.onComparisonCollapsed)
    self.ui.inputsCollapsibleButton.collapsed = False
    self.ui.comparisonCollapsibleButton.collapsed = True

    # Set up button connections and icons

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

  def onResetSettingsClicked(self):
    logging.info("onResetSettingsClicked()")
    self.ui.displayIdCheckBox.checked = self.logic.SHOW_IDS_DEFAULT
    self.ui.fovSpinBox.value = self.logic.CAMERA_FOV_DEFAULT

  def onFovValueChanged(self, value):
    logging.info("onFovValueChanged({})".format(value))
    settings = slicer.app.userSettings()
    settings.setValue(self.logic.CAMERA_FOV_SETTING, str(value))
    self.logic.prepareDisplay(self.ui.imageThresholdSliderWidget.value)

  def onDisplayIdChecked(self, checked):
    logging.info("onDisplayIdChecked({})".format(checked))
    settings = slicer.app.userSettings()
    if checked != 0:
      settings.setValue(self.logic.SHOW_IDS_SETTING, "true")
    else:
      settings.setValue(self.logic.SHOW_IDS_SETTING, "false")
    self.logic.prepareDisplay(self.ui.imageThresholdSliderWidget.value)

  def onInputsCollapsed(self, collapsed):
    if collapsed == False:
      self.ui.comparisonCollapsibleButton.collapsed = True

  def onComparisonCollapsed(self, collapsed):
    if collapsed == False:
      self.ui.inputsCollapsibleButton.collapsed = True

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

    slicer.app.layoutManager().setLayout(self.LAYOUT_DUAL_3D)  # Setting this layout creates all views automatically

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(
      self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    slicer.util.setDataProbeVisible(True)

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
      self.removeObserver(
        self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    self._parameterNode = inputParameterNode
    if self._parameterNode is not None:
      self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent,
                       self.updateGUIFromParameterNode)

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
    self._updatingGUIFromParameterNode = True

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    # Modify all properties in a single batch
    wasModified = self._parameterNode.StartModify()

    self._parameterNode.SetParameter("Threshold", str(
      self.ui.imageThresholdSliderWidget.value))

    self._parameterNode.EndModify(wasModified)

  # Threshold the selected volume(s)
  def onThresholdSliderValueChanged(self, value):
    """
    Callback function for threshold slider.
    @param value: expected to have minimum value of 0.0, and maximum of logic.THRESHOLD_SLIDER_RESOLUTION
    @return: None
    """
    thresholdPercentage = self.getThresholdPercentage(value)
    self.ui.thresholdPercentageLabel.text = str(round(thresholdPercentage)) + "%"

    if (self.logic.nextPair is None) or (self.logic.nextPair == False):
      logging.info("Not updating volume rendering, because volumes are not displayed yet")
      return

    try:
      currentSceneData = self.logic.nextPair
      for i in range(1, len(currentSceneData)):  # Iterate through currently displayed volumes
        volumeName = self.logic.nameFromPatientSequenceAndModel(currentSceneData[0], currentSceneData[i])
        inputVolume = self._parameterNode.GetNodeReference(volumeName)
        if inputVolume is not None:  # prevents invalid volume error when loading the widget
          self.logic.setVolumeOpacityThreshold(inputVolume, thresholdPercentage)
    except Exception as e:
      slicer.util.errorDisplay("Failed to threshold the selected volume(s): "+str(e))
      import traceback
      traceback.print_exc()

  def getThresholdPercentage(self, value):
    """
    Returns the slider value as a percentage of the total range (0..100).
    @param value: slider value directly from slider widget
    @return: value scaled between 0 and 100.
    """
    minimumValue = self.ui.imageThresholdSliderWidget.minimum
    maximumValue = self.ui.imageThresholdSliderWidget.maximum
    thresholdPercentage = value / (maximumValue - minimumValue) * 100.0
    return thresholdPercentage

  def onLoadButton(self):
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
        # Reset comparison counter
        self.logic.sessionComparisonCount = 0
        self.ui.sessionComparisonLabel.text = str(self.logic.sessionComparisonCount)

        if self.logic.surveyStarted:
          self.logic.surveyStarted = False

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
        self.ui.totalComparisonLabel.text = str(self.logic.totalComparisonCount)
        self.logic.setEloHistoryTable(eloHistoryPath)
        self.logic.setSurveyTable(csvPath)

        self.logic.getNextPair(self.ui.csvPathSelector.currentPath == "")
        self.logic.prepareDisplay(self.ui.imageThresholdSliderWidget.value)

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
    self.ui.imageThresholdSliderWidget.value = self.THRESHOLD_SLIDER_MIDDLE_VALUE
    self.logic.prepareDisplay(self.ui.imageThresholdSliderWidget.value)

  def changeScene(self, score=0.5):
    """
    Change pair of images being evaluated.
    """
    self.logic.sessionComparisonCount += 1
    self.logic.totalComparisonCount += 1
    self.ui.totalComparisonLabel.text = str(self.logic.totalComparisonCount)
    self.ui.sessionComparisonLabel.text = str(self.logic.sessionComparisonCount)
    self.logic.addRecordInTable(score)

    self.logic.hideCurrentVolumes()  # Hide current pair before selecting new pair

    self.logic.nextPair = self.logic.getPairFromSurveyTable()

    if not self.logic.nextPair:
      self.logic.getNextPair(self.ui.csvPathSelector.currentPath == "")

    self.logic.prepareDisplay(self.ui.imageThresholdSliderWidget.value)

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
        surveyTable = self._parameterNode.GetNodeReference(self.logic.RESULTS_TABLE_NAME)
        if (surveyTable.GetCellText(self.logic.totalComparisonCount, self.logic.LEFT_MODEL_COL) == "" and
            surveyTable.GetCellText(self.logic.totalComparisonCount, self.logic.RIGHT_MODEL_COL) == ""):
          surveyTable.RemoveRow(self.logic.totalComparisonCount)
        comparisonHistoryFilename = self.ui.outputDirectorySelector.directory + "/comparison_history_" + time.strftime("%Y%m%d-%H%M%S") + ".csv"
        slicer.util.saveNode(surveyTable, comparisonHistoryFilename)
        # Elo history
        eloHistoryTable = self._parameterNode.GetNodeReference(self.logic.ELO_HISTORY_TABLE)
        eloHistoryFilename = self.ui.outputDirectorySelector.directory + "/elo_history_" + time.strftime("%Y%m%d-%H%M%S") + ".csv"
        slicer.util.saveNode(eloHistoryTable, eloHistoryFilename)

        # Save pandas dataframe to csv
        resultsSavePath = self.ui.outputDirectorySelector.directory + "/elo_scores_" + time.strftime("%Y%m%d-%H%M%S") + ".csv"
        self.logic.surveyDF.to_csv(resultsSavePath, index=False)

        slicer.util.infoDisplay(f"Results successfully saved to: {resultsSavePath}")
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
  RESULTS_TABLE_NAME = "SurveyResultsTable"
  DEFAULT_ELO = 1000
  K = 32
  EXP_SCALING_FACTOR = 0.01
  DF_COLUMN_NAMES = ["ModelName", "Elo", "GamesPlayed", "TimeLastPlayed"]
  ELO_HISTORY_TABLE = "EloHistoryTable"

  THRESHOLD_SLIDER_RESOLUTION = 300  # Must be positive integer
  WINDOW = 50
  IMAGE_INTENSITY_MAX = 310  # Some bug causes images to have values beyond 255. Once that is fixed, this can be set to 255.

  SHOW_IDS_SETTING = "SegmentationComparison/ShowVolumeIds"
  SHOW_IDS_DEFAULT = False
  CAMERA_FOV_SETTING = "SegmentationComparison/CameraFov"
  CAMERA_FOV_DEFAULT = 1800

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)

    self.scansAndModelsDict = {}
    self.surveyDF = None
    self.surveyStarted = False
    self.surveyFinished = False
    self.nextPair = None             # will be used as list[volumeName, AiModelName1, AiModelName2]
    self.previousPair = None
    self.sessionComparisonCount = 0  # How many comparisons have happened in this Slicer session
    self.totalComparisonCount = 0
    self.surveyTable = None

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Threshold"):
      parameterNode.SetParameter("Threshold", "0")

  def setSurveyHistory(self, comparisonHistoryPath):
    parameterNode = self.getParameterNode()
    if comparisonHistoryPath:
      # Load corresponding comparison history csv
      self.surveyTable = slicer.util.loadTable(comparisonHistoryPath)
      self.surveyTable.SetName(self.RESULTS_TABLE_NAME)
      parameterNode.SetNodeReferenceID(self.RESULTS_TABLE_NAME, self.surveyTable.GetID())
      self.totalComparisonCount = self.surveyTable.GetNumberOfRows()

    else:
      # Reset survey table used to store survey results
      self.surveyTable = parameterNode.GetNodeReference(self.RESULTS_TABLE_NAME)
      if self.surveyTable:
        slicer.mrmlScene.RemoveNode(self.surveyTable)

      self.surveyTable = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLTableNode', self.RESULTS_TABLE_NAME)

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
      self.surveyTable.AddColumn(indexCol)
      self.surveyTable.AddColumn(model1Col)
      self.surveyTable.AddColumn(score1Col)
      self.surveyTable.AddColumn(model2Col)
      self.surveyTable.AddColumn(score2Col)
      parameterNode.SetNodeReferenceID(self.RESULTS_TABLE_NAME, self.surveyTable.GetID())

      self.totalComparisonCount = 0

  def setEloHistoryTable(self, eloHistoryPath):
    parameterNode = self.getParameterNode()
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

      modelNames = self.scansAndModelsDict.keys()
      for modelName in modelNames:
        eloCol = vtk.vtkDoubleArray()
        eloCol.SetName(modelName)
        eloHistoryTable.AddColumn(eloCol)

  def setSurveyTable(self, csvPath):
    if csvPath:
      self.surveyDF = pd.read_csv(csvPath)

      # Catch errors in csv format or content
      if self.surveyDF.empty:
        raise Exception("CSV file is empty!")

      # Make sure required columns are in csv
      missingCols = []
      for col in self.DF_COLUMN_NAMES:
        if col not in self.surveyDF.columns.values:
          missingCols.append(col)
      if missingCols:
        raise Exception(f"CSV file is missing columns: {missingCols}.")

      # Make sure model names match
      modelNames = self.scansAndModelsDict.keys()
      csvModelNames = self.surveyDF["ModelName"].unique()
      if not (set(modelNames) == set(csvModelNames)):
        raise Exception("Model names in CSV do not match loaded volumes.")

      # Check for missing values in elo and games played columns
      nanCols = self.surveyDF.columns[self.surveyDF.isnull().any()].tolist()
      nanColNames = []
      for i in range(1, len(self.DF_COLUMN_NAMES) - 1):  # there is probably a better solution
        column = self.DF_COLUMN_NAMES[i]
        if column in nanCols:
          nanColNames.append(column)
      if nanColNames:
        raise Exception(f"CSV file contains missing values in columns: {nanColNames}.")

      self.surveyDF["TimeLastPlayed"] = pd.to_datetime(self.surveyDF["TimeLastPlayed"])

    else:
      # Create new dataframe with each row being one model
      data = {
        "ModelName": self.scansAndModelsDict.keys(),
        "Elo": self.DEFAULT_ELO,
        "GamesPlayed": 0,
        "TimeLastPlayed": None
      }
      self.surveyDF = pd.DataFrame(data)
      self.surveyDF["TimeLastPlayed"] = pd.to_datetime(self.surveyDF["TimeLastPlayed"])

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
      print("Found transforms: " + str(len(transformsInDirectory)))

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
          print("Found default transform")
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
          print("Found exception transform")

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
      print("No transforms found in selected folder. To add a transform, save them in the same folder as "
            "the volumes. Use this naming scheme: DefaultTransform.h5 to set the default transform, "
            "and Scene_x_Model_y_Transform.h5 for specific volumes")

  def loadVolumes(self, directory):
    # Load the volumes that will be compared.
    # Store a dictionary with patient_sequence names as keys and lists of AI models as elements.
    # For example, patient_sequence 405_axial was evaluated with the AI models UNet_1 and UNet_2.

    # Logging to the console
    print('\n',"LOAD BUTTON PRESSED, RESETTING THE SCENE",'\n')

    # List nrrd volumes in indicated directory
    print("Checking directory: " + directory)
    volumesInDirectory = list(f for f in os.listdir(directory) if f.endswith(".nrrd"))
    print("Found volumes: " + str(volumesInDirectory))

    # Load found volumes and create dictionary with their data
    parameterNode = self.getParameterNode()
    self.scansAndModelsDict = {}
    try:
      for volumeIndex, volumeFile in enumerate(volumesInDirectory):
        name = str(volumeFile)
        name = name.replace('.nrrd','') # remove file extension
        loadedVolume = slicer.util.loadVolume(directory + "/" + volumeFile)
        loadedVolume.SetName(name)
        parameterNode.SetNodeReferenceID(name, loadedVolume.GetID())

        patiendId, modelName, sequenceName = name.split('_')
        scanName = patiendId + "_" + sequenceName

        if modelName in self.scansAndModelsDict:
          self.scansAndModelsDict[modelName][scanName] = 0
        else:
          self.scansAndModelsDict[modelName] = {scanName: 0}
    except Exception as e:
      slicer.util.errorDisplay("Ensure volumes follow the naming convention: "
                               "[patient_id]_[AI_model_name]_[sequence_name].nrrd: "+str(e))
      import traceback
      traceback.print_exc()

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
    leftRating = int(self.surveyTable.GetCellText(self.sessionComparisonCount - 1, self.LEFT_MODEL_COL))
    rightRating = int(self.surveyTable.GetCellText(self.sessionComparisonCount - 1, self.RIGHT_MODEL_COL))
    leftActual = self.calculateScaledScore(leftRating - rightRating)
    rightActual = self.calculateScaledScore(rightRating - leftRating)
    return leftActual, rightActual

  def calculateNewElo(self, current, actual, expected):
    return current + self.K * (actual - expected)

  def updateComparisonData(self, leftScore=0.5):
    if leftScore < 0.0 or leftScore > 1.0:
      logging.error("Score cannot be outside 0.0 and 1.0!")

    # Update elo scores
    leftModel = self.nextPair[1]
    rightModel = self.nextPair[2]
    leftElo = self.surveyDF.query(f"ModelName == '{leftModel}'").iloc[0]["Elo"]
    rightElo = self.surveyDF.query(f"ModelName == '{rightModel}'").iloc[0]["Elo"]
    leftExpected, rightExpected = self.calculateExpectedScores(leftElo, rightElo)
    leftActual = leftScore
    rightActual = 1.0 - leftScore
    leftNewElo = self.calculateNewElo(leftElo, leftActual, leftExpected)
    rightNewElo = self.calculateNewElo(rightElo, rightActual, rightExpected)
    leftModelIdx = self.surveyDF.index[self.surveyDF["ModelName"] == leftModel][0]
    rightModelIdx = self.surveyDF.index[self.surveyDF["ModelName"] == rightModel][0]
    self.surveyDF.at[leftModelIdx, "Elo"] = leftNewElo
    self.surveyDF.at[rightModelIdx, "Elo"] = rightNewElo

    # Increment games played for each model/scan and update last time played
    scan = self.nextPair[0]
    for i in range(1, len(self.nextPair)):
      model = self.nextPair[i]
      modelIdx = self.surveyDF.index[self.surveyDF["ModelName"] == model][0]
      self.surveyDF.at[modelIdx, "GamesPlayed"] += 1
      self.surveyDF.at[modelIdx, "TimeLastPlayed"] = datetime.datetime.now()
      self.scansAndModelsDict[model][scan] += 1

    # Add a row to the elo history table

    parameterNode = self.getParameterNode()
    eloHistoryTable = parameterNode.GetNodeReference(self.ELO_HISTORY_TABLE)

    eloHistoryTable.AddEmptyRow()
    rowIdx = eloHistoryTable.GetNumberOfRows() - 1
    eloHistoryTable.SetCellText(rowIdx, 0, str(self.totalComparisonCount))

    modelNames = self.scansAndModelsDict.keys()
    i = 0
    for modelName in modelNames:
      i += 1
      modelIdx = self.surveyDF.index[self.surveyDF["ModelName"] == modelName][0]
      eloHistoryTable.SetCellText(rowIdx, i, str(self.surveyDF.at[modelIdx, "Elo"]))

  def getNextPair(self, isNewCsv):
    # Randomly choose first matchup
    if self.sessionComparisonCount == 0 and isNewCsv:
      models = self.surveyDF["ModelName"].tolist()
      nextModelPair = random.sample(models, 2)

    else:
      nextModelPair = []
      # Get list of models with minimum games played
      minGamesIndexes = self.surveyDF.index[self.surveyDF["GamesPlayed"] == self.surveyDF["GamesPlayed"].min()].tolist()

      if len(minGamesIndexes) == 1:
        # No ties
        leastModel = self.surveyDF.iloc[minGamesIndexes[0]]["ModelName"]
        nextModelPair.append(leastModel)
      else:
        # Pick first model with least recent date played
        minGamesDF = self.surveyDF.iloc[minGamesIndexes]
        leastModel = self.surveyDF.query(f"TimeLastPlayed == '{minGamesDF['TimeLastPlayed'].min()}'").iloc[0]["ModelName"]
        nextModelPair.append(leastModel)

      # Sample list of models with probability based on elo difference
      leastModelElo = self.surveyDF.query(f"ModelName == '{leastModel}'").iloc[0]["Elo"]
      eloDiffList = (self.surveyDF["Elo"] - leastModelElo).abs().tolist()
      if all(eloDiff == 0 for eloDiff in eloDiffList):
        validModel = False
        while not validModel:
          chosenModelIdx = rng.integers(0, len(eloDiffList))
          if self.surveyDF.iloc[chosenModelIdx]["ModelName"] != leastModel:
            validModel = True
      else:
        samplingWeights = self.getModelSamplingProbability(eloDiffList)
        chosenModelIdx = random.choices(list(enumerate(eloDiffList)), weights=samplingWeights)[0][0]
      closestEloModel = self.surveyDF.iloc[chosenModelIdx]["ModelName"]
      nextModelPair.append(closestEloModel)

    # Choose scan with least number of games
    minDictList = []
    for model in nextModelPair:
      modelScans = self.scansAndModelsDict[model].items()
      # workaround to issue of scan getting picked when not the least played
      minDictList.append(min(random.sample(modelScans, len(modelScans)), key=lambda x: x[1]))
    minScan = min(minDictList, key=lambda x: x[1])[0]
    nextModelPair.insert(0, minScan)
    # Remember previous pair
    if self.sessionComparisonCount != 0:
      self.previousPair = self.nextPair
    self.nextPair = nextModelPair

  def getModelSamplingProbability(self, eloDiffList):
    probs = []
    for eloDiff in eloDiffList:
      if eloDiff == 0:
        probs.append(0)
      else:
        probs.append(math.exp(-self.EXP_SCALING_FACTOR * eloDiff))
    return probs

  def getPairFromSurveyTable(self):
    leftScanName = self.surveyTable.GetCellText(self.totalComparisonCount, self.LEFT_MODEL_COL - 1)
    rightScanName = self.surveyTable.GetCellText(self.totalComparisonCount, self.RIGHT_MODEL_COL - 1)
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

    #todo: We should probably use parallel projection and actual FOV. Now FOV is just camera-focus distance.
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

    volumeRenderingLogic = slicer.modules.volumerendering.logic()

    volumeName1 = self.nameFromPatientSequenceAndModel(self.nextPair[0], self.nextPair[1])
    volumeNode1 = parameterNode.GetNodeReference(volumeName1)
    displayNode1 = volumeRenderingLogic.GetFirstVolumeRenderingDisplayNode(volumeNode1)
    displayNode1.SetVisibility(False)

    volumeName2 = self.nameFromPatientSequenceAndModel(self.nextPair[0], self.nextPair[2])
    volumeNode2 = parameterNode.GetNodeReference(volumeName2)
    displayNode2 = volumeRenderingLogic.GetFirstVolumeRenderingDisplayNode(volumeNode2)
    displayNode2.SetVisibility(False)

  def prepareDisplay(self, thresholdValue):
    """
    Prepare views and show models in each view
    :param thresholdValue: intensity value around which opaque voxels should gradually transition to transparent
    :returns: None
    """
    parameterNode = self.getParameterNode()

    # Prevent errors from previous or next buttons when the volumes haven't been loaded in yet

    if not self.scansAndModelsDict:
      logging.warning("Volumes not loaded yet")
      return

    slicer.app.setRenderPaused(True)

    # Set up left side view

    volumeName1 = self.nameFromPatientSequenceAndModel(self.nextPair[0], self.nextPair[1])
    volumeNode1 = parameterNode.GetNodeReference(volumeName1)
    viewNode1 = slicer.mrmlScene.GetSingletonNode("1", "vtkMRMLViewNode")
    viewNode1.LinkedControlOn()
    volumeDisplayNode1 = self.setVolumeRenderingProperty(volumeNode1, self.WINDOW, thresholdValue)
    volumeDisplayNode1.SetViewNodeIDs([viewNode1.GetID()])
    volumeDisplayNode1.SetVisibility(True)
    self.centerAndRotateCamera(volumeNode1, viewNode1)
    viewNode1.SetOrientationMarkerType(viewNode1.OrientationMarkerTypeHuman)
    viewNode1.SetOrientationMarkerSize(viewNode1.OrientationMarkerSizeSmall)

    # Set up right side view

    volumeName2 = self.nameFromPatientSequenceAndModel(self.nextPair[0], self.nextPair[2])
    volumeNode2 = parameterNode.GetNodeReference(volumeName2)
    viewNode2 = slicer.mrmlScene.GetSingletonNode("2", "vtkMRMLViewNode")
    viewNode2.LinkedControlOn()
    volumeDisplayNode2 = self.setVolumeRenderingProperty(volumeNode2, self.WINDOW, thresholdValue)
    volumeDisplayNode2.SetViewNodeIDs([viewNode2.GetID()])
    volumeDisplayNode2.SetVisibility(True)
    self.centerAndRotateCamera(volumeNode2, viewNode2)
    viewNode2.SetOrientationMarkerType(viewNode2.OrientationMarkerTypeHuman)
    viewNode2.SetOrientationMarkerSize(viewNode2.OrientationMarkerSizeSmall)

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

    slicer.app.setRenderPaused(False)

  def addRecordInTable(self, leftScore):
    self.surveyTable.AddEmptyRow()
    rowIdx = self.surveyTable.GetNumberOfRows() - 1
    namesVolumesToDisplay = [self.nameFromPatientSequenceAndModel(self.nextPair[0], self.nextPair[1]),
                             self.nameFromPatientSequenceAndModel(self.nextPair[0], self.nextPair[2])]
    self.surveyTable.SetCellText(rowIdx, 0, str(rowIdx + 1))
    self.surveyTable.SetCellText(rowIdx, 1, namesVolumesToDisplay[0])
    self.surveyTable.SetCellText(rowIdx, 2, str(leftScore))
    self.surveyTable.SetCellText(rowIdx, 3, namesVolumesToDisplay[1])
    self.surveyTable.SetCellText(rowIdx, 4, str(1.0-leftScore))

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
