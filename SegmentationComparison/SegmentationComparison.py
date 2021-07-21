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
    self.parent.categories = ["Examples"]
    # TODO: add here list of module names that this module requires
    self.parent.dependencies = []
    # TODO: replace with "Firstname Lastname (Organization)"
    self.parent.contributors = ["John Doe (AnyWare Corp.)"]
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#SegmentationComparison">module documentation</a>.
"""
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
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

#
# SegmentationComparisonWidget
#


class SegmentationComparisonWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

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
    self.addObserver(slicer.mrmlScene,
                     slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene,
                     slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).

    # This input selector will be removed soon
    self.ui.inputSelector.connect(
        "currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)

    self.ui.imageThresholdSliderWidget.connect(
        "valueChanged(double)", self.updateParameterNodeFromGUI)

    self.ui.imageThresholdSliderWidget.connect(
        "valueChanged(double)", self.autoUpdateThresholdSlider)
        
    self.ui.directorySelector.connect(
        "directoryChanged(const QString)", self.updateParameterNodeFromGUI)

    # Buttons
    self.ui.loadButton.connect('clicked(bool)', self.onLoadButton)

    self.ui.displayButton.connect('clicked(bool)', self.onDisplayButton)

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()


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


  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(
        self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)


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

    # Select default input nodes if nothing is selected yet to save a few clicks for the user
    if not self._parameterNode.GetNodeReference("InputVolume"):
      firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass(
          "vtkMRMLScalarVolumeNode")
      if firstVolumeNode:
        self._parameterNode.SetNodeReferenceID(
            "InputVolume", firstVolumeNode.GetID())


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
    self.ui.inputSelector.setCurrentNode(
        self._parameterNode.GetNodeReference("InputVolume"))
  
    self.ui.imageThresholdSliderWidget.value = float(
        self._parameterNode.GetParameter("Threshold"))

    self.ui.directorySelector.directory = self._parameterNode.GetParameter("Directory")

    # Update buttons states and tooltips
    if self._parameterNode.GetParameter("Directory"):
      self.ui.loadButton.toolTip = "Load segmentation volumes"
      self.ui.loadButton.enabled = True

      self.ui.displayButton.toolTip = "Group and display the segmentation(s)"
      self.ui.displayButton.enabled = True

    else:
      self.ui.loadButton.toolTip = "Select a directory containing segmentation volumes"
      self.ui.loadButton.enabled = False

      self.ui.displayButton.toolTip = "Add volumes to the scene"
      self.ui.displayButton.enabled = False

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

    self._parameterNode.SetNodeReferenceID(
        "InputVolume", self.ui.inputSelector.currentNodeID)
    
    self._parameterNode.SetParameter("Threshold", str(
        self.ui.imageThresholdSliderWidget.value))

    self._parameterNode.SetParameter("Directory", str(
        self.ui.directorySelector.directory))

    self._parameterNode.EndModify(wasModified)
    

  # Threshold the selected volume
  def autoUpdateThresholdSlider(self):

    try:
      # TODO: replace this with the for models in scene loop in logic.prepareDisplay()
      # Then, I can get rid of the inputselector, as it is chosen automatically
      inputVolume = self.ui.inputSelector.currentNode()

      # prevents invalid volume error when loading the widget
      if inputVolume is not None:
        # create or use output volume
        outputVolume = self.logic.prepareOutputVolume(self.ui.inputSelector.currentNode())

        self.logic.threshold(inputVolume, outputVolume, self.ui.imageThresholdSliderWidget.value, True)

    except Exception as e:
      slicer.util.errorDisplay("Failed to compute results: "+str(e))
      import traceback
      traceback.print_exc()



  def onLoadButton(self):
    confirmation = slicer.util.confirmYesNoDisplay("Loading this folder will clear the scene. Proceed?")

    if confirmation == True: 
      self.logic.loadVolumes(self._parameterNode.GetParameter("Directory"))
      

  def onDisplayButton(self):
    print("display button pressed")
    # Once "next" and "previous" buttons have been implemented,
    # this function will pass the corresponding value into prepareDisplay()
    # in order to change the group of volumes that are displayed
    self.logic.prepareDisplay(0,self.ui.imageThresholdSliderWidget.value)


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
    self.volumesArray = np.zeros((0,0), dtype='object')
    self.thresholdedVolumesArray = np.zeros((0,0), dtype='object')

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    if not parameterNode.GetParameter("Threshold"):
      parameterNode.SetParameter("Threshold", "0")
    '''
    if not parameterNode.GetParameter("Invert"):
      parameterNode.SetParameter("Invert", "false")
    '''


  def loadVolumes(self, directory):
    # TODO: This needs to delete more nodes in order to fully reset after creating the custom view
    slicer.mrmlScene.Clear()

    print("Checking directory: " + directory)
    
    volumesInDirectory = list(f for f in os.listdir(directory) if f.endswith(".nrrd"))
    print("Found volumes: " + str(volumesInDirectory))

    volumeArrayXDim = 0
    volumeArrayYDim = 0

    try:

      # this loop is for determining the dimensions of the array to store the volume references
      for volumeIndex, volumeFile in enumerate(volumesInDirectory):
        print(volumeFile)
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

        slicer.util.loadVolume(directory + "/" + volumeFile)

        self.volumesArray[sceneNumber][modelNumber] = name

      self.thresholdedVolumesArray = self.volumesArray


    except Exception as e:
      slicer.util.errorDisplay("Ensure volumes follow the naming scheme: 'Scene_x_Model_x.nrrd': "+str(e))
      import traceback
      traceback.print_exc()



  def prepareOutputVolume(self, inputVolume):

    # this occurs on initial load of the scene

    outputVolumeName = inputVolume.GetName() + "_thresholded"
    print("Saved threshold output in: " + outputVolumeName)

    outputVolume = slicer.mrmlScene.GetFirstNodeByName(outputVolumeName)

    if outputVolume is None:
      print("Creating thresholded volume")

      outputVolume = slicer.mrmlScene.AddNode(slicer.vtkMRMLScalarVolumeNode())
      outputVolume.CreateDefaultDisplayNodes()

      outputVolume.SetName(outputVolumeName)

    return outputVolume


  def prepareDisplay(self, selectedScene, thresholdValue):
    print("preparing display")

    volumeIndex = 0
    for volume in self.volumesArray[selectedScene]:
      print(volume)
      inputVolume = slicer.util.getFirstNodeByName(volume)
      outputVolume = self.prepareOutputVolume(inputVolume)
      outputVolumeName = outputVolume.GetName()

      print(outputVolumeName)

      self.threshold(inputVolume, outputVolume, thresholdValue, True)

      self.thresholdedVolumesArray[selectedScene][volumeIndex] = outputVolumeName

      volumeIndex += 1

    print(self.thresholdedVolumesArray)

    # Code related to the 3D view is taken from here: https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html

    # this portion of the function is very much WIP
    # it does not yet automatically display the volumes in their corresponding view
    # and it also causes strange errors when loading more files from a directory,
    # because it is not clearing the scene properly

    numberOfColumns = 2

    numberOfVolumes = len(self.volumesArray[selectedScene])

    numberOfRows = int(math.ceil(numberOfVolumes/numberOfColumns))

    customLayoutId=567  # we pick a random id that is not used by others
    slicer.app.setRenderPaused(True)

    customLayout = '<layout type="vertical">'
    viewIndex = 0
    for rowIndex in range(numberOfRows):
      customLayout += '<item><layout type="horizontal">'
      for colIndex in range(numberOfColumns):

        name = self.thresholdedVolumesArray[selectedScene][viewIndex] if viewIndex < numberOfVolumes else "compare " + str(viewIndex)
        customLayout += '<item><view class="vtkMRMLViewNode" singletontag="'+name
        customLayout += '"><property name="viewlabel" action="default">'+name+'</property></view></item>'
        viewIndex += 1
      customLayout += '</layout></item>'
      
    customLayout += '</layout>'
    if not slicer.app.layoutManager().layoutLogic().GetLayoutNode().SetLayoutDescription(customLayoutId, customLayout):
        slicer.app.layoutManager().layoutLogic().GetLayoutNode().AddLayoutDescription(customLayoutId, customLayout)

    slicer.app.layoutManager().setLayout(customLayoutId)

    for volumeIndex, volumeName in enumerate(self.thresholdedVolumesArray[selectedScene]):

      viewNode = slicer.mrmlScene.GetSingletonNode(volumeName, "vtkMRMLViewNode")
      viewNode.LinkedControlOn()

      outputVolume = slicer.util.getFirstNodeByName(volumeName)
      outputVolume.GetDisplayNode().AddViewNodeID(viewNode.GetID())

      # this is not sufficient to actually display the volume
      # i am still looking into this

    slicer.app.setRenderPaused(False)



  def threshold(self, inputVolume, outputVolume, imageThreshold, showResult=True):
    """
    Run the processing algorithm.
    Can be used without GUI widget.
    :param inputVolume: volume to be thresholded
    :param outputVolume: thresholding result
    :param imageThreshold: values above/below this threshold will be set to 0
    :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
    :param showResult: show output volume in slice viewers
    """

    if not inputVolume or not outputVolume:
      raise ValueError("Input or output volume is invalid")

    import time
    startTime = time.time()
    # logging.info('Processing started')

    # Compute the thresholded output volume using the "Threshold Scalar Volume" CLI module
    cliParams = {
      'InputVolume': inputVolume.GetID(),
      'OutputVolume': outputVolume.GetID(),
      'ThresholdValue' : imageThreshold,
      'ThresholdType' : 'Below'
      }
    cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True, update_display=showResult)
    # We don't need the CLI module node anymore, remove it to not clutter the scene with it
    slicer.mrmlScene.RemoveNode(cliNode)

    stopTime = time.time()
    logging.info('Thresholding completed in {0:.2f} seconds'.format(stopTime-startTime))



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
