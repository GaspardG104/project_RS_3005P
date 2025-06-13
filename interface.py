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
    QMainWindow, QMessageBox, QFileDialog, QTableWidgetItem)
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
        
        # On associe les cliques sur le bouttons à des fonctions
        #self.NomBouton.clicked.connect(self.NomFonction)
        
        #fichier led.h / promotion style sheet
        self.buttonCV.clicked.connect(self.desactiveCC)
        self.buttonCC.clicked.connect(self.desactiveCV)
        # self.buttonLOCK.clicked.connect(self.bloquePanneau)
        # self.btnReini.clicked.connect(self.reiniTab)
        # self.btnEnregistrer.clicked.connect(self.enregTab)
        # self.btnPause.clicked.connect(self.pauseTab) jsp comment y afficher à la place du bouton commencer
        # self.btnOnoff.clicked.connect(self.onoff)
        self.dialVoltage.valueChanged.connect(self.majDialV)
        self.dialAmpere.valueChanged.connect(self.majDialA)
        # self.realVoltage.valueChanged.connect(self.majRealV)        
        # self.realAmpere.valueChanged.connect(self.majRealA)

    # # On créé des Timer pour les tâches qui se répètent toutes les X ms
    # # Il faut démarrer le timer avec un start !
    #     self.refresh = QTimer()
    #     self.refresh.timeout.connect(self.refreshData)
    #     self.refresh.start(1000)
    
    
    #tableau graph tension
        self.Temps = []
        self.Tension = []
        # Indice de couleur pour les courbes
        self.color = 0
        # Liste des couleurs de courbes
        self.tab_couleur = ['b','g','r','c', 'm','y','black']
        self.col = -2
        self.colonne_Labels = ['Temps (s)','Tension (Ω)']
        self.row = 0
        # Couleur du fond du graphe
        self.TabTension.setBackground("w")
        # Entête du graphe 
        self.TabTension.setTitle('Monitoring de la tension', color ='b')
        # Titre de l'axe vertical
        self.TabTension.setLabel('left','Tension (Ω)', color ='black')
        # Titre de l'axe horizontal
        self.TabTension.setLabel('bottom','Temps (s)', color ='black')
        self.TabTension.showGrid(x = True, y = True, alpha = 0.3)        

        

    def desactiveCC(self):
        self.buttonCV.setEnabled(True)
        self.led.setState(0)
    def desactiveCV(self):
        self.led.setState(1)
        self.buttonCC.setEnabled(True)
        # Le bouton ne reviens pas à modifier
        
    def majDialV(self,event):
        self.nbVoltage.display(event)
        
    def majDialA(self,event):
        self.nbAmpere.display(event)
        
    def enregTab(self):
        self.btnPause.setEnabled(True) #doit remplacer le bouton 
        self.btnEnregistrer.setEnabled(True)
        self.btnReini.setEnabled(True)
        


    # def boutonGraph(self):
    #     self.action
            
    
                
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())
