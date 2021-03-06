import sys
import logging

from PyQt4.QtCore import (QPoint, QRectF, QPointF, Qt, SIGNAL, QTimer, QObject)
from PyQt4.QtGui import (QApplication, QMainWindow, QGraphicsView,
    QGraphicsScene, QImage, QWidget, QHBoxLayout, QPen,
    QVBoxLayout, QPushButton, QGraphicsEllipseItem, QGraphicsItem,
    QPainter, QKeySequence, QAction, QIcon, QFileDialog, QProgressBar,
    QBrush, QFrame, QLabel, QRadioButton, QGridLayout, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QLineEdit, QMessageBox)
import numpy as np

from . import config
from . import __version__
from base import *
from io import *

##H #
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
from matplotlib.figure import Figure
import pickle
from . import my_flatten as flt
#####



logging.basicConfig(filename = config.loggingFilename, level=config.loggingLevel)

class QGraphicsSpotView(QGraphicsEllipseItem):
    """ Provides an QGraphicsItem to display a Spot on a QGraphicsScene.
    
        Circle class providing a circle that can be moved by mouse and keys.
        
    """

    def __init__(self, point, radius, parent=None):
        offset = QPointF(radius, radius)
        super(QGraphicsSpotView, self).__init__(QRectF(-offset, offset),  parent)
        self.setPen(QPen(Qt.blue))
        self.setPos(point)
        self.setFlags(QGraphicsItem.ItemIsSelectable|
                      QGraphicsItem.ItemIsMovable|
                      QGraphicsItem.ItemIsFocusable)

    def keyPressEvent(self, event):
        """ Handles keyPressEvents.

            The circle can be moved using the arrow keys. Applying Shift
            at the same time allows fine adjustments.

            The circles radius can be changed using the plus and minus keys.
        """

        if event.key() == Qt.Key_Plus:
            self.changeSize(config.QGraphicsSpotView_spotSizeChange)
        elif event.key() == Qt.Key_Minus:
            self.changeSize(-config.QGraphicsSpotView_spotSizeChange)
        elif event.key() == Qt.Key_Right:
            if event.modifiers() & Qt.ShiftModifier:
                self.moveRight(config.QGraphicsSpotView_smallMove)
            else:
                self.moveRight(config.QGraphicsSpotView_bigMove)
        elif event.key() == Qt.Key_Left:
            if event.modifiers() & Qt.ShiftModifier:
                self.moveLeft(config.QGraphicsSpotView_smallMove)
            else:
                self.moveLeft(config.QGraphicsSpotView_bigMove)
        elif event.key() == Qt.Key_Up:
            if event.modifiers() & Qt.ShiftModifier:
                self.moveUp(config.QGraphicsSpotView_smallMove)
            else:
                self.moveUp(config.QGraphicsSpotView_bigMove)
        elif event.key() == Qt.Key_Down:
            if event.modifiers() & Qt.ShiftModifier:
                self.moveDown(config.QGraphicsSpotView_smallMove)
            else:
                self.moveDown(config.QGraphicsSpotView_bigMove)

    def onPositionChange(self, point):
        """ Handles incoming position change request."""
        self.setPos(point)

    def radius(self):
        return self.rect().width() / 2.0

    def onRadiusChange(self, radius):
        """ Handles incoming radius change request."""
        self.changeSize(radius - self.radius())

    def moveRight(self, distance):
        """ Moves the circle distance to the right."""
        self.setPos(self.pos() + QPointF(distance, 0.0))

    def moveLeft(self, distance):
        """ Moves the circle distance to the left."""
        self.setPos(self.pos() + QPointF(-distance, 0.0))

    def moveUp(self, distance):
        """ Moves the circle distance up."""
        self.setPos(self.pos() + QPointF(0.0, -distance))

    def moveDown(self, distance):
        """ Moves the circle distance down."""
        self.setPos(self.pos() + QPointF(0.0, distance))

    def changeSize(self, inc):
        """ Change radius by inc.
        
            inc > 0: increase
            inc < 0: decrease
        """

        inc /= 2**0.5 
        self.setRect(self.rect().adjusted(-inc, -inc, +inc, +inc))

class QSpotModel(QObject):
    """
    Wraps a SpotModel to offer signals.

    Provides the following signals:
    - intensityChanged
    - positionChanged
    - radiusChanged
    """

    def __init__(self, parent = None):
        super(QSpotModel, self).__init__(parent)
        self.m = SpotModel()
    
    def update(self, x, y, intensity, energy, radius):
        self.m.update(x, y, intensity, energy, radius)
        QObject.emit(self, SIGNAL("positionChanged"), QPointF(x, y))
        QObject.emit(self, SIGNAL("radiusChanged"), radius)
        QObject.emit(self, SIGNAL("intensityChanged"), intensity)

