# -*- coding: utf-8 -*-
"""
Created on Thu Jun 12 14:03:55 2025

@author: gaspard.guidetti
"""

import compiler

import sys
# Bibliothèque pour carte Arduino
try:
    from pyfirmata import Arduino, util
except:
    print("Pas de librairie arduino, merci de l'installer (pip install pyfirmata)")

# Import de la partie graphique dessinée dans designer
from alimlabo import Ui_MainWindow

# Import des widgets utilisés
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow, QMessageBox, QFileDialog, QTableWidgetItem
)
# Import des bibliotèques QtCore
from PyQt5.QtCore import QTimer, QFileInfo, Qt, QDateTime
from PyQt5.QtGui import QIcon

import random
import pathlib
from math import log

class Window(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())
