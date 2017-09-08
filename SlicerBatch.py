import csv
from collections import OrderedDict
import logging
import os

import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *


#
# SlicerBatch
#

class SlicerBatch(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = 'SlicerBatch'
    self.parent.categories = ['Informatics']
    self.parent.dependencies = []
    self.parent.contributors = ["Joost van Griethuysen (AVL-NKI)"]
    self.parent.helpText = """
    This is a scripted loadable module to process a batch of images for segmentation.
    """
    self.parent.acknowledgementText = ""
#
# SlicerBatchWidget
#

class SlicerBatchWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Setup a logger for the extension log messages
    self.logger = logging.getLogger('slicerBatch')

    # Variables to hold current case and all cases to process
    self.csv_dir = None
    self.cases = None
    self.currentCase = None

    # Instantiate and connect widgets ...

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = 'Parameters'
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # Input CSV Path
    #
    self.inputPathSelector = qt.QLineEdit()
    self.inputPathSelector.toolTip = 'Location of the CSV file containing the cases to process'
    parametersFormLayout.addRow('input CSV path', self.inputPathSelector)

    #
    # Start position
    #
    self.txtStart = qt.QLineEdit()
    self.txtStart.text = 1
    self.txtStart.toolTip = 'Start position in the CSV file (1 = first patient)'
    parametersFormLayout.addRow('start position', self.txtStart)

    #
    # Root Path
    #
    self.rootSelector = qt.QLineEdit()
    self.rootSelector.text = 'path'
    self.rootSelector.toolTip = 'Location of the root directory to load form, or the column name specifying said' \
                                'directory in the input CSV'
    parametersFormLayout.addRow('Root Column', self.rootSelector)

    #
    # Image Path
    #
    self.imageSelector = qt.QLineEdit()
    self.imageSelector.text = 'image'
    self.imageSelector.toolTip = 'Name of the column specifying main image files in input CSV'
    parametersFormLayout.addRow('Image Column', self.imageSelector)

    #
    # Mask Path
    #
    self.maskSelector = qt.QLineEdit()
    self.maskSelector.text = 'mask'
    self.maskSelector.toolTip = 'Name of the column specifying main mask files in input CSV'
    parametersFormLayout.addRow('Mask Column', self.maskSelector)

    #
    # Additional images
    #
    self.addImsSelector = qt.QLineEdit()
    self.addImsSelector.text = ''
    self.addImsSelector.toolTip = 'Comma separated names of the columns specifying additional image files in input CSV'
    parametersFormLayout.addRow('Additional images Column', self.addImsSelector)

    #
    # Additional masks
    #
    self.addMasksSelector = qt.QLineEdit()
    self.addMasksSelector.text = ''
    self.addMasksSelector.toolTip = 'Comma separated names of the columns specifying additional mask files in input CSV'
    parametersFormLayout.addRow('Additional masks Column', self.addMasksSelector)

    #
    # Save masks
    #
    self.chkSaveMasks = qt.QCheckBox()
    self.chkSaveMasks.checked = 1
    self.chkSaveMasks.toolTip = 'save all masks when proceeding to next case'
    parametersFormLayout.addRow('Save masks', self.chkSaveMasks)

    #
    # Load CSV / Next Case
    #
    self.btnNext = qt.QPushButton('Load CSV')
    self.btnNext.enabled = True
    self.layout.addWidget(self.btnNext)

    #
    # Reset
    #
    self.btnReset = qt.QPushButton('Reset')
    self.btnReset.enabled = False
    self.layout.addWidget(self.btnReset)

    self.btnNext.connect('clicked(bool)', self.onNext)
    self.btnReset.connect('clicked(bool)', self.onReset)

    self._setGUIstate(csv_loaded=False)

  def cleanup(self):
    if self.cases is not None:
      try:
        self.cases.close()
      except GeneratorExit:
        pass

  def onNext(self):
    if self.currentCase is None:
      print('Loading %s...' % self.inputPathSelector.text)
      try:
        start = int(self.txtStart.text)
      except:
        self.logger.warning('Could not parse start number, starting at 1')
        start = 1
      self.cases = self._loadCases(self.inputPathSelector.text, start=start)
    else:
      self.currentCase.closeCase((self.chkSaveMasks.checked == 1))

    newCase = self._getNextCase()
    if newCase is not None:
      settings = {}
      settings['root'] = self.rootSelector.text
      settings['image'] = self.imageSelector.text
      settings['mask'] = self.maskSelector.text
      settings['addIms'] = str(self.addImsSelector.text).split(',')
      settings['addMas'] = str(self.addMasksSelector.text).split(',')
      settings['csv_dir'] = self.csv_dir

      self.currentCase = SlicerBatchLogic(newCase, **settings)

  def onReset(self):
    try:
      self.cases.close()
    except GeneratorExit:
      pass
    self.cases = None
    self._setGUIstate(csv_loaded=False)

  def _loadCases(self, csv_file, start=1):
    if not os.path.isfile(csv_file):
      self.logger.warning('Your input does not exist. Try again...')
      return

    # Load cases
    cases = []
    try:
      with open(csv_file) as open_csv_file:
        print('Reading File')
        csv_reader = csv.DictReader(open_csv_file)
        for row in csv_reader:
          cases.append(row)
      self._setGUIstate()
      self.csv_dir = os.path.dirname(csv_file)
      self.logger.info('file loaded, %d cases' % len(cases))
    except:
      self.logger.error('DOH!! something went wrong!', exc_info=True)

    # Return generator to iterate over all cases
    if len(cases) < start:
      self.logger.warning('No cases to process (%d cases, start %d)', len(cases), start)
    for case in cases[start - 1:]:
      self.logger.debug('yielding next case %s' % case)
      yield case

  def _setGUIstate(self, csv_loaded=True):
    if csv_loaded:
      self.btnNext.text = 'Next case'
    else:
      self.btnNext.text = 'Load CSV'
    self.btnReset.enabled = csv_loaded
    self.inputPathSelector.enabled = not csv_loaded
    self.txtStart.enabled = not csv_loaded
    self.rootSelector.enabled = not csv_loaded
    self.imageSelector.enabled = not csv_loaded
    self.maskSelector.enabled = not csv_loaded
    self.addImsSelector.enabled = not csv_loaded
    self.addMasksSelector.enabled = not csv_loaded

    self.currentCase = None

  def _getNextCase(self):
    if self.cases is None:
      return
    try:
      return self.cases.next()
    except StopIteration:
      self._setGUIstate(csv_loaded=False)
      return None

#
# SlicerBatchLogic
#

class SlicerBatchLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, newCase, **kwargs):
    self.logger = logging.getLogger('slicerbatch')

    self.case = newCase

    root = kwargs.get('root', None)
    csv_dir = kwargs.get('csv_dir', None)
    self.root = None
    if root is not None:  # Root is specified as a directory
      if os.path.isdir(root):
        self.root = root
      elif root in self.case:  # Root points to a column in csv file
        if os.path.isabs(self.case.root):  # Absolute path, use as it is
          self.root = self.case[root]
        elif csv_dir is not None:  # If it is a relative path, assume it is relative to the csv file location
          self.root = os.path.join(csv_dir, self.case[root])

        if not os.path.isdir(self.root):
          self.root = None

    self.addIms = kwargs.get('addIms', [])
    self.addMas = kwargs.get('addMas', [])
    self.image = kwargs.get('image', None)
    self.mask = kwargs.get('mask', None)

    self.GenerateMasks = kwargs.get('GenerateMasks', True)
    self.GenerateAddMasks = kwargs.get('GenerateAddMasks', True)

    self.image_nodes = OrderedDict()
    self.mask_nodes = OrderedDict()

    if self._loadImages():

      slicer.util.selectModule('Editor')

    self.logger.debug('Case initialized (settings: %s)' % kwargs)

  def _loadImages(self):
    if self.root is None:
      self.logger.error('Missing root path, cannot load case!')
      return False

    if self.image is not None:
      self.addIms.insert(0, self.image)
    if self.mask is not None:
      self.addMas.insert(0, self.mask)

    for im in self.addIms:
      if im == '':
        continue
      if im not in self.case:
        self.logger.warning('%s not found in this case, skipping...', im)
        continue
      if self.case[im] == '':
        continue
      filepath = os.path.join(self.root, self.case[im])
      if not os.path.isfile(filepath):
        self.logger.warning('image file for %s does not exist, skipping...', im)
      if not slicer.util.loadVolume(filepath):
        self.logger.warning('Failed to load ' + filepath)
      im_node = slicer.util.getNode(os.path.splitext(os.path.basename(filepath))[0])
      if im_node is not None:
        self.image_nodes[im] = im_node
    for ma in self.addMas:
      if ma == '':
        continue
      if ma not in self.case:
        self.logger.warning('%s not found in this case, skipping...', ma)
        continue
      if self.case[ma] == '':
        continue
      filepath = os.path.join(self.root, self.case[ma])
      if not os.path.isfile(filepath):
        self.logger.warning('image file for %s does not exist, skipping...', ma)
      if not slicer.util.loadLabelVolume(filepath):
        self.logger.warning('Failed to load ' + filepath)
      ma_node = slicer.util.getNode(os.path.splitext(os.path.basename(filepath))[0])
      if ma_node is not None:
        self.image_nodes[ma] = ma_node

    if len(self.image_nodes) > 0:
      self._rotateToVolumePlanes(self.image_nodes.values()[0])

    return True

  def closeCase(self, save_nodes=False):
    if save_nodes:
      self._saveNodes()
    slicer.mrmlScene.Clear(0)
    node = slicer.vtkMRMLViewNode()
    slicer.mrmlScene.AddNode(node)
    self.logger.info('case closed')

  def _rotateToVolumePlanes(self, referenceVolume):
    sliceNodes = slicer.util.getNodes('vtkMRMLSliceNode*')
    for name, node in sliceNodes.items():
      node.RotateToVolumePlane(referenceVolume)
    # snap to IJK to try and avoid rounding errors
    sliceLogics = slicer.app.layoutManager().mrmlSliceLogics()
    numLogics = sliceLogics.GetNumberOfItems()
    for n in range(numLogics):
      l = sliceLogics.GetItemAsObject(n)
      l.SnapSliceOffsetToIJK()

  def _saveNodes(self):
    if self.root is None:
      return
    self.logger.info('Saving Masks...')
    nodes = self.mask_nodes.values()

    node_names = [n.GetName() for n in nodes]
    new_nodes = slicer.util.getNodes('*-label*')

    for node in nodes:
      slicer.util.saveNode(node, os.path.join(self.root, node.GetName() + '.nrrd'))
      self.logger.info('Saved node %s in %s', node.GetName(), os.path.join(self.root, node.GetName()))

    for nodename, node in new_nodes.iteritems():
      if nodename in node_names:
        continue  # already saved, go to next
      slicer.util.saveNode(node, os.path.join(self.root, nodename + '.nrrd'))
      self.logger.info('Saved node %s in %s', nodename, os.path.join(self.root, nodename))