class GraphicsScene(QGraphicsScene):
    """ Custom GraphicScene having all the main content."""

    def __init__(self, parent=None):
        super(GraphicsScene, self).__init__(parent)
    
    def mousePressEvent(self, event):
        """ Processes mouse events through either            
              - propagating the event
            or 
              - instantiating a new Circle (on left-click)
        """
       
        if self.itemAt(event.scenePos()):
            super(GraphicsScene, self).mousePressEvent(event)
        elif event.button() == Qt.LeftButton:
            item = QGraphicsSpotView(event.scenePos(),
                         config.GraphicsScene_defaultRadius)
            self.clearSelection()
            self.addItem(item)
            item.setSelected(True)
            self.setFocusItem(item)

    def keyPressEvent(self, event):
        """ Processes key events through either            
              - deleting the focus item
            or   
              - propagating the event

        """

        item = self.focusItem()
        if item:
            if event.key() == Qt.Key_Delete:
                self.removeItem(item)
                del item
            else:
                super(GraphicsScene, self).keyPressEvent(event)

    def drawBackground(self, painter, rect):
        """ Draws image in background if it exists. """
        if hasattr(self, "image"):
            painter.drawImage(QPoint(0, 0), self.image)

    def setBackground(self, image):
        """ Sets the background image. """
        self.image = image
        self.update()
    
    def removeAll(self):
        """ Remove all items from the scene (leaves background unchanged). """
        for item in self.items():
            self.removeItem(item)

class GraphicsView(QGraphicsView):
    """ Custom GraphicsView to display the scene. """
    def __init__(self, parent=None):
        super(GraphicsView, self).__init__(parent)
        self.setRenderHints(QPainter.Antialiasing)
    
#    def wheelEvent(self, event):
#        factor = 1.41 ** (-event.delta() / 240.0)
#        self.scale(factor, factor)
    
    def resizeEvent(self, event):
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
    
    def drawBackground(self, painter, rect):
        painter.fillRect(rect, QBrush(Qt.lightGray))
        self.scene().drawBackground(painter, rect)

class FileDialog(QFileDialog):
    def __init__(self, **kwargs):
        super(FileDialog, self).__init__(**kwargs)
        self.setFileMode(QFileDialog.ExistingFiles)


############## H ###########

class PlotOptionWidget(QWidget):
    '''PyQt widget for selecting plotting options'''

    def __init__(self):
        super(PlotOptionWidget, self).__init__()
        
        self.initUI()
        
    def initUI(self):
        
        self.setGeometry(300, 300, 300, 150)
        self.setWindowTitle('Select plotting method')
        self.gridLayout = QGridLayout()
        self.setLayout(self.gridLayout)
        self.rbutton1 = QRadioButton('Plot &intensities', self)
        self.rbutton2 = QRadioButton('Plot a&verage', self)
        self.rbutton3 = QRadioButton('&Plot intensities && average', self)
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.addWidget(self.rbutton1)
        self.verticalLayout.addWidget(self.rbutton2)
        self.verticalLayout.addWidget(self.rbutton3)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.label = QLabel("", self)	
        self.verticalLayout.addWidget(self.label)
        self.hLayout = QHBoxLayout()
        self.pbutton1 = QPushButton('&Accept', self)
        self.pbutton2 = QPushButton('&Cancel', self)
        self.hLayout.addWidget(self.pbutton1)
        self.hLayout.addWidget(self.pbutton2)
        self.gridLayout.addLayout(self.hLayout, 1, 0, 1, 1)

class Plot(QWidget):
    '''Custom PyQt widget canvas for plotting'''

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setWindowTitle("I(E)-curve")

        self.create_main_frame()
    
    def create_main_frame(self):       
        # Create the mpl Figure and FigCanvas objects. 
        # 5x4 inches, 100 dots-per-inch
        self.dpi = 100
        self.fig = Figure((5.0, 4.0), dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        
        # Since we have only one plot, we can use add_axes 
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.
        self.axes = self.fig.add_subplot(111)
        
        # Create the navigation toolbar, tied to the canvas
        #self.mpl_toolbar = NavigationToolbar(self.canvas, self)

        # Layout
        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)
        #vbox.addWidget(self.mpl_toolbar)
        
        self.setLayout(vbox)

