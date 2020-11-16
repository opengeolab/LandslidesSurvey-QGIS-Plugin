# -*- coding: utf-8 -*-
"""
/***********************************************************************************************************************
 LandslidesSurvey

 This QGIS plugin allows to retrieve all the data inserted through the smartphone application LandslidesSurvey
 (https://github.com/epessina/LandslidesSurvey). The data can be filtered using a vector layer and downloaded both in
 JSON format and as a Shapefile.
 The plugin is compatible with QGIS 3.x.x and does not require any additional dependency.

 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
 -----------------------------------------------------------------------------------------------------------------------
        begin                : 2019-08-20
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Edoardo Pessina
        email                : edoardo2.pessina@mail.polimi.it
 **********************************************************************************************************************/

/****************************************************************
 *    This program is free software; you can redistribute it    *
 *    and/or modify it under the terms of the GNU GPLv3         *
 *    License https://choosealicense.com/licenses/gpl-3.0/#)    *
 ***************************************************************/
"""

# Import the core functionality of PyQGIS
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import QAction, QFileDialog
from qgis.core import *

# Initialize Qt resources from file resources.py
from .resources import *

# Import the code for the dialog
from .landslides_survey_dialog import LandslidesSurveyDialog

# Import the needed modules
import os.path
import requests
import json


