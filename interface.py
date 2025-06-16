# -*- coding: utf-8 -*-
"""
Created on Thu Jun 12 14:03:55 2025

@author: gaspard.guidetti
"""

import compiler
import sys

# Import de la partie graphique dessinée dans designer
from alimlabo import Ui_MainWindow
from classesecond import PyLedLabel

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
        self.buttonCV.clicked.connect(self.actionCV)
        self.buttonCC.clicked.connect(self.actionCC)
        self.buttonLOCK.clicked.connect(self.bloquePanneau)
        self.btnCommencer.clicked.connect(self.TimerStartMesure)
        self.btnCommencer.clicked.connect(self.actionCommencer)
        #self.btnReini.clicked.connect(self.reiniTab)
        
        # self.btnEnregistrer.clicked.connect(self.enregTab)
        # self.self.btnArret.clicked.connect(self.Arret)
        
        self.btnOnoff.clicked.connect(self.onoff)
        self.dialVoltage.valueChanged.connect(self.majDialV)
        self.dialAmpere.valueChanged.connect(self.majDialA)
        # self.realVoltage.valueChanged.connect(self.majRealV)        
        # self.realAmpere.valueChanged.connect(self.majRealA)

        # On créé des Timer pour les tâches qui se répètent toutes les X ms
        # Il faut démarrer le timer avec un start !
        self.timerMesure = QTimer()
        self.timerMesure.timeout.connect(self.read_Data_Mesure)
        
        self.checkBoxSimu.stateChanged.connect(self.ChangeMode)
        self.spinBox.valueChanged.connect(self.TimerStartMesure)
        
    
    #tableau graph tension
        self.Temps = []
        self.Tension = []
        # Indice de couleur pour les courbes
        self.color = 0
        # Liste des couleurs de courbes
        self.tab_couleur = ['b','g','r','c', 'm','y','black']
        self.col = -2
        self.colonne_Labels = ['Temps (s)','Tension (V)']
        self.row = 0
        # Couleur du fond du graphe
        self.TabTension.setBackground("w")
        # Entête du graphe 
        self.TabTension.setTitle('Monitoring de la tension', color ='b')
        # Titre de l'axe vertical
        self.TabTension.setLabel('left','Tension (V)', color ='black')
        # Titre de l'axe horizontal
        self.TabTension.setLabel('bottom','Temps (s)', color ='black')
        self.TabTension.showGrid(x = True, y = True, alpha = 0.3)        

        

    def actionCV(self):
        self.led_cv.setState(0)
        self.led_cc.setState(2)
    def actionCC(self):
        self.led_cc.setState(0)
        self.led_cv.setState(2)      
    def bloquePanneau(self):
        if (self.buttonLOCK.isChecked()):
            self.led_lock.setState(0)
            self.dialVoltage.setEnabled(False)
            self.dialAmpere.setEnabled(False)
            self.dialVoltage.setNotchesVisible(False)
            self.dialAmpere.setNotchesVisible(False)
        else:
            self.led_lock.setState(1)
            self.dialVoltage.setEnabled(True)
            self.dialAmpere.setEnabled(True)
            self.dialVoltage.setNotchesVisible(True)
            self.dialAmpere.setNotchesVisible(True)
        
        

        
        # Le bouton ne reviens pas, à modifier
        
    def majDialV(self,event):
        self.nbVoltage.display(event)
        
    def majDialA(self,event):
        self.nbAmpere.display(event)
        
    def enregTab(self):
        self.btnPause.setEnabled(True) #doit remplacer le bouton 
        self.btnEnregistrer.setEnabled(True)
        self.btnReini.setEnabled(True)
        self.nbAmpere.clearFocus()
        


    # def boutonGraph(self):
    #     self.action
    
    def onoff(self):
        self.led_pp.setState(4)
        self.led_pn.setState(5)
        self.led_pgdn.setState(6)
        # self.buttonCC.setEnabled(False)
        # self.buttonCV.setEnabled(False)
        # self.buttonLOCK.setEnabled(False)
        
    
    def actionCommencer(self):# se transform en pause
        self.btnCommencer.setText("Pause")
        self.btnCommencer.clicked.connect(self.actionPause)
        # self.btnReini.setEnable(True)
        # self.btnEnregistrer.setEnable(True)
        # self.btnArret.setEnable(True)
        self.btnCommencer.clicked.connect(self.TimerStop)
        
        
    def actionPause(self):#se transforme en commencer 
        self.btnCommencer.setText("Continuer")
    
    def TimerStop(self):
        self.spinBox.setValue(1000)
        self.timerMesure.stop()
        self.Data.appendHtml('Stop Measuring\n')
            
            
    #Tableau de données
    def TimerStartMesure(self):
        # Réinitialistaion des listes de données
        self.Temps, self.Tension=[],[]
        self.col += 2
        self.row = 0        
        #Création de nouvelles colonnes de données
        self.Donnees.insertColumn(self.col)
        self.Donnees.insertColumn(self.col + 1)
        # Définition des entêtes de colonnes
        self.colonne_Labels.append('Temps (s)')
        self.colonne_Labels.append('Tension (V)')
        self.Donnees.setHorizontalHeaderLabels(self.colonne_Labels)
        
        # boucle d'incrémentation des couleurs des courbes
        if self.color < len(self.tab_couleur)-1:
            self.color += 1
        else :
            self.color = 0
        # Démarrage du timer d'acquisition
        self.timerMesure.start(self.spinBox.value())
        if(self.checkBoxSimu.isChecked()):
            self.Data.appendHtml('Start Simulation at {} ms\n'.format(
                self.spinBox.value()))
        else:
            self.Data.appendHtml('Start Measuring at {} ms\n'.format(
                self.spinBox.value()))
        
    
                
    def read_Data_Mesure(self):
        # Génération de l'axe X
        if len(self.Temps) > 0 and self.row > 0:
            # Si le point 0 existe, on créé le nouveau point en ajoutant le
            # point précédent à la valeur de la vitesse d'acquisition
            self.Temps.append(self.Temps[-1] + self.spinBox.value()/1000.0)
        else:
            self.Temps.append(0)
    
        # Si on est en mode simu, on ajoute des points aléatoires
        if(self.checkBoxSimu.isChecked()):
            self.Tension.append(random.uniform(0, 2) + 19)
        # Sinon on récupère les valeurs de l'alimentation
        