class SetParameters(QWidget): 
    '''PyQt widget for setting tracking parameters'''
 
    
    def __init__(self):
        super(SetParameters, self).__init__()
        
        self.initUI()
        
    def initUI(self):
        
        # Buttons/elements
        self.inputPrecision = QSpinBox(self)
        self.inputPrecision.setWrapping(True)
        self.inputPrecision.setValue(config.Tracking_inputPrecision)
        self.ipLabel = QLabel("User input precision", self)

        self.integrationWindowRadius = QSpinBox(self)
        self.integrationWindowRadius.setWrapping(True)
        self.integrationWindowRadius.setValue(config.Tracking_minWindowSize)
        self.iwrLabel = QLabel("Minimun radius of the integration window", self)

        self.validationRegionSize = QSpinBox(self)
        self.validationRegionSize.setWrapping(True)
        self.validationRegionSize.setValue(config.Tracking_gamma)
        self.vrsLabel = QLabel("Size of the validation region", self)

        self.determinationCoefficient = QDoubleSpinBox(self)
        self.determinationCoefficient.setWrapping(True)
        self.determinationCoefficient.setSingleStep(0.01)
        self.determinationCoefficient.setValue(config.Tracking_minRsq)
        self.dcLabel = QLabel("Minimal coefficient of determinating R^2 for fit", self)

        self.integrationWindowScale = QCheckBox("Scale integration window with changing energy")
        self.integrationWindowScale.setChecked(config.Tracking_windowScalingOn)

        self.backgroundSubstraction = QCheckBox("Background substraction")
        self.backgroundSubstraction.setChecked(config.Processing_backgroundSubstractionOn)

        self.spotIdentification = QComboBox(self)
        self.spotIdentification.addItem("guess_from_Gaussian")
        self.siLabel = QLabel("Spot indentification algorithm", self)


        self.fnLabel = QLabel("Kalman tracker process noise", self)
        self.text = QLabel("Set the diagonal values for 4x4 matrix:", self)
        self.value1 = QLineEdit(self)
        self.value1.setText(str(config.Tracking_processNoise.diagonal()[0]))
        self.value2 = QLineEdit(self)
        self.value2.setText(str(config.Tracking_processNoise.diagonal()[1]))
        self.value3 = QLineEdit(self)
        self.value3.setText(str(config.Tracking_processNoise.diagonal()[2]))
        self.value4 = QLineEdit(self)
        self.value4.setText(str(config.Tracking_processNoise.diagonal()[3]))


        self.saveButton = QPushButton('&Save', self)
        self.loadButton = QPushButton('&Load', self)
        self.defaultButton = QPushButton('&Default', self)
        self.wrongLabel = QLabel(" ", self)
        self.acceptButton = QPushButton('&Accept', self)
        self.cancelButton = QPushButton('&Cancel', self)

        #Layouts
        self.setGeometry(300, 300, 300, 150)
        self.setWindowTitle('Set tracking parameters')
     
        #base grid
        self.gridLayout = QGridLayout()
        self.setLayout(self.gridLayout)

        #1st (left) vertical layout
        #adding items
        self.lvLayout = QVBoxLayout()
        self.lvLayout.addWidget(self.ipLabel)
        self.lvLayout.addWidget(self.inputPrecision)
        self.lvLayout.addWidget(self.iwrLabel)
        self.lvLayout.addWidget(self.integrationWindowRadius)
        self.lvLayout.addWidget(self.vrsLabel)
        self.lvLayout.addWidget(self.validationRegionSize)
        self.lvLayout.addWidget(self.dcLabel)
        self.lvLayout.addWidget(self.determinationCoefficient)

        #2nd (right) vertical layout
        #adding items
        self.rvLayout = QVBoxLayout()
        self.rvLayout.addWidget(self.integrationWindowScale)
        self.rvLayout.addWidget(self.backgroundSubstraction)
        self.rvLayout.addWidget(self.siLabel)
        self.rvLayout.addWidget(self.spotIdentification)

        #3rd (process noise) vertical layout
        self.vpLayout = QVBoxLayout()
        self.hpLayout = QHBoxLayout()
        self.vpLayout.addWidget(self.fnLabel)
        self.vpLayout.addWidget(self.text)
        self.hpLayout.addWidget(self.value1)
        self.hpLayout.addWidget(self.value2)
        self.hpLayout.addWidget(self.value3)
        self.hpLayout.addWidget(self.value4)

        #horizontal layout
        #adding items
        self.hLayout = QHBoxLayout()
        self.hLayout.addWidget(self.saveButton)
        self.hLayout.addWidget(self.loadButton)
        self.hLayout.addWidget(self.defaultButton)
        self.hLayout.addWidget(self.wrongLabel)
        self.hLayout.addWidget(self.acceptButton)
        self.hLayout.addWidget(self.cancelButton)

        #adding layouts to the grid
        self.gridLayout.addLayout(self.lvLayout, 0, 0)
        self.gridLayout.addLayout(self.rvLayout, 0, 1)
        self.gridLayout.addLayout(self.vpLayout, 4, 0)
        self.gridLayout.addLayout(self.hpLayout, 4, 1)
        self.gridLayout.addLayout(self.hLayout, 5, 1)

        # apologies for horrific use of PyQt. I'll go back to text based. /Hanna #