class LandslidesSurvey(QObject):
    """ QGIS Plugin Implementation. """

    # URL of the database
    DB_URL = "https://mhyconos.como.polimi.it/"

    # Create a new signal
    all_done = pyqtSignal()

    def __init__(self, iface):
        """ Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """

        # Init the class as a subclass of QObject
        super(LandslidesSurvey, self).__init__()

        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n', 'LandslidesSurvey_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = LandslidesSurveyDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&LandslidesSurvey')

        # Initialize the variables
        self.bb_coord = []
        self.bb_layer = None
        self.bb = None
        self.out_json = ""
        self.out_shp = ""

    def tr(self, message, **kwargs):
        """ Gets the translation for a string using Qt translation API.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """

        return QCoreApplication.translate("LandslidesSurvey", message)

    def add_action(self, icon_path, text, callback, enabled_flag = True, add_to_menu = True, add_to_toolbar = True,
                   status_tip = None, whats_this = None, parent = None):
        """ Adds a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    ###################################################################################################################
    # Start GUI functions.
    ###################################################################################################################

    def initGui(self):
        """ Initializes the GUI of the plugin. """

        # Set the icon
        icon_path = ':/plugins/landslides_survey/icon.png'
        self.add_action(icon_path, text = self.tr(u'LandslidesSurvey'), callback = self.run,
                        parent = self.iface.mainWindow())

        # Disable the bounding box ComboBox
        self.dlg.cb_bb.setEnabled(False)

        # Disable the bounding box ToolButton
        self.dlg.tb_bb.setEnabled(False)

        # Set a listener for the change of the state of the bounding box check box
        self.dlg.chb_bb.stateChanged.connect(self.toggle_bb)

        # Set the behaviour of the bounding box ToolButton
        self.dlg.tb_bb.clicked.connect(self.open_bb_layer)

        # Set the behaviour of the json ToolButton
        self.dlg.tb_json.clicked.connect(self.save_json)

        # Set the behaviour of the shape ToolButton
        self.dlg.tb_shp.clicked.connect(self.save_shp)

        # Set the behaviour of the "run" button
        self.dlg.btn_ok.clicked.connect(self.on_start)

        # Set the behaviour of the "close" button
        self.dlg.btn_close.clicked.connect(self.on_close)

        # Connect the "all_done" signal with the function
        self.all_done.connect(self.on_finished)

    def toggle_bb(self, state):
        """
        Enable or disable the bounding box ComboBox and the ToolButton wrt the state of the CheckBox.

        :param state: State of the checkbox.
        :type state: int.

        """

        # Variable to store the state of the check box
        enable = False

        # If the check box is checked, set "enable" to true
        if state > 0:
            enable = True

        # Enable the bounding box ComboBox
        self.dlg.cb_bb.setEnabled(enable)

        # Enable the bounding box tool button
        self.dlg.tb_bb.setEnabled(enable)

    def open_bb_layer(self):
        """ Opens a vector file from a file dialog and adds it to the map. """

        # Retrieve the selected shape file
        in_file = str(QFileDialog.getOpenFileName(caption = "Open shapefile", filter = "Shapefile (*.shp)")[0])

        # If there is a selected file
        if in_file != "":
            # Add the new layer to the project
            self.iface.addVectorLayer(in_file, str.split(os.path.basename(in_file), ".")[0], "ogr")

            # Load the layer as bounding box
            self.load_bb_layer()

    def load_bb_layer(self):
        """ Loads all the vector layers from the project into the bounding box ComboBox."""

        # Clear the bounding box ComboBox
        self.dlg.cb_bb.clear()

        # Retrieve all the layers in the project
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]

        # Temporal variable to save the vector layers
        vector_layers = []

        # For each layer in the project
        for layer in layers:

            # If the layer is a vector
            if layer.type() == QgsMapLayer.VectorLayer:
                # Add the layer to the "vector_layers" array
                vector_layers.append(layer.name() + " [ " + layer.crs().authid() + "]")

        # Add all the vector layers to the bounding box ComboBox
        self.dlg.cb_bb.addItems(vector_layers)

    def get_bb_layer(self):
        """ Retrieves the vector layer specified in the bounding box ComboBox.

        :return: layer: Layer specified in the bounding box combo box.
        :rtype: layer: QgsMapLayer.VectorLayer
        """

        # Initialize the variable
        layer = None

        # Extract the name of the layer form the ComboBox
        layer_name = self.dlg.cb_bb.currentText()

        # Removes from the layer name the crs
        index = layer_name.find("[") - 1
        layer_name = layer_name[:index]

        # For each layer in the project
        for lyr in QgsProject.instance().mapLayers().values():

            # If the layer name is the one selected
            if lyr.name() == layer_name:
                # Save the layer
                layer = lyr

                # Break the loop
                break

        # Return the layer
        return layer

    def save_json(self):
        """ lets the user choose the name and path of the output JSON file. """

        # Retrieve the selected JSON file
        out_file = str(QFileDialog.getSaveFileName(caption = "Save JSON", filter = "JSON files (*.json)")[0])

        # Set the file as the selected one in the JSON LineEdit
        self.dlg.le_json.setText(out_file)

    def save_shp(self):
        """ lets the user choose the name and path of the output Shapefile. """

        # Retrieve the selected Shapefile file
        out_file = str(QFileDialog.getSaveFileName(caption = "Save Shapefile", filter = "SHP files (*.shp)")[0])

        # Set the file as the selected one in the Shapefile LineEdit
        self.dlg.le_shp.setText(out_file)

    ###################################################################################################################
    # End GUI functions.
    ###################################################################################################################

    ###################################################################################################################
    # Start points manipulation functions.
    ###################################################################################################################

    def init_variables(self):
        """ Initializes the variables needed for the computation. """

        # If the bounding box checkbox is checked
        if self.dlg.chb_bb.isChecked():
            # Save the selected layer
            self.bb_layer = self.get_bb_layer()

        # Save the path of the output json file
        self.out_json = self.dlg.le_json.text()

        # Save the path of the output Shapefile
        self.out_shp = self.dlg.le_shp.text()

    def compute_bb(self):
        """ Compute the bounding box (in EPSG:4326) to filter the points. """

        # If no layer has been selected, return
        if self.bb_layer is None:
            return

        # Initialize the vector of boxes
        boxes = []

        # Extract the crs from the bounding box layer
        source_crs = self.bb_layer.crs()

        # Set WGS84 as target crs
        destination_crs = QgsCoordinateReferenceSystem(4326)

        # Initialize the transformation
        transformation = None

        # If the crs of the layer is not WGS84
        if source_crs != destination_crs:
            # Set the transformation
            transformation = QgsCoordinateTransform(source_crs, destination_crs, QgsProject.instance())

        # Retrieve all the features of the layer
        features = self.bb_layer.getFeatures()

        # For each feature
        for feature in features:
            # Append the bounding box of the feature to the array
            boxes.append(feature.geometry().boundingBox())

        # For each bounding box
        for box in boxes:

            # If there is a transformation to apply
            if transformation is not None:
                # Apply the tranformation
                box = transformation.transformBoundingBox(box)

            # Save the minimum and maximum coordinates of the bounding box
            self.bb_coord.append([box.xMinimum(), box.yMinimum(), box.xMaximum(), box.yMaximum()])

    def save_points(self):
        """ Retrieves, filters and saves the landslides. """

        # Alert the user
        self.dlg.text_status.setText("Retrieving the landslides...")

        # Get the landslides from the database
        res = requests.get(self.DB_URL + "landslide/get-all", headers = {"Accept": "application/json"}).json()

        # Initialize the array of landslides
        landslides = []

        # Variable that states if the writes has an error
        writer_error = False

        # Compute the bounding box
        self.compute_bb()

        print(self.bb_coord)

        # If the output Shapefile has been provided
        if self.out_shp != "":
            # Alert the user
            self.dlg.text_status.setText("Creating the Shapefile...")

            # Initialize the fields object
            fields = QgsFields()

            # Set the fields of the Shapefile
            fields.append(QgsField("id", QVariant.String))
            fields.append(QgsField("latitude", QVariant.Double))
            fields.append(QgsField("longitude", QVariant.Double))
            fields.append(QgsField("altitude", QVariant.Double))
            fields.append(QgsField("type", QVariant.String))
            fields.append(QgsField("imageUrl", QVariant.String))

            # Create the writer to write the Shapefile
            writer = QgsVectorFileWriter(
                self.out_shp,
                "UTF-8",
                fields,
                QgsWkbTypes.Point,
                QgsCoordinateReferenceSystem("EPSG:4326"),
                "ESRI Shapefile"
            )

            # If the writer had an error
            if writer.hasError() != QgsVectorFileWriter.NoError:
                # Alert the user
                self.iface.messageBar().pushMessage(
                    "Error",
                    "Could not create the Shapefile.",
                    level = Qgis.Critical)

                # Set the flag to true
                writer_error = True

        # Alert the user
        self.dlg.text_status.setText("Processing the landslides...")

        # For each landslide
        for ls in res["landslides"]:

            # Set the full path of the image
            ls["imageUrl"] = self.DB_URL + ls["imageUrl"]

            # Delete the __v feature
            ls.pop("__v", None)

            # If no bounding box has been specified
            if self.bb_layer is None:

                # Save the landslide
                landslides.append(ls)

            # Else
            else:

                # For ach bounding box
                for box in self.bb_coord:

                    # If the coordinates of the landslide falls inside the bounding box
                    if box[0] <= ls["coordinates"][1] <= box[2] and box[1] <= ls["coordinates"][0] <= box[3]:
                        # Save the landslide
                        landslides.append(ls)

                        # Break the loop
                        break

        # Alert the user
        self.dlg.text_status.setText("Saving the JSON...")

        # Create the json
        with open(self.out_json, "w") as f_out:

            # Save the landslides in the json
            json.dump(landslides, f_out)

        # If the output Shapefile has been provided and the writer has no errors
        if self.out_shp != "" and not writer_error:

            # Alert the user
            self.dlg.text_status.setText("Saving the Shapefile...")

            # For each of the filtered landslides
            for ls in landslides:
                # Create a feature
                fet = QgsFeature()

                # Set the geometry type and the coordinates of the feature
                fet.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(ls["coordinates"][1], ls["coordinates"][0])))

                # Set the attributes of the feature
                fet.setAttributes([
                    ls["_id"],
                    ls["coordinates"][0],
                    ls["coordinates"][1],
                    None,
                    ls["type"],
                    ls["imageUrl"]
                ])

                # Add the feature to the writer
                writer.addFeature(fet)

            # Delete the writer
            del writer

            # Create the layer
            layer = QgsVectorLayer(self.out_shp, "Landslides", "ogr")

            # If the layer is not valid
            if not layer.isValid():
                # Alert the user
                self.iface.messageBar().pushMessage(
                    "Error",
                    "Could not load the layer.",
                    level = Qgis.Critical)

                # Return
                return

            # Create the html snippet to show in the tooltip
            html_snippet = '<b>Coordinates:</b> [%"latitude"%], [%"longitude"%]' \
                           '<br>' \
                           '<b>Classification:</b> [%"type"%]' \
                           '<br>' \
                           '<img src= \'[%"imageUrl"%]\' width=300 />'

            # Set the tooltip
            layer.setMapTipTemplate(html_snippet)

            # Add the layer to the map
            QgsProject.instance().addMapLayer(layer)

    ###################################################################################################################
    # End points manipulation functions.
    ###################################################################################################################

    ###################################################################################################################
    # Start main functions.
    ###################################################################################################################

    def on_start(self):
        """ Checks if the JSON output file path has been specified and starts the process. """

        # If no Shapefile output file has been selected
        if self.dlg.le_json.text() == "":
            # Alert the user
            self.dlg.text_status.setText("Select the output json file")

            # Return
            return

        # Alert the user
        self.dlg.text_status.setText("Process started...")

        # Disable the "ok" button
        self.dlg.btn_ok.setEnabled(False)

        # Disable the "close" button
        self.dlg.btn_close.setEnabled(False)

        # Start the process
        self.main()

    def on_finished(self):
        """ Re-enables the 'Ok' and 'Close' buttons and alerts the user. """

        # Enable the "ok" button
        self.dlg.btn_ok.setEnabled(True)

        # Enable the "close" button
        self.dlg.btn_close.setEnabled(True)

        # Alert the user
        self.dlg.text_status.setText("Done!")

    def on_close(self):
        """ Closes the plugin and resets its fields. """

        # Disable the bounding box ComboBox
        self.dlg.cb_bb.setEnabled(False)

        # Disable the bounding box ToolButton
        self.dlg.tb_bb.setEnabled(False)

        # Uncheck the bounding box check box
        self.dlg.chb_bb.setChecked(False)

        # Empty the output file fields
        self.dlg.le_json.setText("")
        self.dlg.le_shp.setText("")

        # Reset the status label
        self.dlg.text_status.setText("Compile the fields and press OK...")

        # Reset the variables
        self.bb_coord = []
        self.bb_layer = None
        self.bb = None
        self.out_json = ""
        self.out_shp = ""

        # Close the dialogue
        self.dlg.close()

    def main(self):
        """ Performs the main process. """

        # Initialize the variables
        self.init_variables()

        # Save the points into the Shapefile output file
        self.save_points()

        # Emit a "done" signal
        self.all_done.emit()

    def unload(self):
        """ Removes the plugin menu item and icon from QGIS GUI. """

        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&LandslidesSurvey'), action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """ Runs the plugin. """

        # show the dialog
        self.dlg.show()

        # Load all the vector layers currently in the project in the bounding box ComboBox
        self.load_bb_layer()

        # Run the dialog event loop
        result = self.dlg.exec_()
