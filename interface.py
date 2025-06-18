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

# -*- coding: utf-8 -*-
"""
Simple class for controlling RS-3000 and 6000-series programmable power supplies

Not tested with 6000-series, and a few features for 6000-series are not implemented.
Please feel free to fork and push these missing features:
    * Support for two channels
    * STATUS? and SAV, RCL functions

Andreas Svela 2020
"""

import time
import serial
import numpy as np

PORT = "COM3"
_CONNECTION_SETTINGS = {
    "baudrate": 9600,
    "parity": serial.PARITY_NONE,
    "bytesize": serial.EIGHTBITS,
    "stopbits": serial.STOPBITS_ONE,
}


def test_connection(port=PORT):
    """Simple funtion to test connection to the PSU"""
    with serial.Serial(port=port, **_CONNECTION_SETTINGS, timeout=1) as dev:
        dev.flush()
        dev.write("*IDN?".encode())
        print(dev.readline().decode())


class PowerSupply:
    """Control for RS PRO 3000/6000 Series programmable power supply"""

    _is_open = False

    def __init__(
        self,
        port=PORT,
        connection_settings=_CONNECTION_SETTINGS,
        open_on_init=True,
        timeout=1,
        verbose=True,
    ):
        self.port = port
        self.connection_settings = connection_settings
        self.timeout = timeout
        self.verbose = verbose
        if open_on_init:
            self.open_connection()

    def __enter__(self, **kwargs):
        # The kwargs will be passed on to __init__
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._is_open:
            self.dev.close()
            
    def close(self):
        self.dev.close()

    def write(self, command):
        return self.dev.write(command.encode())

    def query(self, command):
        self.dev.write(command.encode())
        ret = self.dev.readline().decode("utf-8").strip()
        # Query again if empty string received
        if ret == "":
            time.sleep(0.2)
            self.dev.write(command.encode())
            ret = self.dev.readline().decode("utf-8").strip()
        return ret

    def open_connection(self, timeout=None):
        # Override class timeout if argument given
        if timeout is not None:
            self.timeout = timeout
        # Failures to connect are usual, so trying a few times
        tries = 3
        while tries > 0:
            try:
                self.dev = serial.Serial(
                    port=self.port, **self.connection_settings, timeout=self.timeout
                )
            except serial.SerialException:
                if not tries == 1:
                    print("Failed to connect, trying again..")
                else:
                    print("Failed again, will now stop.")
                    raise RuntimeError(f"Could not connect to {self.port}")
                tries -= 2
            else:
                self._is_open = True
                break
        self.dev.flush()
        self.idn = self.get_idn()
        if self.verbose:
            print(f"Connected to {self.idn}")

    def get_idn(self):
        return self.query("*IDN?")
    
    
    
    
    #   !Attention, IDN est mentionner ici
    #   Cependant, il est inscrit ION dans la doc manuscrite


    # def set_output(self, state):
    #     """Works only for 6000-series!"""
    #     if "RS-300" in self.idn:
    #         raise NotImplementedError(
    #             "The set_output() function only works with 6000 series"
    #         )
    #     self.write(f"OUT{state}")
    
    
    

    def get_actual_current(self):
        current = float(self.query("IOUT1?"))
        # Check if within limits of possible values
        current = current if 0 <= current <= 5 else np.nan
        return current

    def set_current(self, current):
        self.write(f"ISET1:{current}")

    def get_actual_voltage(self):
        voltage = float(self.query("VOUT1?"))
        # Check if within limits of possible values
        voltage = voltage if 0 <= voltage <= 30 else np.nan
        return voltage

    def set_voltage(self, voltage):
        self.write(f"VSET1:{voltage}")
        
        
        
        
    # def get_status(self):
    #     #essayer avec un string ou 
    #     status = int(self.query("STATUS?"))
    #     return status
    
#modif du mercredi 11 juin


            
    
    def get_info_output(self):
            os = str(self.query("OUT?"))
            if os==self.query("OUT0"):
                os = "disconnected"
            elif os==self.query("OUT1"):
                os= "connected"
            else:
                os= " error"
            return os
    
    def get_activate_output(self):
        connexion=bool(self.query("OUT?"))
        return connexion
    
    def set_activate_output(self, bool):
        self.write("OUT:bool")

        
    