##############

class MainWindow(QMainWindow):
    """ easyLeed's main window. """
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("easyLeed %s" % __version__)

        #### setup central widget ####
        self.plotoptionwid = PlotOptionWidget()
        self.plotwid = Plot()
        self.setparameterswid = SetParameters()
        self.scene = GraphicsScene(self)
        self.view = GraphicsView()
        self.view.setScene(self.scene)
        self.view.setMinimumSize(640, 480)
        self.setCentralWidget(self.view)
        
        #### define actions ####
        processRunAction = self.createAction("&Run", self.run,
                QKeySequence("Ctrl+r"), None,
                "Run the analysis of the images.")
        processRestartAction = self.createAction("&Restart", self.restart,
                QKeySequence("Ctrl+z"), None,
                "Reset chosen points and jump to first image.")
        processNextAction = self.createAction("&Next Image", self.next_,
                QKeySequence("Ctrl+n"), None,
                "Open next image.")
        processPreviousAction = self.createAction("&Previous Image", self.previous,
                QKeySequence("Ctrl+p"), None,
                "Open previous image.")
                
## H #
        # actions to "Process" menu
        processPlotAction = self.createAction("&Plot", self.plotting, QKeySequence("Ctrl+d"), None, "Plot the energy/intensity.")
        processPlotAverageAction = self.createAction("&Plot average", self.plottingAverage, QKeySequence("Ctrl+g"), None, "Plot the energy/intensity average.")
        #needs still work
        #processSpotsAction = self.createAction("&Process Spots", self.processSpots, QKeySequence("Ctrl+"), None, "Process spots.")
        processPlotOptions = self.createAction("&Plot...", self.plottingOptions, None, None, "Choose plotting method.")
        processSetParameters = self.createAction("&Set Parameters", self.setParameters, None, None, "Set tracking parameters.")

######

        self.processActions = [processNextAction, processPreviousAction, None, processRunAction, processRestartAction, None, processPlotAction, None, processPlotAverageAction, None, processSetParameters]
        fileOpenAction = self.createAction("&Open...", self.fileOpen,
                QKeySequence.Open, None,
                "Open a directory containing the image files.")
        self.fileSaveAction = self.createAction("&Save intensities...", self.saveIntensity,
                QKeySequence.Save, None,
                "Save the calculated intensities to a text file.")
                
## H #
        # actions to "File" menu
        self.fileSavePlotAction = self.createAction("&Save plot...", self.savePlot, QKeySequence("Ctrl+a"), None, "Save the plot to a pdf file.")
        # Will only enable plot saving after there is a plot to be saved
        self.fileSavePlotAction.setEnabled(False)
        self.fileQuitAction = self.createAction("&Quit", self.fileQuit, QKeySequence("Ctrl+q"), None, "Close the application.")
        self.fileSaveSpotsAction = self.createAction("&Save spot locations...", self.saveSpots, QKeySequence("Ctrl+t"), None, "Save the spots to a file.")
        # Enables when data to be saved
        self.fileSaveSpotsAction.setEnabled(False)
        self.fileLoadSpotsAction = self.createAction("&Load spot locations...", self.loadSpots, QKeySequence("Ctrl+l"), None, "Load spots from a file.")
