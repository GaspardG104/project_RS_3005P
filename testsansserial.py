# -*- coding: utf-8 -*-
"""
Created on Fri Jun 20 15:10:26 2025

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
from PyQt5.QtCore import QTimer, QFileInfo, Qt, QDateTime, QThread
from PyQt5.QtGui import QIcon

#ajout pour l'optimisation QSerialPort 
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt5.QtCore import QIODevice, pyqtSignal, QObject, QThread

import random
import pathlib
from math import log

import time
import numpy as np

        
class SerialWorker(QObject):
    data_received = pyqtSignal(bytes)
    response_serial = pyqtSignal()
    port_opened = pyqtSignal(bool, str) # bool success, str message
    port_closed = pyqtSignal()
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()
    
    mesures_received = pyqtSignal(float)
    donnees_mesures = pyqtSignal(list)
    
    #Ce qui s'envoi en dehors du SerialWorker
    command = pyqtSignal()
    _write_request = pyqtSignal(bytes)
    

    def __init__(self):
        super().__init__()
        self._serial_port = QSerialPort()
        self._serial_port.readyRead.connect(self._read_data)
        self._write_request.connect(self._write_data)
        self._is_open = False
        self.timerMesure = QTimer()
        self.Temps = []
        self.Tension = []
        self.Current = []
        self.row = 0
        self.open_port("COM3", 9600)
        
 
    def open_port(self, port_name, baud_rate):
        if self._serial_port.isOpen():
            self._serial_port.close() # Ferme si déjà ouvert
 
        self._serial_port.setPortName(port_name)
        self._serial_port.setBaudRate(baud_rate)
        if self._serial_port.open(QIODevice.ReadWrite):
            self._is_open = True
            self.port_opened.emit(True, f"Port {port_name} ouvert à {baud_rate} bauds.")
        else:
            self._is_open = False
            self.port_opened.emit(False, f"Erreur d'ouverture du port {port_name}: {self._serial_port.errorString()}")
            self.error_occurred.emit(self._serial_port.errorString())
 
    def _close_port(self):
        if self._serial_port.isOpen():
            self._serial_port.close()
            self._is_open = False
            self.port_closed.emit()
            print("Port fermé dans le worker.")
 
    def _write_data(self, data):
        if self._is_open:
            self._serial_port.write(data)
        else:
            self.error_occurred.emit("Impossible d'écrire: le port n'est pas ouvert.")
 
    def _read_data(self):
        while self._serial_port.bytesAvailable():
            data = self._serial_port.readAll().data()
            self.data_received.emit(data)
            
            
    def _query(self, command):
        if self._serial_port.isOpen():
            self._write_data.emit((command + "\n").encode('ascii'))# je sais âs si l'encodage en ascii est utile en vrais
        else:
            self.error_occurred.emit("Impossible d'écrire: le port n'est pas ouvert.")
                
#Partie des commandes de l'alimentation:
    
    def get_idn(self):
        self._query("*IDN?")

    def set_voltage(self, voltage):
        self._query(f"VSET1:{voltage}")

    def get_actual_voltage(self):
        self._query("VOUT1?")

    def get_actual_current(self):
        self._query("IOUT1?")
    
    #Modifie le courrent (Ampere)
    def set_current(self, current):
        self._query(f"ISET1:{current}")
        
    
    #Active/désactive le mode LOCK qui vérouille le panneau de controle
    def _set_lock(self, lockonoff):
        self._query(f"LOCK{lockonoff}")
            
    #Active/désactive le mode OCP (Over Current Protection)    
    def set_ocp(self, ocponoff):
        self._query(f"OCP{ocponoff}")
            
    #Demande si le port de sortie électronique est activer ou désactiver           
    def get_info_output(self):
            os = self._query("STATUS?")
            if (os=="S"):
                os = "connected"
            elif (os==" "):
                os= "disconnected"
            else:
                os= " error"
            return os
        
    #Active/Désactive le port de sortie électronique
    def _set_activate_output(self, outonoff):
        self._write_data(f"OUT{outonoff}")
            
    def _stop_mesure_timer(self):
        self.timerMesure.stop()   


    def _read_mesure(self):             #IL FAUT METTRE mesures_received.emit A LA PLACE DES APPENDS
        #démarage du timer
        self.timerMesure.start()
        # Génération de l'axe X 
        if len(self.Temps) > 0 and self.row > 0:
            # Si le point 0 existe, on créé le nouveau point en ajoutant le
            # point précédent à la valeur de la vitesse d'acquisition
            self.Temps.append(self.Temps[-1] + self.spinBox.value()/1000.0)
        else:
            self.Temps.append(0)
        
        # Si on est en mode simu, on ajoute des points aléatoires
        if(self.checkBoxSimu.isChecked()):
            self.mesures_received_voltage.emit()(random.uniform(0, 2) + 19)
        
        # Si on est en mode simu, on ajoute des points aléatoires
        if(self.checkBoxSimu.isChecked()):
            self.Current.append(random.uniform(0, 2) + 4)
        
        else:                           #fait lagger le code probleme d'indexage de liste
            self.Tension.append(self.get_actual_voltage())
            self.Current.append(self.get_actual_current())

        #timer  tension emit lier au display
        self.nouveaux_tableaux= [self.Temps, self.Tension, self.Current]
        self.donnees_mesures.emit(self.nouveaux_tableaux)
        
            
# class Window(QMainWindow, Ui_MainWindow):
#     open_port_request = pyqtSignal(str, int)
#     close_port_request = pyqtSignal()

#     def __init__(self):
#         super().__init__()
#         self.setupUi(self)
        
#         self._serial_thread = QThread()
#         self._serial_worker = SerialWorker()
#         self._serial_worker.moveToThread(self._serial_thread)
        
#         self.dialVoltage.valueChanged.connect(lambda: self._serial_worker.set_voltage(5))
        
#         # Connexions entre MainWindow et SerialWorker
#         self.open_port_request.connect(self._serial_worker.open_port)
#         self.close_port_request.connect(self._serial_worker._close_port)
        
#         # Connexions des signaux du SerialWorker vers les slots de MainWindow (pour mise à jour UI)

        
#         # Démarrer le thread. Le worker ne commencera ses opérations que quand ses slots seront appelés.
#         self._serial_thread.start()
#         print("MainWindow: QThread démarré.")

#     def start_serial_communication(self):
#             # Émettre un signal pour demander au worker d'ouvrir le port
#             self.open_port_request.emit("COM3", 9600) # Remplacez "COM3" par le port de votre appareil






class Window(QMainWindow, Ui_MainWindow):
    open_port_request = pyqtSignal(str, int)
    _close_port_request = pyqtSignal(str, int)
    write_data_request = pyqtSignal(bytes)   
    dialV_request = pyqtSignal(float)
    dialA_request = pyqtSignal(float)
    # V_request = pyqtSignal(float)  pour afficher les valeur réels
    # A_request = pyqtSignal(float)
    mesures_request = pyqtSignal(list)
    LOCK_request = pyqtSignal(int)
    start_read_mesures_request = pyqtSignal() 
    stop_mesure_timer_request = pyqtSignal()
    info_spinBox = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.init_ui()
        self.serial_thread = QThread()
        self.serial_worker = SerialWorker()
        self.serial_worker.moveToThread(self.serial_thread)
        self.nouveaux_tableaux=[]
        # Connexions des signaux de la GUI aux slots du worker          MainWindow -->Worker
        self.open_port_request.connect(self.serial_worker.open_port)
        self.close_port_request.connect(self.serial_worker._close_port)
        # self.write_data_request.connect(self.serial_worker._write_data)
        # Dial des Voltes pour modifier la valeurs   
        self.dialV_request.connect(self.serial_worker.set_voltage)    
        # Dial des amperes pour modifier la valeurs
        self.dialA_request.connect(self.serial_worker.set_current)   
        #Bloquage du panneau
        self.LOCK_request.connect(self.serial_worker._set_lock)
        #Commence le timer
        self.start_read_mesures_request.connect(self.serial_worker._read_mesure)
        #Arrete  le timer
        self.stop_mesure_timer_request.connect(self.serial_worker._stop_mesure_timer)
        #envoi un signal pour la spinBox
        self.info_spinBox.connect(self.serial_worker._spin_box)
        # Connexions des signaux du worker aux slots de la GUI          Worker --> MainWindow
        
        # Pour plus tard ca dessous
        # self.serial_worker.data_received.connect(self.reception_data)
        # self.serial_worker.port_opened.connect(self.handle_port_opened)
        # self.serial_worker.port_closed.connect(self.handle_port_closed)        
        
        self.serial_worker.donnees_mesures.connect(self.tableau) # le tableau recupere les données de _read_mesure pour les affichées
       
        # Démarrer le thread lorsque l'application est prête
        self.serial_thread.start()
        
        self.actionQuitter.triggered.connect(self.closeapp)
        
        # Connecter le signal finished du thread à la suppression du worker
        self.serial_thread.finished.connect(self.serial_worker.deleteLater)
        self.serial_thread.finished.connect(self.serial_thread.deleteLater)   
        
# BIEN PENSER A FAIRE LA SEPARATION SERIAL/UI

    def init_ui(self):

        # On associe les cliques sur le bouttons à des fonctions
        # self.NomBouton.clicked.connect(self.NomFonction)
        
        # fichier led.h / promotion style sheet
        self.buttonLOCK.clicked.connect(self.bloquePanneau)
        self.buttonOCP.clicked.connect(self.actionOCP)
        
        # self.indiceOut.clicked.connect(self.desactiveSortie)
        self.btnReini.clicked.connect(self.reiniTab)       
        self.btnEnregistrer.clicked.connect(self.enregTab)
        self.btnReiniGra.clicked.connect(self.reiniGraphique)
        self.btnOnoff.clicked.connect(self.onoff)
        
        # On créé des Timer pour les tâches qui se répètent toutes les X ms
        self.checkBoxSimu.stateChanged.connect(self.ChangeMode)
        self.alimRS = None
        
        # tableau graphe, je pense qu'il faut les déclarés que une fois mais jsp où et comment...
        self.Temps = []
        self.Tension = []
        self.Current=[]
        
        # Indice de couleur pour les courbes
        self.color = 0
        
        # Liste des couleurs de courbes
        self.tab_couleur = ['b','g','r','c', 'm','y','black']
        self.col = -3
        self.colonne_Labels = ['Temps (s)','Tension (V)','Courant (A)']
        self.row = 0
        
        # Couleur du fond du graphe
        self.TabTension.setBackground("w")
        
        # Entête du graphe 
        self.TabTension.setTitle('Monitoring de la tension', color ='b')
        
        # Titre de l'axe vertical
        self.TabTension.setLabel('left','Tension (V) et Courant (A)', color ='black')
        
        # Titre de l'axe horizontal
        self.TabTension.setLabel('bottom','Temps (s)', color ='black')
        self.TabTension.showGrid(x = True, y = True, alpha = 0.3)        

    def request_open_port(self):
        port_name = self.port_combo.currentText()
        baud_rate = int(self.baud_combo.currentText())
        self.open_port_request.emit(port_name, baud_rate)
 
    def request_close_port(self):
        self.close_port_request.emit()

    
      
        
# Action des boutons et voyants
    def actionOCP(self):
        if (self.buttonOCP.isChecked()):
            self.psu.set_ocp(1)
            self.led_ocp.setState(0)
        else:
            self.psu.set_ocp(0)
            self.led_ocp.setState(1)

    def actionCV(self):
        self.led_cv.setState(0)
        self.led_cc.setState(2)
        
    def actionCC(self):# ne pas oublier que le cv bloque le cc
        self.led_cc.setState(0)
        self.led_cv.setState(2)      
        
    def bloquePanneau(self):
        if (self.buttonLOCK.isChecked()):
            self.LOCK_request.emit(0)
            self.led_lock.setState(0)
            self.dialVoltage.setEnabled(False)
            self.dialAmpere.setEnabled(False)
            self.dialVoltage.setNotchesVisible(False)
            self.dialAmpere.setNotchesVisible(False)
        else:
            self.LOCK_request.emit(0)
            self.led_lock.setState(1)
            self.dialVoltage.setEnabled(True)
            self.dialAmpere.setEnabled(True)
            self.dialVoltage.setNotchesVisible(True)
            self.dialAmpere.setNotchesVisible(True) 
    
    def dialVoltage(self, value):
        self.dialV_request.emit(float(value))
           
    def dialAmpere(self, value):
        self.dialA_request.emit(float(value))

    # def realV(self, value):
    # with PowerSupply() as psu:
    # self.realVoltage.display(psu.get_actual_voltage())
        
    def onoff(self): # a transformer pour le démarrage de l'appareil
        self.led_pp.setState(4)
        self.led_pn.setState(5)
        self.led_pgdn.setState(6)
        # self.buttonCC.setEnabled(False)
        # self.buttonCV.setEnabled(False)
        # self.buttonLOCK.setEnabled(False)

    # def desactiveSortie(self):
    #     if self.indiceOut.isChecked():
    #         with PowerSupply() as psu:
    #             psu.__set_activate_output("0")
    #             print("sortie",psu.get_info_output())
    #     else:
    #         with PowerSupply() as psu:
    #             psu.__set_activate_output("1")
    #             print("sortie",psu.get_info_output())
    
     
        
    #Tableau de données
    def TimerStartMesure(self):
        if self.btnCommencer.text() != "Pause":
            if self.btnCommencer.text() == "Commencer l'enregistrement":
                self.start_read_mesures_request.emit()
                self.btnCommencer.setText('Pause')
                self.btnReini.setEnabled(True)
                self.btnEnregistrer.setEnabled(True)
                self.btnReiniGra.setEnabled(True)

                        # Réinitialistaion des listes de données
                self.resdonnees() 
                self.col += 3
                self.row = 0        
                #Création de nouvelles colonnes de données
                self.Donnees.insertColumn(self.col)
                self.Donnees.insertColumn(self.col + 1)
                self.Donnees.insertColumn(self.col + 2)
                # Définition des entêtes de colonnes
                self.colonne_Labels.append('Temps (s)')
                self.colonne_Labels.append('Tension (V)')
                self.colonne_Labels.append('Courant (A)')
                self.Donnees.setHorizontalHeaderLabels(self.colonne_Labels)     
                # boucle d'incrémentation des couleurs des courbes
                if self.color < len(self.tab_couleur)-1:
                    self.color += 1
                else :
                    self.color = 0
                    # Démarrage du timer d'acquisition
                self.timerMesure.start(self.spinBox.value())
                if(self.checkBoxSimu.isChecked()):
                    self.spinBox(self.info_spinBox.emit.value())                      
                else:
                    self.spinBox(self.info_spinBox.emit.value())                      
                
            elif self.btnCommencer.text() == "Continuer":
                self.btnCommencer.setText('Pause')
                self.timerMesure.start(self.spinBox.value())
            
        elif self.btnCommencer.text() == "Pause":
            self.stop_mesure_timer_request.emit()
            self.btnCommencer.setText('Continuer')    

    def resdonnees(self):
        self.Temps, self.Tension, self.Current=[],[],[]
        
        
    def tableau(self, nouveaux_tableaux : list):   #il recupere les données du calculs de _read_mesure pour y afficher dans le tableau //// Plusieurs maniere d'y écrire
        # Récuperation des tableaux :
            self.Temps = nouveaux_tableaux[0]
            self.Tension = nouveaux_tableaux[1]
            self.Current= nouveaux_tableaux[2]
            
            
        # Affichage de la courbe
            self.TabTension.plot(self.Temps, self.Tension, symbolBrush=(self.tab_couleur[0]))
            self.TabTension.plot(self.Temps, self.Current, symbolBrush=(self.tab_couleur[1]))
            self.TabTension.show()
            row = self.Donnees.rowCount()
            if self.row >= row:
                self.Donnees.insertRow(row)
            self.Donnees.setItem(self.row,self.col,
                                  QTableWidgetItem("{:.2f}".format(self.Temps[-1])))
            self.Donnees.setItem(self.row,self.col+1,
                                  QTableWidgetItem("{:.2f}".format(self.Tension[-1])))
            self.Donnees.setItem(self.row,self.col+2,
                                  QTableWidgetItem("{:.2f}".format(self.Current[-1])))
            self.row += 1        

        
    def reiniTab(self):
        self.btnCommencer.setText("Commencer l'enregistrement")
        self.resdonnees()
        while self.Donnees.rowCount() > 0:
            self.Donnees.removeRow(0)
        while self.Donnees.columnCount() > 0:
            self.Donnees.removeColumn(0)            
        self.col = -3
        self.row = 0
        self.btnReini.setEnabled(False)
        self.btnEnregistrer.setEnabled(False)
        
    def reiniGraphique(self):
        self.TabTension=[]
        self.btnReiniGra.setEnabled(False)
 
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
        # if(file_name == ""):             je n'utilise pas de tableau de retour 
        #     self.Data.appendHtml(
        #         "<b style='color:red'>Enregistrement annulé</b>")
        #     return            
        with open(file_name, "w") as file:
            # zip permet d'extraire 2 valeurs de 2 listes
            for x, y, z in zip(self.Temps, self.Tension, self.Current):
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
        info_spinbox = (checkState == Qt.Checked)
        if info_spinbox:
            self.spinBox.setMinimum(10)
        else:
            self.spinBox.setMinimum(500)
        # Informer le worker du changement de modepour le timer de mesure
        if self.serial_worker._mesure_timer.isActive():
            self.start_mesure_timer_request.emit(self.spinBox.value(), info_spinbox)
            
            
    def closeapp(self):
        # On stoppe les mesures si l'alimentation a été initialisée
        if(self.alimRS is not None):
            self.alimRS.exit()
        self.close()            
        
    def closeEvent(self, event):
        # S'assurer que le thread se termine proprement à la fermeture de l'application
        self._close_port_request.emit()
        self.serial_thread.quit()
        self.serial_thread.wait() # Attendre que le thread se termine
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())
    
 