with PowerSupply() as psu:
    # print("Actual voltage", psu.get_actual_voltage())
    # print("Set voltage to 1V")
    psu.set_voltage(2)
    psu.close()
    # print("Actual voltage", psu.get_actual_voltage())
    # print("Set current to to 1A")
    # psu.set_current(0)
    # print("Actual current", psu.get_actual_current())
    # print("Actual voltage", psu.get_actual_voltage())
    # #Remise à zéro
    # print('remise à zéro')
    # psu.set_voltage(0)
    # print("Actual voltage", psu.get_actual_voltage())
    #psu.set_current(0)
    # print("Actual current", psu.get_actual_current())
    #print("Actual statut", psu.get_statut())
# mercredi----------------------------------------------------------------------
    #print("Identification", psu.get_idn())
    #psu.set_activate_output(0)
    #print("Actual statut of the output : ", psu.get_info_output())



















# ^ partie serial 
####################################################################################################################################☺
# partie python qt

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
        
        self.btnCommencer.clicked.connect(self.creationGraphe)
    

        self.btnReini.clicked.connect(self.reiniTab)       
        self.btnEnregistrer.clicked.connect(self.enregTab)
#        self.btnArret.clicked.connect(self.arret)
        self.btnReiniGra.clicked.connect(self.reiniGraphique)
        
        self.btnOnoff.clicked.connect(self.onoff)
        self.dialVoltage.valueChanged.connect(self.majDialV)
        self.dialVoltage.valueChanged.connect(self.majDialAlimV)
        self.majDialAlimV(True)
        self.dialAmpere.valueChanged.connect(self.majDialA)
        self.realVoltage.valueChanged.connect(self.realV)

        

        # self.realVoltage.valueChanged.connect(self.majRealV)        
        # self.realAmpere.valueChanged.connect(self.majRealA)

        # On créé des Timer pour les tâches qui se répètent toutes les X ms
        # Il faut démarrer le timer avec un start !
        self.timerMesure = QTimer()
        self.timerMesure.timeout.connect(self.read_Data_Mesure)
        
        
        
        self.checkBoxSimu.stateChanged.connect(self.ChangeMode)
        #self.spinBox.valueChanged.connect(self.TimerStartMesure)
        

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


    
    #def arret(self):
        
        
    

    def creationGraphe(self):
        self.btnCommencer.setText('Pause')    
        self.TimerStartMesure()
        self.btnCommencer.click.connect(self.TimerStop)
        self.Quitter.clicked.connect(lambda: self.Mclose())
        self.Data.appendHtml("Initialisation Carte")
        # try except permet d'intercepter les erreurs et évite de terminer le
        # programme de façon "brutale", ex : on peut essayer de se connecter
        # à un port COM et si celui-ci ne répond pas, on essaie les autres
        # try:
        #     self.statusBar.showMessage("Tentative connexion port " +
        #                                str(self.spinBox_COM.value()), 5000)
        #     self.carte = Arduino('COM' + str(self.spinBox_COM.value()))
        # except Exception as e:
        #     self.Data.appendHtml(str(e) + " port " +
        #                                str(self.spinBox_COM.value()))
        #     # On va tenter sur les port COM 0 à 9 de se connecter
        #     for i in range(10):
        #         try:
        #             self.carte = Arduino('COM'+str(i))
        #             print("next")
        #         except Exception:
        #             self.statusBar.showMessage(
        #                 "Tentative connexion port {}\n".format(i), 5000)
        #             #self.Data.appendHtml("Essai port {}\n".format(i))
        #             continue
        #         break
        #     if(i == 9):
        #         self.statusBar.showMessage("Aucune Carte Trouvée !", 5000)
        #         self.Data.appendHtml(
        #             "<b style='color:red'>Aucune Carte Trouvée !</b>")
        #         self.carte = None
        #         return
        # self.statusBar.showMessage("Connected", 5000)
        # acquisition = util.Iterator(self.carte)
        # acquisition.start()
        # # On vérifie que le numéro d'entrée est correct
        # try:
        #     self.signal_A0 = self.carte.get_pin('a:0:i')
        # except Exception as e:
        #     self.Data.appendHtml(
        #         "<b style='color:red'>Carte pas OK !"+str(e)+"</b>")
        #     try:
        #         self.carte.exit()
        #     except Exception as e:
        #         self.Data.appendHtml("<b style='color:red'>"+str(e)+" !</b>")
        #     self.carte = None
        #     return
        # # On modifie la valeur minimum de la vitesse d'acquistion
        # # Pour modifier une propriété, on ajoute set
        # self.spinBox.setMinimum(500)
        # self.spinBox.setValue(1000)
        # self.spinBox.setSingleStep(500)
        # self.Data.appendHtml("Carte prête")
        # # On active la checkBox pour changer de mode
        # self.checkBoxSimu.setEnabled(True)






    def actionCV(self):
        self.led_cv.setState(0)
        self.led_cc.setState(2)
        
    def actionCC(self):# ne pas oublier que le cv bloque le cc
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
        
   

        
        
    def majDialV(self, event):
       self.nbVoltage.display(event)        
             
    def majDialAlimV(self, value):
          with PowerSupply() as psu:
              psu.set_voltage(value)    
        
            
    def majDialA(self,event):
        self.nbAmpere.display(event)
    
    def realV(self, value):
        with PowerSupply() as psu:
            self.realVoltage.display(psu.get_actual_voltage())
        
             
              
        
    def onoff(self):
        self.led_pp.setState(4)
        self.led_pn.setState(5)
        self.led_pgdn.setState(6)
        # self.buttonCC.setEnabled(False)
        # self.buttonCV.setEnabled(False)
        # self.buttonLOCK.setEnabled(False)

    
    def TimerStop(self):
        #self.spinBox.setValue(1000)
        self.TimerStartMesure is False

    
    #Tableau de données
    def TimerStartMesure(self):
        self.btnReini.setEnabled(True)
        self.btnEnregistrer.setEnabled(True)
        self.btnArret.setEnabled(True)
        self.btnReiniGra.setEnabled(True)
        
        
        
        
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
        if (self.test==0):
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
        self.Donnees.clear()
        while self.Donnees.rowCount() > 0:
            self.Donnees.removeRow(0)
        while self.Donnees.columnCount() > 0:
            self.Donnees.removeColumn(0)

        self.col = -2
        self.row = 0