######
        self.helpAction = self.createAction("&Help", self.helpBoxShow, None, None, "Show help")
        self.aboutAction = self.createAction("&About", self.aboutBoxShow, None, None, "About Easyleed")
        self.helpActions = [None, self.helpAction, None, self.aboutAction]
                
        
        self.fileActions = [fileOpenAction, self.fileSaveAction, self.fileSavePlotAction, self.fileSaveSpotsAction, self.fileLoadSpotsAction, None, self.fileQuitAction]

        #### Create menu bar ####
        fileMenu = self.menuBar().addMenu("&File")
        self.fileSaveAction.setEnabled(False)
        self.addActions(fileMenu, self.fileActions)
        processMenu = self.menuBar().addMenu("&Process")
        self.addActions(processMenu, self.processActions)
        self.enableProcessActions(False)
        helpMenu = self.menuBar().addMenu("&Help")
        self.addActions(helpMenu, self.helpActions)

        #### Create tool bar ####
        toolBar = self.addToolBar("&Toolbar")
        # adding actions to the toolbar, addActions-function creates a separator with "None"
        self.toolBarActions = [self.fileQuitAction, None, fileOpenAction, None, processRunAction, None, processPreviousAction, None, processNextAction, None, processPlotOptions, None, processSetParameters, None, None, processRestartAction]
        self.addActions(toolBar, self.toolBarActions)

        #### Create status bar ####
        self.statusBar().showMessage("Ready", 5000)
        self.energyLabel = QLabel()
        self.energyLabel.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.statusBar().addPermanentWidget(self.energyLabel)
  
    def addActions(self, target, actions):
        """
        Convenience function that adds the actions to the target.
        If an action is None a separator will be added.
        
        """
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)
    
    def createAction(self, text, slot=None, shortcut=None, icon=None,
                     tip=None, checkable=False, signal="triggered()"):
        """ Convenience function that creates an action with the specified attributes. """
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/{0}.png".format(icon)))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            self.connect(action, SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action

    def enableProcessActions(self, enable):
        for action in self.processActions:
            if action:
                action.setEnabled(enable)

    def next_(self):
        try:
            image = self.loader.next()
        except StopIteration:
            self.statusBar().showMessage("Reached last picture", 5000)
        else:
            self.setImage(image)

    def previous(self):
        try:
            image = self.loader.previous()
        except StopIteration:
            self.statusBar().showMessage("Reached first picture", 5000)
        else:
            self.setImage(image)

    def restart(self):
        '''Delete stored plot information and start fresh'''
        self.scene.removeAll()
        self.loader.restart()
        self.setImage(self.loader.next())
        self.plotwid.axes.cla()
        self.plotwid.canvas.draw()
        self.plotwid.close()

    def setImage(self, image):
        npimage, energy = image
        qimage = npimage2qimage(npimage)
        self.view.setSceneRect(QRectF(qimage.rect()))
        self.scene.setBackground(qimage)
        self.current_energy = energy
        self.energyLabel.setText("Energy %s eV" % self.current_energy)

    def saveIntensity(self):
        filename = str(QFileDialog.getSaveFileName(self, "Save intensities to a file"))
        if filename:
            self.worker.save(filename)

    def fileOpen(self):
        """ Prompts the user to select input image files."""
        self.scene.removeAll()
        dialog = FileDialog(parent = self,
                caption = "Choose image files", filter= ";;".join(IMAGE_FORMATS))
        if dialog.exec_():
            files = dialog.selectedFiles();
            filetype = IMAGE_FORMATS[str(dialog.selectedNameFilter())]
            files = [str(file_) for file_ in files]
            try:
                self.loader = filetype.loader(files, config.IO_energyRegex)
                self.setImage(self.loader.next())
                self.enableProcessActions(True)
            except IOError, err:
                self.statusBar().showMessage('IOError: ' + str(err), 5000)
            
    def stopProcessing(self):
        self.stopped = True

    def run(self):
        import time
        time_before = time.time()
        
        self.stopped = False
        progress = QProgressBar()
        stop = QPushButton("Stop", self)
        self.connect(stop, SIGNAL("clicked()"), self.stopProcessing)
        progress.setMinimum(int(self.loader.current_energy()))
        progress.setMaximum(int(self.loader.energies[-1]))
        statusLayout = QHBoxLayout()
        statusLayout.addWidget(progress)
        statusLayout.addWidget(stop)
        statusWidget = QWidget(self)
        statusWidget.setLayout(statusLayout)
        self.statusBar().addWidget(statusWidget)
        self.view.setInteractive(False)
        self.scene.clearSelection()
        self.worker = Worker(self.scene.items(), self.current_energy, parent=self)
        self.fileSaveAction.setEnabled(True)
        self.fileSaveSpotsAction.setEnabled(True)
        for image in self.loader:
            if self.stopped:
                break
            progress.setValue(int(image[1]))
            QApplication.processEvents()
            self.setImage(image)
            self.worker.process(image)
            QApplication.processEvents()
        self.view.setInteractive(True)
        self.statusBar().removeWidget(statusWidget)

        print time.time() - time_before

    def disableInput(self):
        for item in self.scene.items():
            item.setFlag(QGraphicsItem.ItemIsSelectable, False)
            item.setFlag(QGraphicsItem.ItemIsFocusable, False)
            item.setFlag(QGraphicsItem.ItemIsMovable, False)

    def helpBoxShow(self):
       helpFile = open("../doc/source/uiuserguide.txt", 'r')
       filedata = helpFile.read()
       self.textBox = QMessageBox.information(self, "Help", filedata, QMessageBox.Ok)

    def aboutBoxShow(self):
       aboutFile = open("../doc/source/uiabout.txt", 'r')
       filedata = aboutFile.read()
       self.textBox = QMessageBox.information(self, "About", filedata, QMessageBox.Ok)

