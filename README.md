# SegmentationComparison

SegmentationComparison is a Slicer extension that displays volumes in a side-by-side comparison, and allows users to rate the volumes using a built-in survey section. It's intended purpose is to qualitatively compare neural networks, but it can be used for any volumes.

This version of the software was modified to compare AI reconstructions of the spine.

## Information

The following will describe the module and its basic functions.

**Inputs:**
This section is for selecting a folder, and loading volumes from that folder. If the randomize button is checked when loading, it will randomize the order in which the volumes are displayed. Randomizing can reduce bias in the visual evaluarion. 

**Comparison:**
From top to bottom, this section contains:
1. A threshold slider for the currently displayed volumes.
2. A button to reset the camera to its original position. 

**3D View:**
After loading the input folder, the 3D view should display a group of volumes. By default, the camera will be centered on a posterior view of the volume. The name of An orientation marker is shown in the bottom right corner. 

The user can drag the 3D view with left click, and can zoom in or out with the scroll wheel. 

![loadedVolumes](https://github.com/keiranbarr/SegmentationComparison/blob/master/loadedVolumes.PNG)