#A modifier pour la liaison avec l'alimentation de laboratoire
        
        # else:
        #     try:
        #         signalCTN = self.signal_A0.read()
        #         Rref = 1000                          
        #         R = Rref * signalCTN / (1 - signalCTN) #
        #         R0 = 950 # paramètre étalonnage - Résistance à T0 25°C soit 298 K
        #         T0 = 298 # 28°C
        #         beta = 4070   # gap de la thermistance
        #         T = 1 / (log(R/R0) / beta + 1/T0) - 273 # Loi d'étalonnage de la thermistance
        #         self.Temperature.append(T)
        #     except Exception:
        #         self.Data.appendHtml(
        #             "<b style='color:red'>Erreur de mesure</b>")
    
    
        # Affichage de la courbe
        self.TabTension.plot(self.Temps, self.Tension, symbolBrush=(self.tab_couleur[self.color]))
        #self.TabTension.show()
        row = self.Donnees.rowCount()
        # print(self.row, row)
        if self.row >= row:
            self.Donnees.insertRow(row)
        self.Donnees.setItem(self.row,self.col,
                             QTableWidgetItem("{:.2f}".format(self.Temps[-1])))
        self.Donnees.setItem(self.row,self.col+1,
                             QTableWidgetItem("{:.2f}".format(self.Tension[-1])))
        self.row += 1        
        
    def reiniTab(self):
            while self.Donnees.rowCount() > 0:
                self.Donnees.removeRow(0)
            while self.Donnees.columnCount() > 0:
                self.Donnees.removeColumn(0)

            self.col = -2
            self.row = 0
            self.Data.appendHtml('Tableau effacé\n')

    def ChangeMode(self, checkState):
        # Test si la checkbox est cochée
        if (checkState == Qt.Checked):
            # Modification de la valeur mini de la spinbox
            self.spinBox.setMinimum(10)
        else:
            self.spinBox.setMinimum(500)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())