##H #
	## Plotting with matplotlib ##

    def plotting(self):
        '''Basic Matplotlib plotting I(E)-curve'''
        # do only if there's some data to draw the plot from, otherwise show an error message in the statusbar
        try:
            # getting intensities and energy from the worker class
            intensities = [model.m.intensity for model, tracker \
                                in self.worker.spots_map.itervalues()]
            energy = [model.m.energy for model, tracker in self.worker.spots_map.itervalues()]
            # setting the axe labels
            self.plotwid.axes.set_xlabel("Energy [eV]")
            self.plotwid.axes.set_ylabel("Intensity")
            self.plotwid.axes.set_title("I(E)-curve")
            # removes the ticks from y-axis
            self.plotwid.axes.set_yticks([])

            # do the plot
            for x in energy:
                for y in intensities:
                    self.plotwid.axes.plot(x, y)
            # and show it
            self.plotwid.canvas.draw()
            self.plotwid.show()
            # can save the plot now
            self.fileSavePlotAction.setEnabled(True)
        except AttributeError:
            self.statusBar().showMessage("No plottable data.", 5000)

    def plottingAverage(self):
        '''Mostly the same as normal plotting but plots the average of the calculated intensities '''
        try:
            sum_intensity=0
            list_of_average_intensities = []
            intensities = [model.m.intensity for model, tracker \
                                in self.worker.spots_map.itervalues()]
            number_of_pictures = len(intensities[0])
            number_of_points = len(intensities)
            energy = [model.m.energy for model, tracker in self.worker.spots_map.itervalues()]
            intensities = flt.flatten(intensities)
            for i in range(number_of_pictures):
                for j in range(i, len(intensities), number_of_pictures):
                    sum_intensity = sum_intensity + intensities[j]
                average_intensity = sum_intensity/number_of_points
                list_of_average_intensities.append(average_intensity)
                sum_intensity = 0
            # setting the axe labels
            self.plotwid.axes.set_xlabel("Energy [eV]")
            self.plotwid.axes.set_ylabel("Intensity")
            self.plotwid.axes.set_title("I(E)-curve")
            # removes the ticks from y-axis
            self.plotwid.axes.set_yticks([])
            self.plotwid.axes.plot(energy[0], list_of_average_intensities,'k-', linewidth=3, label = 'Average')
            self.plotwid.canvas.draw()
            self.plotwid.show()
            self.fileSavePlotAction.setEnabled(True)
        except AttributeError:
            self.statusBar().showMessage("No plottable data.", 5000)

    def plottingOptions(self):

        QObject.connect(self.plotoptionwid.pbutton1, SIGNAL("clicked()"), self.PlotWidgetAccept)
        QObject.connect(self.plotoptionwid.pbutton2, SIGNAL("clicked()"), self.plotoptionwid.close)

        self.plotoptionwid.show()

    def PlotWidgetAccept(self):        
        if self.plotoptionwid.rbutton1.isChecked():
            self.plotwid.axes.cla()
            self.plotting()
            self.plotoptionwid.close()
        elif self.plotoptionwid.rbutton2.isChecked():
            self.plotwid.axes.cla()
            self.plottingAverage()
            self.plotoptionwid.close()
        elif self.plotoptionwid.rbutton3.isChecked():
            self.plotwid.axes.cla()
            self.plotting()
            self.plottingAverage()
            self.plotoptionwid.close()
        else:
            self.plotoptionwid.label.setText('Check a mode')

    def setParameters(self):

        QObject.connect(self.setparameterswid.acceptButton, SIGNAL("clicked()"), self.acceptParameters)
        QObject.connect(self.setparameterswid.cancelButton, SIGNAL("clicked()"), self.setparameterswid.close)
        QObject.connect(self.setparameterswid.defaultButton, SIGNAL("clicked()"), self.defaultValues)
        QObject.connect(self.setparameterswid.saveButton, SIGNAL("clicked()"), self.saveValues)
        QObject.connect(self.setparameterswid.loadButton, SIGNAL("clicked()"), self.loadValues)

        self.setparameterswid.show()

    #Set user values to the parameters
    def acceptParameters(self):
        '''Parameter setting control'''
        config.Tracking_inputPrecision = self.setparameterswid.inputPrecision.value()
        config.Tracking_windowScalingOn = self.setparameterswid.integrationWindowScale.isChecked()
        config.Tracking_minWindowSize = self.setparameterswid.integrationWindowRadius.value()
        config.Tracking_guessFunc = self.setparameterswid.spotIdentification.currentText()
        config.Tracking_gamma = self.setparameterswid.validationRegionSize.value()
        config.Tracking_minRsq = self.setparameterswid.determinationCoefficient.value()
        config.Processing_backgroundSubstractionOn = self.setparameterswid.backgroundSubstraction.isChecked()
        try:
            self.noiseList = [float(self.setparameterswid.value1.text()), float(self.setparameterswid.value2.text()), float(self.setparameterswid.value3.text()), float(self.setparameterswid.value4.text())]
            config.Tracking_processNoise = np.diag(self.noiseList)
            self.setparameterswid.close()
        except ValueError:
            self.setparameterswid.setText.wrongLabel("Invalid process noise value")

    #Reload config-module and get the default values
    def defaultValues(self):
        '''Loading deault parameter valued from config file'''
        reload(config)
        self.setparameterswid.inputPrecision.setValue(config.Tracking_inputPrecision)
        self.setparameterswid.integrationWindowRadius.setValue(config.Tracking_minWindowSize)
        self.setparameterswid.validationRegionSize.setValue(config.Tracking_gamma)
        self.setparameterswid.determinationCoefficient.setValue(config.Tracking_minRsq)
        self.setparameterswid.integrationWindowScale.setChecked(config.Tracking_windowScalingOn)
        self.setparameterswid.backgroundSubstraction.setChecked(config.Processing_backgroundSubstractionOn)
        self.setparameterswid.value1.setText(str(config.Tracking_processNoise.diagonal()[0]))
        self.setparameterswid.value2.setText(str(config.Tracking_processNoise.diagonal()[1]))
        self.setparameterswid.value3.setText(str(config.Tracking_processNoise.diagonal()[2]))
        self.setparameterswid.value4.setText(str(config.Tracking_processNoise.diagonal()[3]))

    #Save given user values to a file
    def saveValues(self):
        '''Basic saving of the set parameter values to a file '''
        filename = str(QFileDialog.getSaveFileName(self, "Save the parameter configuration to a file"))
        if filename:
            output = open(filename, 'w')
            backgroundsublist = [float(self.setparameterswid.value1.text()), float(self.setparameterswid.value2.text()), float(self.setparameterswid.value3.text()), float(self.setparameterswid.value4.text())]
            writelist = [self.setparameterswid.inputPrecision.value(), self.setparameterswid.integrationWindowScale.isChecked(), self.setparameterswid.integrationWindowRadius.value(), self.setparameterswid.spotIdentification.currentText(), self.setparameterswid.validationRegionSize.value(), self.setparameterswid.determinationCoefficient.value(), self.setparameterswid.backgroundSubstraction.isChecked(), backgroundsublist]
            pickle.dump(writelist, output)

    #Load user values from a file to the widget
    def loadValues(self):
        '''Load a file of set parameter values that has been saved with the widget'''
        namefile = str(QFileDialog.getOpenFileName(self, 'Open spot location file'))
        try:
            loadput = open(namefile, 'r')
            loadlist = pickle.load(loadput)
            self.setparameterswid.inputPrecision.setValue(loadlist[0])
            self.setparameterswid.integrationWindowScale.setChecked(loadlist[1])
            self.setparameterswid.integrationWindowRadius.setValue(loadlist[2])
            self.setparameterswid.spotIdentification.setCurrentIndex(self.setparameterswid.spotIdentification.findText(loadlist[3]))
            self.setparameterswid.validationRegionSize.setValue(loadlist[4])
            self.setparameterswid.determinationCoefficient.setValue(loadlist[5])
            self.setparameterswid.backgroundSubstraction.setChecked(loadlist[6])
            self.setparameterswid.value1.setText(str(loadlist[7][0]))
            self.setparameterswid.value2.setText(str(loadlist[7][1]))
            self.setparameterswid.value3.setText(str(loadlist[7][2]))
            self.setparameterswid.value4.setText(str(loadlist[7][3]))
        except:
            print "Invalid file"
       