#        self.Data.appendHtml('Tableau effacé\n')
        
    def reiniGraphique(self):
        self.TabTension.clear()


        
        
        
    def enregTab(self):
        """
        Pour choisir un dossier d'enregistrement
        dir_name = QFileDialog.getExistingDirectory()
        print(dir_name)
        """
        file_name = "data" + QDateTime.currentDateTime().toString("_yyyy-MM-dd_hh.mm.ss")
        file_name, Type = QFileDialog.getSaveFileName(
            self, 'Save data', file_name,
            'Text file (*.txt);;CSV file (*.csv);;All files()')
        if(file_name == ""):
            self.Data.appendHtml(
                "<b style='color:red'>Enregistrement annulé</b>")
            return
        with open(file_name, "w") as file:
            # zip permet d'extraire 2 valeurs de 2 listes
            for x, y in zip(self.Temps, self.Tension):
                file.write("{} {}\n".format(x, y))
        path = pathlib.Path(file_name)
        self.Data.appendHtml(path.name +
                     ' : Enregistrement de {} points fait\n'.format(
                         len(self.Temps)))
        
        selected = self.Donnees.selectedRanges()
        if len(selected) > 0:
            texte = ""
            ligne = ""
            with open(file_name+"Selected.txt", "w") as file:
                for i in range(selected[0].topRow(), selected[0].bottomRow() + 1):
                    for j in range(selected[0].leftColumn(), selected[0].rightColumn() + 1):
                        if self.Donnees.item(i, j) != None:
                            texte += self.Donnees.item(i, j).text() + "\t"
                            ligne += self.Donnees.item(i, j).text() + "\t"
                        else:
                            # Sur les colonnes de temps, on ajoute le temps
                            if j%2==0:
                                texte += str(i*(float(self.Donnees.item(1, j).text())-float(self.Donnees.item(0, j).text())))+"\t"
                                ligne += str(i*(float(self.Donnees.item(1, j).text())-float(self.Donnees.item(0, j).text())))+"\t"
                            else:
                                texte += "0\t"
                                ligne += "0\t"
                                
                    texte = texte[:-1] + "\n"  # le [:-1] élimine le '\t' en trop
                    file.write(ligne[:-1] + "\n")
                    ligne = ""
                QApplication.clipboard().setText(texte)
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
    
    
    

