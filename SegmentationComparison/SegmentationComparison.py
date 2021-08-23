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
import math
import time


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

  LAST_INPUT_PATH_SETTING="SegmentationComparison/LastInputPath"
  LAST_OUTPUT_PATH_SETTING="SegmentationComparison/LastOutputPath"

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


    self.ui.imageThresholdSliderWidget.connect(
        "valueChanged(double)", self.autoUpdateThresholdSlider)

    lastInputPath = slicer.util.settingsValue(self.LAST_INPUT_PATH_SETTING, "")
    if lastInputPath != "":
      self.ui.inputDirectorySelector.directory = lastInputPath

    lastOutputPath = slicer.util.settingsValue(self.LAST_OUTPUT_PATH_SETTING, "")
    if lastOutputPath != "":
      self.ui.outputDirectorySelector.directory = lastOutputPath


    self.ui.inputDirectorySelector.connect("directoryChanged(const QString)", self.onInputDirectorySelected)

    self.ui.outputDirectorySelector.connect("directoryChanged(const QString)", self.onOutputDirectorySelected)

    # Buttons
    self.ui.loadButton.connect('clicked(bool)', self.onLoadButton)

    self.ui.nextButton.connect('clicked(bool)', self.onNextButton)

    self.ui.previousButton.connect('clicked(bool)', self.onPreviousButton)

    self.ui.resetCameraButton.connect('clicked(bool)', self.onResetCameraButton)

    self.ui.saveButton.connect('clicked(bool)', self.onSaveButton)


    self.ui.leftGroup.buttonClicked.connect(self.onLeftGroup)

    self.ui.rightGroup.buttonClicked.connect(self.onRightGroup)

    self.ui.randomizeBox.stateChanged.connect(self.onRandomizeBox)


    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()

    # sets the name of each button in the survey
    # e.g. L_3 corresponds to the left side recieving 3 stars
    self.setNameOfButtons(self.ui.leftGroup, "L_")
    self.setNameOfButtons(self.ui.rightGroup, "R_")

    # update randomizeOutput from checkbox in UI
    if self.ui.randomizeBox.checkState()==0:
      self.randomizeOutput = False
    else:
      self.randomizeOutput = True

    
  def setNameOfButtons(self, buttonGroup, startOfName):
    index = 1
    for button in buttonGroup.buttons():
      buttonName = startOfName + str(index)
      button.setAccessibleName(buttonName)

      index += 1


  # set the output directory to the input directory as a default
  def onInputDirectorySelected(self, selectedPath):
    settings = qt.QSettings()
    settings.setValue(self.LAST_INPUT_PATH_SETTING, selectedPath)

    self.ui.outputDirectorySelector.directory = selectedPath
    settings.setValue(self.LAST_OUTPUT_PATH_SETTING, selectedPath)

    self.updateParameterNodeFromGUI()


  def onOutputDirectorySelected(self, selectedPath):
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
  def autoUpdateThresholdSlider(self):

    try:
      # prevent thresholding when volumes have not yet been loaded
      if self.logic.volumesArray != np.zeros((0,0), dtype='object'):
        # iterate through currently displayed volumes
        for volume in self.logic.volumesArray[self.logic.currentSceneIndex]:
          inputVolume = slicer.util.getFirstNodeByClassByName("vtkMRMLScalarVolumeNode",volume)

          # prevents invalid volume error when loading the widget
          if inputVolume is not None:
            self.logic.threshold(inputVolume, self.ui.imageThresholdSliderWidget.value)

    except Exception as e:
      slicer.util.errorDisplay("Failed to threshold the selected volume(s): "+str(e))
      import traceback
      traceback.print_exc()



  def onLoadButton(self):
    if self.logic.surveyStarted:
      confirmation = slicer.util.confirmYesNoDisplay("WARNING: This will delete all survey progress. Proceed?")

    else: 
      confirmation = slicer.util.confirmYesNoDisplay("Loading this folder will clear the scene. Proceed?")

    if confirmation == True: 
      
      if self.logic.surveyStarted:
        self.ui.progressBar.reset()
        self.logic.surveyStarted=False

      self.uncheckSurveyButtons()

      self.logic.loadVolumes(self.ui.inputDirectorySelector.directory, self.randomizeOutput)
      self.logic.loadAndApplyTransforms(self.ui.inputDirectorySelector.directory)

      self.logic.currentSceneIndex = 0
      self.logic.prepareDisplay(0,self.ui.imageThresholdSliderWidget.value)

      self.loadSurveyMessage(self.ui.inputDirectorySelector.directory)

      if len(self.logic.volumesArray[0]) > 2:
        slicer.util.infoDisplay("More than 2 models are being compared. The survey portion will not work as intended.")


  # change survey message if "message.txt" found in input directory
  def loadSurveyMessage(self, directory):
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

    # reset to default if message is removed from directory and module is reloaded
    if customMessage == False:
      self.ui.surveyMessage.setText(self.defaultSurveyMessage)
      

  def onResetCameraButton(self):
    self.logic.prepareDisplay(self.logic.currentSceneIndex,self.ui.imageThresholdSliderWidget.value)


  def onPreviousButton(self):
    # prevent wraparound
    if self.logic.currentSceneIndex!=0:
      self.changeScene(-1)


  def onNextButton(self):
    # prevent wraparound
    if self.logic.currentSceneIndex!=self.logic.numberOfScenes-1:
      self.changeScene(1)


  def changeScene(self,factor):
    self.uncheckSurveyButtons()
    self.logic.currentSceneIndex += factor

    self.ui.imageThresholdSliderWidget.reset()

    self.logic.prepareDisplay(self.logic.currentSceneIndex,self.ui.imageThresholdSliderWidget.value)
    self.repopulateSurveyButtons()


  def onRandomizeBox(self, checkState):
    if checkState == qt.Qt.Checked:
      self.randomizeOutput = True
    elif checkState == qt.Qt.Unchecked:
      self.randomizeOutput = False


  def onLeftGroup(self):
    rating = self.ui.leftGroup.checkedButton().accessibleName
    self.onRating(rating)

  def onRightGroup(self):
    rating = self.ui.rightGroup.checkedButton().accessibleName
    self.onRating(rating)

  def onRating(self,rating):
    # prevents rating before any volumes have been loaded
    if self.logic.volumesArray != np.zeros((0,0), dtype='object'):
      self.logic.recordRatingInTable(rating)

      # iterate through all of the cells, if there is something there, add it to the total
      totalRated = 0

      for row in range(self.logic.surveyTable.GetNumberOfRows()):
        # the -1 and +1 accounts for the scene column (column 0 in the table)
        for col in range(self.logic.surveyTable.GetNumberOfColumns()-1):
          enteredValue = self.logic.surveyTable.GetCellText(row,col+1)
          if enteredValue != "":
            totalRated+=1

      totalVolumes = self.logic.volumesArray.shape[0] * self.logic.volumesArray.shape[1]
      progress = (totalRated/totalVolumes)*100
      self.ui.progressBar.setValue(int(progress))

      # prevents the dialog from coming up repeatedly if changing answers
      if progress == 100 and self.logic.surveyFinished != True:
        slicer.util.infoDisplay("You have completed the survey. Choose a save path below, and press the Save button.")
        self.logic.surveyFinished = True

    else:
      slicer.util.infoDisplay("Volumes must be loaded in order to start the survey")
      self.uncheckSurveyButtons()


  # this function uses the table of survey results to display prior answers
  def repopulateSurveyButtons(self):

    currentlyDisplayedVolumes = self.logic.volumesArray[self.logic.currentSceneIndex]
    
    leftModelNumber = int(currentlyDisplayedVolumes[0].split("_")[3])
    rightModelNumber = int(currentlyDisplayedVolumes[1].split("_")[3])

    selectedScene = int(currentlyDisplayedVolumes[0].split("_")[1])

    leftModelRating = self.logic.surveyTable.GetCellText(selectedScene,leftModelNumber+1)
    rightModelRating = self.logic.surveyTable.GetCellText(selectedScene,rightModelNumber+1)

    leftSurveyButton = "L_"+str(leftModelRating)
    rightSurveyButton = "R_"+str(rightModelRating)

    allButtons = self.ui.leftGroup.buttons() + self.ui.rightGroup.buttons()
    for button in allButtons:
      if button.accessibleName==leftSurveyButton or button.accessibleName==rightSurveyButton:
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

    if self.logic.surveyFinished:
      confirmation = True

      # this line should prevent the warning to save your changes on exiting slicer
      # but i think i have messed something up, as it doesnt work properly
      filter = CloseApplicationEventFilter()
      slicer.util.mainWindow().installEventFilter(filter)

    else:
      confirmation = slicer.util.confirmYesNoDisplay("You have not yet completed the survey. Proceed?")

    if confirmation:
      import time
      
      sceneSaveFilename = self.ui.outputDirectorySelector.directory + "/saved-scene-" + time.strftime("%Y%m%d-%H%M%S") + ".mrb"
      
      addedSurveyTable = slicer.mrmlScene.AddNode(self.logic.surveyTable)
      addedSurveyTable.SetName("SurveyResultsTable")

      volumesArrayTable = slicer.vtkMRMLTableNode()

      for col in range(self.logic.volumesArray.shape[1]):
       
        column = volumesArrayTable.AddColumn()
        column.SetName("View " + str(col))

        for row in range(self.logic.volumesArray.shape[0]):
          volumesArrayTable.AddEmptyRow()
          volumesArrayTable.SetCellText(row,col,self.logic.volumesArray[row][col])

      addedVolumesArrayTable = slicer.mrmlScene.AddNode(volumesArrayTable)
      addedVolumesArrayTable.SetName("VolumesArrayTable")

      # Save scene
      if slicer.util.saveScene(sceneSaveFilename):
        if self.logic.surveyFinished:
          slicer.util.infoDisplay("Scene saved to: {0}. \n \n You can now close slicer to end the survey.".format(sceneSaveFilename))
        else: 
          slicer.util.infoDisplay("Scene saved to: {0}".format(sceneSaveFilename))

      else:
        slicer.util.errorDisplay("Scene saving failed")


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

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)
    
    self.clearVariables()
    
  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Threshold"):
      parameterNode.SetParameter("Threshold", "0")

  def clearVariables(self):
    self.volumesArray = np.zeros((0,0), dtype='object')

    # scene index is different from scene number if randomize is checked
    # scene index is the selected scene's index in the list of displayed scenes
    # scene number is simply the identification of the scene itself
    self.currentSceneIndex = 0

    self.numberOfScenes = 0

    self.surveyTable = slicer.vtkMRMLTableNode()

    col=self.surveyTable.AddColumn()
    col.SetName('Scene #')
    col=self.surveyTable.AddColumn()
    col.SetName('Model_0')
    col=self.surveyTable.AddColumn()
    col.SetName('Model_1')

    self.surveyStarted = False
    self.surveyFinished = False



  def resetScene(self):
    slicer.mrmlScene.Clear()

    # the following lines clean up things that aren't affected by clearing the scene

    views = slicer.mrmlScene.GetNodesByClass("vtkMRMLViewNode")
    views.UnRegister(None)
    for view in views:
      slicer.mrmlScene.RemoveNode(view)

    cameras = slicer.mrmlScene.GetNodesByClass("vtkMRMLCameraNode")
    cameras.UnRegister(None)
    for camera in cameras:
      slicer.mrmlScene.RemoveNode(camera)

    # if the layout is not changed from the custom one, then it will result in weird problems when numbering the views
    slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)



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
          slicer.util.infoDisplay("A transform doesn't follow the naming scheme. Use DefaultTransform.h5 to set the default transform, and Scene_x_Model_y_Transform.h5 for specific volumes")

    else:
      print("No transforms found in selected folder. To add a transform, save them in the same folder as the volumes. Use this naming scheme: DefaultTransform.h5 to set the default transform, and Scene_x_Model_y_Transform.h5 for specific volumes")



  def loadVolumes(self, directory, randomize):

    # improves readability of console output
    print('\n',"LOAD BUTTON PRESSED, RESETTING THE SCENE",'\n')

    # these two must be called in tandem to fully reset the scene
    self.resetScene()
    self.clearVariables()

    print("Checking directory: " + directory)
    
    volumesInDirectory = list(f for f in os.listdir(directory) if f.endswith(".nrrd"))
    print("Found volumes: " + str(volumesInDirectory))

    volumeArrayXDim = 0
    volumeArrayYDim = 0

    try:

      # determining the dimensions of the array to store the volume references
      for volumeIndex, volumeFile in enumerate(volumesInDirectory):
        name = str(os.path.basename(volumeFile))
        # remove file extension
        name = name.replace('.nrrd','')

        # Splits name according to this naming convention:
        # Scene_x_Model_y.nrrd
        sceneNumber = int(name.split("_")[1])
        modelNumber = int(name.split("_")[3])
        
        if sceneNumber > volumeArrayXDim: volumeArrayXDim = sceneNumber
        if modelNumber > volumeArrayYDim: volumeArrayYDim = modelNumber
        
        self.volumesArray.resize((volumeArrayXDim+1, volumeArrayYDim+1))

        self.numberOfScenes = volumeArrayXDim+1

        slicer.util.loadVolume(directory + "/" + volumeFile)

        self.volumesArray[sceneNumber][modelNumber] = name
      

    except Exception as e:
      slicer.util.errorDisplay("Ensure volumes follow the naming scheme: 'Scene_x_Model_x.nrrd': "+str(e))
      import traceback
      traceback.print_exc()

    if randomize: self.createShuffledArray()

    for row in range(self.numberOfScenes):
      self.surveyTable.AddEmptyRow()



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

    upper = min(255, level + window/2)
    lower = max(0, level - window/2)

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


  # currently, this function will shuffle every time the load volumes button is called
  # this could be good (for testing the randomization feature quickly)
  # but could also be bad (if the user accidentally clicks it, and loses the progress of their survey)
  def createShuffledArray(self):

    for scene in range(len(self.volumesArray)):
      np.random.shuffle(self.volumesArray[scene])

    np.random.shuffle(self.volumesArray)

    print("Shuffled array: ")
    print(self.volumesArray)



  def prepareDisplay(self, selectedScene, thresholdValue):

    # prevent errors from previous or next buttons when the volumes havent been loaded in yet
    if self.volumesArray != np.zeros((0,0), dtype='object'):

      # Code related to the 3D view is taken from here: https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html
      slicer.app.setRenderPaused(True)

      customID = 567 + selectedScene

      numberOfColumns = 2
      numberOfVolumes = len(self.volumesArray[selectedScene])
      numberOfRows = int(math.ceil(numberOfVolumes/numberOfColumns))
      
      firstViewNode = selectedScene*numberOfVolumes
      volumesToDisplay = self.volumesArray[selectedScene]

      existingViewNode = False

      # if the view node already exists
      # center the camera BEFORE switching views
      # this prevents the user from seeing the camera centering
      if slicer.util.getFirstNodeByClassByName("vtkMRMLViewNode","View"+volumesToDisplay[0]):
        existingViewNode = True

      else: 
        self.makeCustomView(customID, numberOfRows, numberOfColumns, volumesToDisplay, firstViewNode)
        slicer.app.layoutManager().setLayout(customID)

      # iterate through each volume, and display it in its own corresponding view
      for volumeIndex, volumeName in enumerate(self.volumesArray[selectedScene]):

        volume = slicer.util.getFirstNodeByClassByName("vtkMRMLScalarVolumeNode", volumeName)

        viewNode = slicer.mrmlScene.GetSingletonNode(volumeName, "vtkMRMLViewNode")
        viewNode.LinkedControlOn()

        displayNode = self.setVolumeRenderingProperty(volume,100,thresholdValue)
        displayNode.SetViewNodeIDs([viewNode.GetID()])

        self.centerAndRotateCamera(volume, viewNode)

        viewNode.SetOrientationMarkerType(viewNode.OrientationMarkerTypeHuman)
        viewNode.SetOrientationMarkerSize(viewNode.OrientationMarkerSizeSmall)

      if existingViewNode:
        # the pause allows for the camera centering to actually complete before switching views
        time.sleep(0.1)
        slicer.app.layoutManager().setLayout(customID)

      slicer.app.setRenderPaused(False)



  def recordRatingInTable(self,buttonId):
    if not self.surveyStarted:
      self.surveyStarted=True

    # split the name
    side = buttonId.split("_")[0]
    rating = int(buttonId.split("_")[1])

    currentlyDisplayedVolumes = self.volumesArray[self.currentSceneIndex]

    if side == "L":
      selectedVolume = currentlyDisplayedVolumes[0]

    elif side == "R":
      selectedVolume = currentlyDisplayedVolumes[1]

    else:
      slicer.util.errorDisplay("ERROR: Invalid button Id")

    selectedModel = int(selectedVolume.split("_")[3])
    selectedScene = int(selectedVolume.split("_")[1])

    self.surveyTable.SetCellText(selectedScene,selectedModel+1,str(rating))
    self.surveyTable.SetCellText(self.currentSceneIndex,0,str(self.currentSceneIndex))


  def threshold(self, inputVolume, imageThreshold):

    if not inputVolume:
      raise ValueError("Input volume is invalid")

    self.setVolumeRenderingProperty(inputVolume,50,imageThreshold)

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