#           
#
#
	
	## Saving the plot

    def savePlot(self):
        # savefile prompt
	    filename = str(QFileDialog.getSaveFileName(self, "Save the plot to a file"))
	    if filename:
            # matplotlib.pyplot save-function, saves as pdf
		    self.plotwid.canvas.print_figure(filename, format="pdf")

    ## Quitting the application
    # special quit-function as the normal window closing might leave something on the background
    def fileQuit(self):
        '''Special quit-function as the normal window closing might leave something on the background '''
        QApplication.closeAllWindows()
        self.plotwid.canvas.close()

    ## Some spot controlling
    # saves the spot locations to a file, uses workers saveloc-function
    def saveSpots(self):
        filename = str(QFileDialog.getSaveFileName(self, "Save the spot locations to a file"))
        if filename:
            self.worker.saveloc(filename)

    # loads the spots from a file
    def loadSpots(self):
        '''Load saved spot positions, incomplete'''
        # This can probably be done in a better way
        filename = QFileDialog.getOpenFileName(self, 'Open spot location file')
        if filename:
            # pickle doesn't recognise the file opened by PyQt's openfile dialog as a file so 'normal' file processing
            pkl_file = open(filename, 'rb')
            # loading the zipped info to "location"
            location = pickle.load(pkl_file)
            pkl_file.close()
            # unzipping the "location"
            energy, locationx, locationy, radius = zip(*location)
            # NEED TO FIGURE OUT HOW TO GET ALL THE SPOTS TO RESPECTIVE ENERGIES, now only loads the first energy's spots
            # improving might involve modifying the algorithm for calculating intensity
            for i in range(len(energy)):
                #for j in range(len(energy[i])):
                # only taking the first energy location, [0] -> [j] for all, but now puts every spot to the first energy
                point = QPointF(locationx[i][0], locationy[i][0])
                item = QGraphicsSpotView(point, radius[i][0])
                # adding the item to the gui
                self.scene.clearSelection()
                self.scene.addItem(item)
                item.setSelected(True)
                self.scene.setFocusItem(item)
            
            
            

    ## Controlling the spots
    # doesn't do much, only lists how many scene items (circles) there is in the gui, a test for trying to name the spots
    def processSpots(self):
        self.control = SpotControl(self.scene.items(), 0)
      

