# SegmentationComparison

SegmentationComparison is a Slicer extension that displays volumes in a side-by-side comparison, and allows users to rate the volumes using a built-in survey section. It's intended purpose is to qualitatively compare neural networks, but it can be used for any volumes. 

## Information for survey-takers

The following will describe the module and its basic functions.

**Inputs:**
This section is for selecting a folder, and loading volumes from that folder. If the randomize button is checked when loading, it will randomize the order in which the volumes are displayed. This is preferable for survey-taking, as it can reduce bias. 

**Comparison:**
From top to bottom, this section contains:
1. A threshold slider for the currently displayed volumes.
2. A button to reset the camera to its original position. 

3. The survey itself, which supports ranking the left and right side on a scale of 1 to 5.

4. Buttons to navigate to the previous or next set of volumes, as well as a progress indicator.

5. A button to save the scene, which contains the final results. 

**3D View:**
After loading the input folder, the 3D view should display a group of volumes. By default, the camera will be centered on a posterior view of the volume. An orientation marker is shown in the bottom right corner, and if the transforms are correct, it will show the volume's orientation relative to that of a human body. 

The user can drag the 3D view with left click, and can zoom in or out with the scroll wheel. 

![loadedVolumes](E:\Perk\Summer 2021\Extension\SegmentationComparison\loadedVolumes.PNG)

## Information for developers

1. *Volumes must follow the naming scheme "Scene_x_Model_y.nrrd"!*

2. Transforms can be applied by placing them in the input folder before pressing the load button. If a transform is named "DefaultTransform.h5", it will be applied to all volumes in the folder. If it is named "Scene_x_Model_y_Transform.h5", then it will be applied to that specific volume. If it does not follow either naming scheme, it will not be loaded. 

3. A custom survey message can be set by placing a file named "message.txt" in the input folder before pressing the load button. 