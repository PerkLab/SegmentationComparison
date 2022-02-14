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
    # TODO: make this more human readable by adding spaces
    self.parent.title = "SegmentationComparison"
    # TODO: set categories (folders where the module shows up in the module selector)
    self.parent.categories = ["Ultrasound"]
    # TODO: add here list of module names that this module requires
    self.parent.dependencies = []
    # TODO: replace with "Firstname Lastname (Organization)"
    self.parent.contributors = ["Keiran Barr (Perk Lab)"]
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
This module is for comparing volumes, and contains a built-in survey portion to record the preferences of the user.
See more information in <a href="https://github.com/keiranbarr/SegmentationComparison">module documentation</a>.
"""
    # TODO: replace with organization, grant and thanks
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
  THRESHOLD_SLIDER_MIDDLE_VALUE = 152

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False

    self.defaultSurveyMessage = "Rate the displayed volumes on a scale from 1 to 5:"

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
    self.addObserver(slicer.mrmlScene,
                     slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene,
                     slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).

    self.ui.imageThresholdSliderWidget.connect("valueChanged(int)", self.onThresholdSliderValueChanged)
    self.ui.imageThresholdSliderWidget.connect(
      "sliderPressed()",
      lambda: logging.info("Threshold slider pressed.")
    )
    thresholdPercentage = self.getThresholdPercentage(self.ui.imageThresholdSliderWidget.value)
    self.ui.thresholdPercentageLabel.text = str(int(thresholdPercentage)) + "%"

    lastInputPath = slicer.util.settingsValue(self.LAST_INPUT_PATH_SETTING, "")
    if lastInputPath != "":
      self.ui.inputDirectorySelector.directory = lastInputPath

    lastOutputPath = slicer.util.settingsValue(self.LAST_OUTPUT_PATH_SETTING, "")
    if lastOutputPath != "":
      self.ui.outputDirectorySelector.directory = lastOutputPath

    # Inputs
    self.ui.csvPathSelector.connect("currentPathChanged(const QString)", self.onCSVPathChanged)
    self.ui.clearCSVPathButton.connect("clicked()", self.onClearButtonPressed)
    self.ui.inputDirectorySelector.connect("directoryChanged(const QString)", self.onInputVolumeDirectorySelected)
    self.ui.loadButton.connect('clicked()', self.onLoadButton)

    # Comparison
    self.ui.resetCameraButton.connect('clicked()', self.onResetCameraButton)
    self.ui.leftGroup.buttonClicked.connect(self.onLeftGroup)
    self.ui.rightGroup.buttonClicked.connect(self.onRightGroup)
    self.ui.nextButton.connect('clicked()', self.onNextButton)
    self.ui.previousButton.connect('clicked()', self.onPreviousButton)
    self.ui.saveButton.connect('clicked()', self.onSaveButton)

    # Settings
    self.ui.outputDirectorySelector.connect("directoryChanged(const QString)", self.onOutputDirectorySelected)

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()

    # sets the name of each button in the survey
    # e.g. L_3 corresponds to the left side recieving 3 stars
    self.setNameOfButtons(self.ui.leftGroup, "L_")
    self.setNameOfButtons(self.ui.rightGroup, "R_")

  def setNameOfButtons(self, buttonGroup, startOfName):
    index = 1
    for button in buttonGroup.buttons():
      buttonName = startOfName + str(index)
      button.setAccessibleName(buttonName)
      index += 1

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

    # Update node selectors and sliders
    self.ui.imageThresholdSliderWidget.value = float(
      self._parameterNode.GetParameter("Threshold"))

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
    thresholdPercentage = self.getThresholdPercentage(value)
    self.ui.thresholdPercentageLabel.text = str(round(thresholdPercentage)) + "%"
    try:
      # Prevent thresholding when volumes have not yet been loaded
      if self.logic.nextPair:
        # Iterate through currently displayed volumes
        currentSceneData = self.logic.nextPair
        for i in range(1, len(currentSceneData)):
          volumeName = self.logic.nameFromPatientSequenceAndModel(currentSceneData[0], currentSceneData[i])
          inputVolume = self._parameterNode.GetNodeReference(volumeName)
          # prevents invalid volume error when loading the widget
          if inputVolume is not None:
            self.logic.threshold(inputVolume, value)
    except Exception as e:
      slicer.util.errorDisplay("Failed to threshold the selected volume(s): "+str(e))
      import traceback
      traceback.print_exc()

  def getThresholdPercentage(self, value):
    thresholdPercentage = self.logic.calculateScaledScore(
      value,
      rmin=0,
      rmax=255 + self.logic.WINDOW,
      tmin=100,
      tmax=0
    )
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

        if self.logic.surveyStarted:
          self.logic.surveyStarted = False

        self.logic.loadVolumes(self.ui.inputDirectorySelector.directory)
        csvPath = self.ui.csvPathSelector.currentPath
        self.logic.setSurveyHistory(csvPath)
        self.logic.setSurveyTable(csvPath)

        # self.logic.loadAndApplyTransforms(self.ui.inputDirectorySelector.directory)
        self.changeScene(0)
        self.loadSurveyMessage(self.ui.inputDirectorySelector.directory)

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

  def loadSurveyMessage(self, directory):
    # Change survey message if "message.txt" found in input directory

    textFilesInDirectory = list(f for f in os.listdir(directory) if f.endswith(".txt"))

    customMessage = False

    for textIndex, textFile in enumerate(textFilesInDirectory):
      name = str(os.path.basename(textFile))
      path = directory + "/" + name

      if name == "message.txt":
        with open(path) as f:
          message = f.read()

        self.ui.surveyMessage.setText(message)
        customMessage = True

    # Reset to default if "message.txt" is not in directory
    if customMessage == False:
      self.ui.surveyMessage.setText(self.defaultSurveyMessage)

  def onResetCameraButton(self):
    logging.info("onResetCameraButton()")
    self.ui.imageThresholdSliderWidget.value = self.THRESHOLD_SLIDER_MIDDLE_VALUE
    self.logic.prepareDisplay(self.ui.imageThresholdSliderWidget.value)

  def onPreviousButton(self):
    logging.info("onPreviousButton()")
    # prevent wraparound
    if self.logic.sessionComparisonCount != 0:
      self.changeScene(-1)

  def onNextButton(self):
    logging.info("onNextButton()")
    self.changeScene(1)

  def changeScene(self, factor):
    # Change pair of images being evaluated. Factor -1 is used for previous image, 0 is for current image, and +1 is
    self.uncheckSurveyButtons()
    self.logic.sessionComparisonCount += factor
    self.logic.totalComparisonCount += factor
    self.ui.totalComparisonLabel.text = str(self.logic.totalComparisonCount)
    self.ui.sessionComparisonLabel.text = str(self.logic.sessionComparisonCount)

    # self.ui.imageThresholdSliderWidget.reset()
    if self.logic.sessionComparisonCount != 0 and factor == 1:
      self.logic.updateComparisonData()

    if factor == -1:
      self.logic.nextPair = self.logic.previousPair
      self.logic.surveyDF = self.logic.previousDF
    else:
      self.logic.getNextPair(self.ui.csvPathSelector.currentPath == "")
      self.logic.addRecordInTable()
    self.logic.prepareDisplay(self.ui.imageThresholdSliderWidget.value)

    self.repopulateSurveyButtons()
    self.enablePreviousAndNextButtons()

  def enablePreviousAndNextButtons(self):
    # This function exists to ensure that, when these two buttons are enabled,
    # they aren't allowing the user to click previous on the first volume.
    # or next on the last volume. Also, the two compared models have to be rated
    # before moving forward or back.
    if self.logic.sessionComparisonCount == 0:
      self.ui.previousButton.setEnabled(False)
    else:
      self.ui.previousButton.setEnabled(True)

    if self.ui.leftGroup.checkedButton() and self.ui.rightGroup.checkedButton():
      self.ui.nextButton.setEnabled(True)
    else:
      self.ui.nextButton.setEnabled(False)

  def onLeftGroup(self):
    rating = self.ui.leftGroup.checkedButton().accessibleName
    self.onRating(rating)
    ratingString = rating.split("_")[-1]
    logging.info(f"Rating of {ratingString} selected for left volume.")

  def onRightGroup(self):
    rating = self.ui.rightGroup.checkedButton().accessibleName
    self.onRating(rating)
    ratingString = rating.split("_")[-1]
    logging.info(f"Rating of {ratingString} selected for right volume.")

  def onRating(self, rating):
    # Prevents rating before any volumes have been loaded
    if self.logic.scansAndModelsDict:
      self.enablePreviousAndNextButtons()
      self.logic.recordRatingInTable(rating)
    else:
      slicer.util.infoDisplay("Volumes must be loaded in order to start the survey")
      self.uncheckSurveyButtons()

  def repopulateSurveyButtons(self):
    # This function uses the table of survey results to display prior answers

    leftModelRating = self.logic.surveyTable.GetCellText(self.logic.totalComparisonCount, self.logic.LEFT)
    rightModelRating = self.logic.surveyTable.GetCellText(self.logic.totalComparisonCount, self.logic.RIGHT)

    leftSurveyButton = "L_"+str(leftModelRating)
    rightSurveyButton = "R_"+str(rightModelRating)

    allButtons = self.ui.leftGroup.buttons() + self.ui.rightGroup.buttons()
    for button in allButtons:
      if button.accessibleName == rightSurveyButton:
        button.setChecked(True)

      if button.accessibleName == leftSurveyButton:
        button.setChecked(True)

  def uncheckSurveyButtons(self):
    self.ui.leftGroup.setExclusive(False)
    self.ui.rightGroup.setExclusive(False)

    allButtons = self.ui.leftGroup.buttons() + self.ui.rightGroup.buttons()
    for button in allButtons:
      button.setChecked(False)

    self.ui.rightGroup.setExclusive(True)
    self.ui.leftGroup.setExclusive(True)

  def onSaveButton(self):
    logging.info("onSaveButton()")
    confirmation = slicer.util.confirmYesNoDisplay("Exit survey and save results?")
    try:
      if confirmation:
        surveyTable = self._parameterNode.GetNodeReference(self.logic.RESULTS_TABLE_NAME)
        if (surveyTable.GetCellText(self.logic.totalComparisonCount, self.logic.LEFT) == "" and
          surveyTable.GetCellText(self.logic.totalComparisonCount, self.logic.RIGHT) == ""):
          surveyTable.RemoveRow(self.logic.totalComparisonCount)
        # Save history as csv
        historySaveFilename = self.ui.outputDirectorySelector.directory + "/comparison_history_" + time.strftime("%Y%m%d-%H%M%S") + ".csv"
        slicer.util.saveNode(surveyTable, historySaveFilename)

        # Save pandas dataframe to csv
        resultsSavePath = self.ui.outputDirectorySelector.directory + "/elo_scores_" + time.strftime(
          "%Y%m%d-%H%M%S") + ".csv"
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

  N_COLUMNS_VIEW = 2
  N_ROWS_VIEW = 1
  VIEW_FIRST_DIGITS = 587
  LEFT = 2
  RIGHT = 4
  RESULTS_TABLE_NAME = "SurveyResultsTable"
  DEFAULT_ELO = 1000
  K = 32
  DF_COLUMN_NAMES = ["ModelName", "Elo", "GamesPlayed", "TimeLastPlayed"]
  WINDOW = 50

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)

    self.scansAndModelsDict = {}
    self.surveyDF = None
    self.surveyStarted = False
    self.surveyFinished = False
    self.nextPair = None
    self.previousPair = None
    self.sessionComparisonCount = 0
    self.totalComparisonCount = 0
    self.surveyTable = None
    self.previousDF = None
    
  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Threshold"):
      parameterNode.SetParameter("Threshold", "0")

  def setSurveyHistory(self, csvPath):
    parameterNode = self.getParameterNode()
    if csvPath:
      # Load corresponding comparison history csv
      csvFileName = os.path.basename(csvPath)
      timestamp = csvFileName.split("_")[-1]
      csvRoot = os.path.abspath(os.path.join(csvPath, os.pardir))
      historyPath = os.path.join(csvRoot, "comparison_history_" + timestamp)
      self.surveyTable = slicer.util.loadTable(historyPath)
      self.surveyTable.SetName(self.RESULTS_TABLE_NAME)
      parameterNode.SetNodeReferenceID(self.RESULTS_TABLE_NAME, self.surveyTable.GetID())
      self.totalComparisonCount = self.surveyTable.GetNumberOfRows()

    else:
      # Reset survey table used to store survey results
      self.surveyTable = parameterNode.GetNodeReference(self.RESULTS_TABLE_NAME)
      if self.surveyTable:
        slicer.mrmlScene.RemoveNode(self.surveyTable)

      self.surveyTable = slicer.vtkMRMLTableNode()
      addedSurveyTable = slicer.mrmlScene.AddNode(self.surveyTable)
      addedSurveyTable.SetName(self.RESULTS_TABLE_NAME)
      parameterNode.SetNodeReferenceID(self.RESULTS_TABLE_NAME, addedSurveyTable.GetID())

      col = self.surveyTable.AddColumn()
      col.SetName('Comparison')
      col = self.surveyTable.AddColumn()
      col.SetName('Model_L')
      col = self.surveyTable.AddColumn()
      col.SetName('Score_L')
      col = self.surveyTable.AddColumn()
      col.SetName('Model_R')
      col = self.surveyTable.AddColumn()
      col.SetName('Score_R')

      self.totalComparisonCount = 0

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

  def resetScene(self):
    slicer.mrmlScene.Clear()

    # The following lines clean up things that aren't affected by clearing the scene
    views = slicer.mrmlScene.GetNodesByClass("vtkMRMLViewNode")
    views.UnRegister(None)
    for view in views:
      slicer.mrmlScene.RemoveNode(view)

    cameras = slicer.mrmlScene.GetNodesByClass("vtkMRMLCameraNode")
    cameras.UnRegister(None)
    for camera in cameras:
      slicer.mrmlScene.RemoveNode(camera)

    # If the layout is not changed from the custom one, then it will result in weird problems when numbering the views
    slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    # Reset comparison counter
    self.sessionComparisonCount = 0

  def loadAndApplyTransforms(self, directory):
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
    return

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
    leftRating = int(self.surveyTable.GetCellText(self.sessionComparisonCount - 1, self.LEFT))
    rightRating = int(self.surveyTable.GetCellText(self.sessionComparisonCount - 1, self.RIGHT))
    leftActual = self.calculateScaledScore(leftRating - rightRating)
    rightActual = self.calculateScaledScore(rightRating - leftRating)
    return leftActual, rightActual

  def calculateNewElo(self, current, actual, expected):
    return current + self.K * (actual - expected)

  def updateComparisonData(self):
    # Store previous dataframe state
    self.previousDF = self.surveyDF.copy()

    # Update elo scores
    leftModel = self.nextPair[1]
    rightModel = self.nextPair[2]
    leftElo = self.surveyDF.query(f"ModelName == '{leftModel}'").iloc[0]["Elo"]
    rightElo = self.surveyDF.query(f"ModelName == '{rightModel}'").iloc[0]["Elo"]
    leftExpected, rightExpected = self.calculateExpectedScores(leftElo, rightElo)
    leftActual, rightActual = self.calculateActualScores()
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

      # Pick model with closest elo score
      leastModelElo = self.surveyDF.query(f"ModelName == '{leastModel}'").iloc[0]["Elo"]
      sortedEloDiffIdx = (self.surveyDF["Elo"] - leastModelElo).abs().argsort()
      if self.surveyDF.iloc[sortedEloDiffIdx[1]]["ModelName"] != leastModel:
        closestModelIdx = 1
      else:
        closestModelIdx = 0
      closestEloModel = self.surveyDF.iloc[sortedEloDiffIdx[closestModelIdx]]["ModelName"]
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

  def centerAndRotateCamera(self, volume, viewNode):
    # Compute the RAS coordinates of the center of the volume
    imageData = volume.GetImageData() 
    volumeCenter_Ijk = imageData.GetCenter()

    IjkToRasMatrix = vtk.vtkMatrix4x4()
    volume.GetIJKToRASMatrix(IjkToRasMatrix)
    volumeCenter_Ras = np.array(IjkToRasMatrix.MultiplyFloatPoint(np.append(volumeCenter_Ijk, [1])))
    volumeCenter_Ras = volumeCenter_Ras[:3]

    # Center camera on the volume, rotate camera so top is superior, position camera behind volume
    camerasLogic = slicer.modules.cameras.logic()
    cameraNode = camerasLogic.GetViewActiveCameraNode(viewNode)
    camera = cameraNode.GetCamera()

    camera.SetFocalPoint(volumeCenter_Ras)
    camera.SetViewUp([0, 0, 1])
    camera.SetPosition(volumeCenter_Ras + np.array([0, -2500, 0]))
    cameraNode.ResetClippingRange()

    # equivalent to pressing the "center 3D view" button
    layoutManager = slicer.app.layoutManager()

    threeDWidget = layoutManager.viewWidget(viewNode)
    threeDView = threeDWidget.threeDView()
    threeDView.resetFocalPoint()

  # Manually define volume property for volume rendering
  def setVolumeRenderingProperty(self, volumeNode, window, level):

    vrLogic = slicer.modules.volumerendering.logic()
    displayNode = vrLogic.GetFirstVolumeRenderingDisplayNode(volumeNode)

    if displayNode is None:
      volumeNode.CreateDefaultDisplayNodes()
      vrLogic.CreateDefaultVolumeRenderingNodes(volumeNode)
      displayNode = vrLogic.GetFirstVolumeRenderingDisplayNode(volumeNode)

    upper = min(265, level + window/2)
    lower = max(2, level - window/2)

    if upper <= lower:
      upper = lower + 1

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

  def makeCustomView(self, customLayoutId, numberOfRows, numberOfColumns, volumesToDisplay, firstViewNode):

    numberOfVolumes = len(volumesToDisplay)

    customLayout = '<layout type="vertical">'
    viewIndex = 0
    for rowIndex in range(numberOfRows):
      customLayout += '<item><layout type="horizontal">'
      for colIndex in range(numberOfColumns):
        if viewIndex < numberOfVolumes: 
          name = str(viewIndex + firstViewNode)
          tag = volumesToDisplay[viewIndex]
        else: 
          name = ""
          tag = ""
        customLayout += '<item><view class="vtkMRMLViewNode" singletontag="' + tag
        customLayout += '"><property name="viewlabel" action="default">'+name+'</property></view></item>'
        viewIndex += 1
      customLayout += '</layout></item>'
      
    customLayout += '</layout>'
    if not slicer.app.layoutManager().layoutLogic().GetLayoutNode().SetLayoutDescription(customLayoutId, customLayout):
        slicer.app.layoutManager().layoutLogic().GetLayoutNode().AddLayoutDescription(customLayoutId, customLayout)

  def nameFromPatientSequenceAndModel(self, patientSequence, model):
    # Get the full volume name by combining elements of patientSequence and model
    patientId = patientSequence.split("_")[0]
    volumeName = str(patientId) + "_" + model + "_" + "_".join(patientSequence.split("_")[1:])
    return volumeName

  def prepareDisplay(self, thresholdValue):
    # Prepare views and show models in each view
    parameterNode = self.getParameterNode()

    # Prevent errors from previous or next buttons when the volumes haven't been loaded in yet
    if self.scansAndModelsDict:
      # Code related to the 3D view is taken from here:
      # https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html
      slicer.app.setRenderPaused(True)

      customID = self.VIEW_FIRST_DIGITS + self.sessionComparisonCount
      namesVolumesToDisplay = [self.nameFromPatientSequenceAndModel(self.nextPair[0], self.nextPair[1]),
                               self.nameFromPatientSequenceAndModel(self.nextPair[0], self.nextPair[2])]
      existingViewNode = False

      # If the view node already exists, center the camera before switching views
      # This prevents the user from seeing the camera centering
      if parameterNode.GetNodeReference("View" + namesVolumesToDisplay[0] + str(customID)):
        existingViewNode = True
      else: 
        self.makeCustomView(customID, self.N_ROWS_VIEW, self.N_COLUMNS_VIEW, namesVolumesToDisplay, 0)
        slicer.app.layoutManager().setLayout(customID)

      # Iterate through each volume, and display it in its own corresponding view
      for volumeIndex, volumeName in enumerate(namesVolumesToDisplay):
        volume = parameterNode.GetNodeReference(volumeName)

        viewNode = slicer.mrmlScene.GetSingletonNode(volumeName, "vtkMRMLViewNode")
        viewNode.LinkedControlOn()

        displayNode = self.setVolumeRenderingProperty(volume, self.WINDOW, thresholdValue)
        displayNode.SetViewNodeIDs([viewNode.GetID()])

        self.centerAndRotateCamera(volume, viewNode)
        viewNode.SetOrientationMarkerType(viewNode.OrientationMarkerTypeHuman)
        viewNode.SetOrientationMarkerSize(viewNode.OrientationMarkerSizeSmall)

      # Add identifiers/titles in the 3D views
      for i in range(0, slicer.app.layoutManager().threeDViewCount):
        viewWidget = slicer.app.layoutManager().threeDWidget(i)
        viewWidget.threeDView().cornerAnnotation().SetText(vtk.vtkCornerAnnotation.UpperRight,
                                                           viewWidget.objectName.split("ThreeDWidget")[1])
        viewWidget.threeDView().cornerAnnotation().GetTextProperty().SetColor(1, 1, 1)

      if existingViewNode:
        # the pause allows for the camera centering to actually complete before switching views
        time.sleep(0.1)
        slicer.app.layoutManager().setLayout(customID)

      slicer.app.setRenderPaused(False)

  def addRecordInTable(self):
    # Prevent new row from being added after pressing next following a previous click
    if self.totalComparisonCount < self.surveyTable.GetNumberOfRows():
      return
    # Add new record to table
    self.surveyTable.AddEmptyRow()
    rowIdx = self.surveyTable.GetNumberOfRows() - 1
    namesVolumesToDisplay = [self.nameFromPatientSequenceAndModel(self.nextPair[0], self.nextPair[1]),
                             self.nameFromPatientSequenceAndModel(self.nextPair[0], self.nextPair[2])]
    self.surveyTable.SetCellText(rowIdx, 0, str(rowIdx + 1))
    self.surveyTable.SetCellText(rowIdx, 1, namesVolumesToDisplay[0])
    self.surveyTable.SetCellText(rowIdx, 3, namesVolumesToDisplay[1])

  def recordRatingInTable(self, buttonId):
    if not self.surveyStarted:
      self.surveyStarted = True

    # Split the name
    side = buttonId.split("_")[0]
    rating = int(buttonId.split("_")[1])
    rowIdx = self.totalComparisonCount

    if side == "L":
      self.surveyTable.SetCellText(rowIdx, self.LEFT, str(rating))
    elif side == "R":
      self.surveyTable.SetCellText(rowIdx, self.RIGHT, str(rating))
    else:
      slicer.util.errorDisplay("ERROR: Invalid button Id")

  def threshold(self, inputVolume, imageThreshold):
    if not inputVolume:
      raise ValueError("Input volume is invalid")
    self.setVolumeRenderingProperty(inputVolume, self.WINDOW, imageThreshold - self.WINDOW / 2)

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

    import SampleData
    registerSampleData()
    inputVolume = SampleData.downloadSample('SegmentationComparison1')
    self.delayDisplay('Loaded test data set')

    inputScalarRange = inputVolume.GetImageData().GetScalarRange()
    self.assertEqual(inputScalarRange[0], 0)
    self.assertEqual(inputScalarRange[1], 695)

    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    threshold = 100

    # Test the module logic

    logic = SegmentationComparisonLogic()

    # Test algorithm with non-inverted threshold
    logic.threshold(inputVolume, outputVolume, threshold, True)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], threshold)

    # Test algorithm with inverted threshold
    logic.threshold(inputVolume, outputVolume, threshold, False)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], inputScalarRange[1])

    self.delayDisplay('Test passed')