##### H #
# useless at the moment
class SpotControl(QObject):
    """Class that manages the spots. """

    def __init__(self, spots, i):
        self.names = []
        for spot in spots:
            self.names.append(i)
            #text = "%s" % (self.names[i])
            #textItem = QGraphicsSimpleTextItem(self, text, parent = None, scene = scene.GraphicsView)
            i += 1
        print self.names

#######


class Worker(QObject):
    """ Worker that manages the spots."""

    def __init__(self, spots, energy, parent=None):
        super(Worker, self).__init__(parent)
        self.spots_map = {}
        for spot in spots:
            pos = spot.scenePos()
            tracker = Tracker(pos.x(), pos.y(), spot.radius(), energy,
                        input_precision = config.Tracking_inputPrecision,
                        window_scaling = config.Tracking_windowScalingOn)
#            tracker = TrackerPhysics(pos.x(), pos.y(), 217, 218, spot.radius(), energy)
            self.spots_map[spot] = (QSpotModel(self), tracker)

        for view, tup in self.spots_map.iteritems():
            # view = QGraphicsSpotView, tup = (QSpotModel, tracker) -> tup[0] = QSpotModel
            self.connect(tup[0], SIGNAL("positionChanged"), view.onPositionChange)
            self.connect(tup[0], SIGNAL("radiusChanged"), view.onRadiusChange)

    def process(self, image):
        for model, tracker in self.spots_map.itervalues():
            tracker_result = tracker.feed_image(image)
            # feed_image returns x, y, intensity, energy and radius
            model.update(*tracker_result)

    def save(self, filename):
        intensities = [model.m.intensity for model, tracker \
                                in self.spots_map.itervalues()]
        energy = [model.m.energy for model, tracker in self.spots_map.itervalues()]
        zipped = zip(energy[0], *intensities)
        np.savetxt(filename + ".int", zipped)
        x = [model.m.x for model, tracker \
                in self.spots_map.itervalues()]
        y = [model.m.y for model, tracker \
                in self.spots_map.itervalues()]
        x.extend(y)
        zipped = zip(energy[0], *x)
        np.savetxt(filename + ".pos", zipped)
        
##### H #####        
    def saveloc(self, filename):
        # model = QSpotModel object tracker = tracker
        # dict function .itervalues() = return an iterator over the mapping's values
        energy = [model.m.energy for model, tracker in self.spots_map.itervalues()]
        locationx = [model.m.x for model, tracker in self.spots_map.itervalues()]
        locationy = [model.m.y for model, tracker in self.spots_map.itervalues()]
        radius = [model.m.radius for model, tracker in self.spots_map.itervalues()]
        locations = [locationx, locationy, radius]
        zipped = zip(energy, *locations)
        output = open(filename, 'wb')
        pickle.dump(zipped, output)
        output.close()  
    
