# -*- coding: utf-8 -*-
"""
Created on Fri Jun 27 14:16:35 2025

@author: gaspard.guidetti
"""

import sys
import compiler
# Import de la partie graphique dessinée dans designer
from alimlabo import Ui_MainWindow
from classesecond import PyLedLabel

# Import des widgets utilisés
from PyQt5.QtWidgets import (QApplication, QMessageBox, QFileDialog, QTableWidgetItem, QApplication, QMainWindow, QPushButton, 
QVBoxLayout, QWidget, QTextEdit, QLineEdit, QLabel)
# Import des bibliotèques QtCore
from PyQt5.QtCore import QFileInfo, Qt, QDateTime, QThread, QObject, pyqtSignal, pyqtSlot, QIODevice, QEventLoop, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo

#Pour enregistrer le graphique mais chepa si jaurais pu faire le tracé des courbes avec ca directemment a voir 
import pyqtgraph as pg
import pyqtgraph.exporters

import random
import pathlib
from math import log
import time

import string
class SerialWorker(QObject):
    """
    Worker pour gérer la communication série dans un thread séparé.
    Émet des signaux pour communiquer avec l'interface utilisateur.
    """
    # Signaux émis par le worker pour l'UI
    port_status = pyqtSignal(bool, str)     # (succès, message)
    data_received = pyqtSignal(str)         # Données décodées reçues (générique, pour la console)
    error_occurred = pyqtSignal(str)        # Messages d'erreur


    # Signal interne pour demander l'écriture (appelé par des méthodes publiques)
    _write_request = pyqtSignal(bytes)
    # Signal interne pour les requêtes, utilisé par la fonction _query
    _query_response_received = pyqtSignal(str)
    
    table_mesures_ready = pyqtSignal(list)
    #signal pour change la valeurs de temps de latence de _query
    default_query_timeout_updated = pyqtSignal(int)
    statut = pyqtSignal(str)
    

    def __init__(self):
        super().__init__()
        self._serial_port = QSerialPort()
        self._serial_port.readyRead.connect(self._read_data)
        self._write_request.connect(self._write_data)
        self._is_open = False
        # Variables pour la fonction _query
        self._query_data_buffer = ""
        self._query_waiting_for_response = False
        self._query_event_loop = None
        self._query_timeout_timer = QTimer(self)
        self._query_timeout_timer.setSingleShot(True)
        self._query_timeout_timer.timeout.connect(self._on_query_timeout)
        self._default_query_timeout_ms = 1000

    
    @pyqtSlot(str, int)
    def _open_port(self, port_name, baud_rate):
        
        """Ouvre le port série avec les paramètres spécifiés."""
        if self._serial_port.isOpen():
            self._serial_port.close()

        self._serial_port.setPortName(port_name)
        self._serial_port.setBaudRate(baud_rate)
        self._serial_port.setDataBits(QSerialPort.Data8)
        self._serial_port.setParity(QSerialPort.NoParity)
        self._serial_port.setStopBits(QSerialPort.OneStop)
        self._serial_port.setFlowControl(QSerialPort.NoFlowControl)

        if self._serial_port.open(QIODevice.ReadWrite):
            self._is_open = True
            self.port_status.emit(True, f"Port '{port_name}' ouvert à {baud_rate} bauds.")
            self.data_received.emit("Port ouvert !")
            self._remise_zero()  

            
        else:
            self._is_open = False
            error_msg = self._serial_port.errorString()
            self.port_status.emit(False, f"Erreur d'ouverture de '{port_name}': {error_msg}")
            self.data_received.emit("Erreur d'ouverture ")
            self.error_occurred.emit(error_msg)

    @pyqtSlot()
    def _close_port(self):
        """Ferme le port série."""
        if self._serial_port.isOpen():
            self._remise_zero()
            self._serial_port.close()
            self._is_open = False
            self.port_status.emit(False, "Port série fermé.")
            self.data_received.emit("Port série fermé.")
            # Si une requête est en attente, la terminer
            if self._query_waiting_for_response and self._query_event_loop:
                self._query_timeout_timer.stop()
                self._query_event_loop.quit()
                self._query_waiting_for_response = False


    @pyqtSlot(bytes)
    def _write_data(self, data):
        """Slot interne pour écrire des octets sur le port série."""
        if self._is_open:
            written_bytes = self._serial_port.write(data)
            if written_bytes == -1:
                self.error_occurred.emit(f"Erreur d'écriture: {self._serial_port.errorString()}")
        else:
            self.error_occurred.emit("Impossible d'écrire: le port n'est pas ouvert.")



    @pyqtSlot()
    def _read_data(self):
        """Slot pour lire les données disponibles quand 'readyRead' est émis."""
        while self._serial_port.bytesAvailable():
            data = self._serial_port.readAll().data()
            try:
                # Décoder les octets reçus en chaîne (souvent 'ascii' ou 'utf-8')
                decoded_data = data.decode('ascii').strip()

                if decoded_data :
                    
                    # self.data_received.emit(decoded_data)
                
                    # Si une _query est en attente, capturer cette réponse
                    if self._query_waiting_for_response and self._query_event_loop:
                        self._query_data_buffer = decoded_data # Stocke la réponse
                        self._query_timeout_timer.stop()       # Arrête le timeout
                        self._query_event_loop.quit()          # Quitte la boucle d'événements
                        self._query_waiting_for_response = False # Réinitialise l'état

            except UnicodeDecodeError:
                self.error_occurred.emit(f"Erreur de décodage des données: {data!r}")

             
    @pyqtSlot()
    def _on_query_timeout(self):
        """Appelé si le timeout de la requête est atteint."""
        self.error_occurred.emit("Timeout lors de l'attente de la réponse à la requête.")
        if self._query_event_loop:
            self._query_event_loop.quit() # Quitte la boucle d'événements
        self._query_waiting_for_response = False
        self._query_data_buffer = "" # Efface le buffer en cas de timeout


    @pyqtSlot(int)
    def _set_default_query_timeout(self, new_timeout_ms):
        if new_timeout_ms > 0: # S'assurer que le timeout est positif
            self._default_query_timeout_ms = new_timeout_ms
            self.data_received.emit(f"Timeout des requêtes défini à {new_timeout_ms} ms.")
            self.default_query_timeout_updated.emit(new_timeout_ms) 
        else:
            self.error_occurred.emit("Le timeout des requêtes doit être une valeur positive.")
        # PAS DE RETURN ICI ! Un pyqtSlot ne doit généralement pas retourner de valeur
    
    
    @pyqtSlot(str, int, result=str)
    def _query(self, command_string, timeout_ms = -1): 
        if not self._is_open:
            self.error_occurred.emit("Impossible d'effectuer la requête: le port n'est pas ouvert.")
            return ""

        if self._query_waiting_for_response:
            self.error_occurred.emit("Une autre requête est déjà en attente de réponse. Veuillez patienter.")
            return "" # Évite d'empiler les requêtes
        
        actual_timeout = self._default_query_timeout_ms
        if timeout_ms != -1: # Si un timeout spécifique est fourni, on l'utilise à la place
            actual_timeout = timeout_ms
            
        self._query_waiting_for_response = True
        self._query_data_buffer = "" # Réinitialise le buffer pour la nouvelle requête
        # Envoie la commande
        self._write_request.emit((command_string + "\n").encode('ascii'))
        # Crée et exécute une boucle d'événements pour attendre la réponse
        self._query_event_loop = QEventLoop()  
        self._query_timeout_timer.start(actual_timeout)   
        self._query_event_loop.exec_() # Bloque le thread du worker ici
        # Nettoyage après la fin de la boucle (timeout ou réponse reçue)
        self._query_event_loop = None # Libère la référence à la boucle
        self._query_waiting_for_response = False 
        return self._query_data_buffer # Retourne ce qui a été stocké dans le buffer


    def _send_command(self, command_string):
        """Envoie une commande textuelle sans attendre de réponse immédiate."""
        self._write_request.emit((command_string + "\n").encode('ascii'))


    def _request_idn(self):
        """Demande l'identification de l'appareil et renvoie la réponse."""
        return self._query("*IDN?")
    
    
    def _request_status(self):        
        s = self._query("STATUS?")
        if (s == "\12" or s== "↕" or s==""):
            statut = "OCP OFF, C.C OFF, C.V OFF, LOCK ON/OFF, OUT OFF"
        elif (s == "S"):
            statut = "OCP OFF, C.C OFF, C.V ON, LOCK ON/OFF, OUT ON"
        elif (s=="R"):
            statut ="OCP ON, C.C ON, C.V OFF, LOCK ON/OFF, OUT ON" 
        elif (s == "2"):
            statut = "OCP ON, C.C OFF, C.V OFF, LOCK ON/OFF, OUT OFF"
        elif (s == "s"):
            statut = "OCP ON, C.C OFF, C.V ON, LOCK ON/OFF, OUT ON"
        else:
            statut = "Statut non réferencé ou alors résistance exacte"
        return statut
    

    def _status_leds(self):
        s = self._query("STATUS?")
        self.statut.emit(s)
        
        
    def _set_voltage(self, voltage):
        """Définit la tension de sortie de l'alimentation."""
        self._send_command(f"VSET1:{voltage}")

    
    def _get_voltage(self):
        responsev = float(self._query("VOUT1?"))
        return responsev
        try:
            if "VOUT1:" in responsev: 
                voltage = float(responsev.split("VOUT1:")[-1].strip())
                return voltage
            else:
                self.error_occurred.emit(f"Format de réponse VOUT1 inattendu ou vide: '{responsev}'")
                return float('nan')
        except ValueError:
            self.error_occurred.emit(f"Impossible de parser la tension de: '{responsev}'")
            return float('nan')


    def _set_ampere(self, ampere):
        self._send_command(f"ISET1:{ampere}")


    def _get_ampere(self):
        #Demande le courant de sortie actuel et renvoie la valeur.
        responsec = float(self._query('IOUT1?'))
        return responsec
        try:
            if "IOUT1:" in responsec:
                current = float(responsec.split("IOUT1:")[-1].strip())
                return current
            else:
                self.error_occurred.emit(f"Format de réponse IOUT1 inattendu ou vide: '{responsec}'")
                return float('nan')
        except ValueError:
            self.error_occurred.emit(f"Impossible de parser le courant de: '{responsec}'")
            return float('nan')


    def _set_output(self, state):
        """Active (1) ou désactive (0) la sortie de l'alimentation."""
        self._send_command(f"OUT{int(state)}")
        
        
    def _set_ocp(self, state):
        # si ocp acitf = 1 ou inactif = 0
        self._send_command(f"OCP{int(state)}")
        
        
    @pyqtSlot()
    def _read_mesures(self):
        if not self._is_open:
            self.error_occurred.emit("Port non ouvert pour la lecture des données.")  
            return
        TensionValue = self.get_voltage() # Appelle méthode get_voltage qui utilise _query
        CurrentValue = self.get_ampere() # Appelle méthode get_ampere qui utilise _query     
        self.table_mesures_ready.emit([TensionValue, CurrentValue])
        
        
    def _set_lock(self, state):
        # si ocp acitf = 1 ou inactif = 0
        self._send_command(f"LOCK{int(state)}")
        
        
    def _remise_zero(self):
            self._send_command("ISET1:0")
            self._send_command("VSET1:0")
            
            

class MainWindow(QMainWindow, Ui_MainWindow):
    """
    Fenêtre principale de l'application avec l'interface utilisateur.
    Gère le cycle de vie du SerialWorker et du QThread.
    """
    # Signaux pour demander au SerialWorker d'effectuer des actions
    open_port_signal = pyqtSignal(str, int)
    close_port_signal = pyqtSignal()
    start_read_mesures_request = pyqtSignal()
    #pour le timer :
    start_timer_read_signal = pyqtSignal(int) # int = intervalle en ms
    stop_timer_read_signal = pyqtSignal()
    set_default_query_timeout_signal = pyqtSignal(int)
    demande_update_status_leds = pyqtSignal()
    
    
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # --- Configuration du QThread et SerialWorker ---
        self.thread = QThread()
        self.worker = SerialWorker()
        self.worker.moveToThread(self.thread) # IMPORTANT: Déplace le worker vers le nouveau thread
        
        self.console.setReadOnly(True)
        self.entreeCommande.setPlaceholderText("Entrez une commande SCPI (ex: VSET1:5)")
        self.entreeCommande.returnPressed.connect(self.send_custom_command)
              

        #Liason entre les boutons et leurs fonctions
        self.btnOn.clicked.connect(self.info_port_connection)
        self.btnOff.clicked.connect(self.stop_connection)
        self.btnCommencer.clicked.connect(self.TimerStartMesure)
        self.buttonOCP.clicked.connect(self.OCP_mode)
        self.buttonLOCK.clicked.connect(self.LOCK_mode)
        self.indiceOut.clicked.connect(self.Output_mode)

        #Change les pas pour changer les valeurs de l'appareil
        self.ChangeSingleStepVoltage.valueChanged.connect(self.spinVoltage.setSingleStep)
        self.ChangeSingleStepAmpere.valueChanged.connect(self.spinAmpere.setSingleStep)
        
        # Appelle directement la méthode du worker
        self.spinVoltage.valueChanged.connect(self.worker._set_voltage)
        self.spinAmpere.valueChanged.connect(self.worker._set_ampere)
        
        # Bouton UI, pas besoin du Worker Thread
        self.btnReiniGra.clicked.connect(self.reiniGraphique)
        self.btnReiniDonnees.clicked.connect(self.reiniTab)
        self.btnReiniTout.clicked.connect(self.reiniAll)
        
        self.btnEnregistrer.clicked.connect(self.enregTab) #tableau des données
        self.btnEnregistrerGraph.clicked.connect(self.enregGraph) #enregistre graphe
        
        
        #Soucis de répetitions des consol log
        self.worker.table_mesures_ready.connect(self.tableau)
        self.worker.table_mesures_ready.connect(self.updateValue) 
        self.worker.statut.connect(self.updateStatus)
        
        #Création des tableaux
        self.Temps = []
        self.Tension = []
        self.Current=[]
        
        #Variable pour garder la position dans un tableau
        self.savetime = 0
        
        #initialisation du timer
        self.timerMesure = QTimer()
        
        #variable d'aquisition pour servir d'indicateur aux fonctions qui nécessite un signal pour se connecter au timer
        self.aquisition = False
        self.last_data_received = None# jai fais cette variable au cas ou c'était une bonne idee pour stoper toute les infos qui sorte dans l'espace de commande
        
        # Indice de couleur pour les courbes
        self.color = 0
        
        # Liste des couleurs de courbes
        self.tab_couleur = ['b','g','r','c', 'm','y','black']
        self.col = 0
        self.row = 0

        # Couleur du fond du graphe
        self.TabTension.setBackground("w")
        
        # Entête du graphe 
        self.TabTension.setTitle('Graphique des courbes Volts(V) et Amperes(A) / Temps(s)', color ='b')
        
        # Titre de l'axe vertical
        self.TabTension.setLabel('left','Tension (V) et Courant (A)', color ='black')
        
        # Titre de l'axe horizontal
        self.TabTension.setLabel('bottom','Temps (s)', color ='black')
        self.TabTension.showGrid(x = True, y = True, alpha = 0.3)        

        # Connecte les signaux de l'UI au worker
        self.open_port_signal.connect(self.worker._open_port)
        self.close_port_signal.connect(self.worker._close_port)
        self.start_read_mesures_request.connect(self.worker._read_mesures)
        self.demande_update_status_leds.connect(self.worker._status_leds)
        
        self.pasMesures.valueChanged.connect(self.changeTimer)
        
        #les fonctions tampons pour garder en memoir si le message est le même
        
        

        # boutons pour la console et les lignes de commandes :
        self.btn_idn.clicked.connect(self.on_request_idn_clicked)
        self.btn_status.clicked.connect(self.on_request_status_clicked)                   
        self.btn_preset_idn.clicked.connect(self.pre_commande_idn)
        self.btn_preset_get_ampere.clicked.connect(self.pre_commande_outi)
        self.btn_preset_get_voltage.clicked.connect(self.pre_commande_outv)
        self.btn_preset_set_ampere.clicked.connect(self.pre_commande_seti)
        self.btn_preset_set_voltage.clicked.connect(self.pre_commande_setv)
        self.btn_preset_lock.clicked.connect(self.pre_commande_lock)        
        self.btn_preset_ocp.clicked.connect(self.pre_commande_ocp)        
        self.btn_preset_status.clicked.connect(self.pre_commande_status)        
        self.btn_preset_out.clicked.connect(self.pre_commande_out)
        self.envoyerCommandes.clicked.connect(self.envoie_commandes)

        # Connecte les signaux du worker à l'UI
        self.worker.data_received.connect(self.log_data_received) # Pour le logging générique
        self.worker.error_occurred.connect(self.log_error)

        # Démarre le thread (le worker ne fera rien tant qu'il n'est pas appelé via ses slots)
        self.thread.start()
        self.console.append("Application démarrée. Thread worker actif.")
        self.statusbar.showMessage("Application démarrée. Thread worker actif.")
       
        self.info_port_connection() #Je lance automatiquement à l'init la connexion par ce que jtrouve ca nul

    def info_port_connection(self):
        port = self.spinBox_COM.value()
        self.start_connection(port)
        self.console.append("Statut: Connexion en cours...")
        self.statusbar.showMessage("Statut: Connexion en cours...")
        
        
        
    def start_connection(self, va :int):
        """Demande au worker d'ouvrir le port."""
        num_port = va
        self.open_port_signal.emit(f"COM{num_port}", 9600)      

        # Toujours déconnecter avant de (re)connecter pour éviter les connexions multiples
        try:
            self.timerMesure.timeout.disconnect() # Déconnecte TOUS les slots connectés au timeout
               
        except TypeError:
            # Si aucun slot n'était connecté (premier démarrage par ex.), TypeError est levé, on l'ignore.
            pass        
        self.timerMesure.timeout.connect(self.start_read_mesures_request.emit)
        self.timerMesure.start(self.pasMesures.value())
        


    def stop_connection(self):
        """Demande au worker de fermer le port."""
        self.close_port_signal.emit()
        self.console.append("Statut: Deconnexion en cours...")
        self.statusbar.showMessage("Statut: Deconnexion en cours...")
        
        
        #pour arreter le timer a la fin (partri de maniere propre du programme)
        if self.timerMesure.isActive():
            self.timerMesure.stop()
            self.console.append("Arrêt de l'acquisition des mesures.")
        try:
            self.timerMesure.timeout.disconnect(self.start_read_mesures_request.emit)
        except TypeError:
            pass 

    @pyqtSlot(str)
    def log_data_received(self, data):
        #Affiche les données reçues génériques dans la console.  
        self.console.append(f"<span style='color: blue;'>Reçu (générique): {data}</span>")
        

    @pyqtSlot(str)
    def log_error(self, error_message):
        """Affiche les messages d'erreur dans la console."""
        self.console.append(f"<span style='color: red;'>Erreur: {error_message}</span>")

    def send_custom_command(self):
        """Envoie une commande tapée par l'utilisateur."""
        command = self.entreeCommande.text()
        if command:
            self.worker._send_command(command)
            self.console.append(f"<span style='color: green;'>Envoyé: {command}</span>")
            self.entreeCommande.clear()


    def envoie_commandes(self):
        self.send_custom_command()
        

    def on_request_idn_clicked(self):
        if self.worker._is_open:
            self.console.append("Demande d'IDN envoyée (attente de réponse)...")
            # Appel bloquant pour le worker, non pour l'UI
            idn_response = self.worker._request_idn()
            if not idn_response:
                self.console.append("<span style='color: orange;'>Aucune réponse IDN ou timeout.</span>")
        else:
            self.log_error("Port non ouvert pour demander l'IDN.")
            
            
    def on_request_status_clicked(self):
        if self.worker._is_open:
            self.console.append("Demande du statut envoyée (attente de réponse)...")
            # Appel bloquant pour le worker, non pour l'UI
            status_response = self.worker._request_status()
            if not status_response:
                self.console.append("<span style='color: orange;'>Aucune réponse de statut ou timeout.</span>")
            else:
                self.console.append(f"Statut reçu : {status_response}")
        else:
            self.log_error("Port non ouvert pour demander le statut")

    def updateValue(self, data_row_from_worker):
        self.TensionValue, self.CurrentValue = data_row_from_worker
        self.nbRealVoltage.display(self.TensionValue)
        self.nbRealAmpere.display(self.CurrentValue)
        self.demande_update_status_leds.emit()
        
        
    @pyqtSlot(str)
    def updateStatus(self, s): 
        if (s == "\12" or s== "↕" or s==""):
            self.led_ocp.setState(2)
            self.led_cc.setState(1)
            self.led_cv.setState(1)
            self.led_pn.setState(1)
            
        elif (s == "S"):
            self.led_ocp.setState(2)
            self.led_cc.setState(2)
            self.led_cv.setState(0)
            self.led_pn.setState(0)
            
        elif (s=="R"):
            self.led_ocp.setState(0)
            self.led_cc.setState(0)
            self.led_cv.setState(2)
            self.led_pn.setState(0)
            
        elif (s == "2"):
            self.led_ocp.setState(0)
            self.led_cc.setState(1)
            self.led_cv.setState(1)
            self.led_pn.setState(1)
            
        elif (s == "s"):
            self.led_ocp.setState(0)
            self.led_cc.setState(2)
            self.led_cv.setState(0)
            self.led_pn.setState(0)     
            
            
    @pyqtSlot(bool)
    def OCP_mode(self):
        if self.buttonOCP.isChecked():
            self.worker._set_ocp(1)
        else:
            self.worker._set_ocp(0)


    @pyqtSlot(bool)
    def LOCK_mode(self):
        if self.buttonLOCK.isChecked():
            self.worker._set_lock(1)
            self.led_lock.setState(0)
        else:
            self.worker._set_lock(0)          
            self.led_lock.setState(4)
            
            
    @pyqtSlot(bool)
    def Output_mode(self):
        if self.indiceOut.isChecked():
            self.worker._set_output(1)
        else:
            self.worker._set_output(0)
           
    
    def pre_commande_idn(self):
        self.entreeCommande.setText("*IDN?")
        
    def pre_commande_outi(self):
        self.entreeCommande.setText("IOUT1?")
        
    def pre_commande_outv(self):
        self.entreeCommande.setText("VOUT1?")
        
    def pre_commande_seti(self):
        self.entreeCommande.setText("ISET1:'valeurs'")
        
    def pre_commande_setv(self):
        self.entreeCommande.setText("VSET1:'valeurs'")

    def pre_commande_lock(self):
        self.entreeCommande.setText("LOCK'Allumer = 1 Eteint = 0'")

    def pre_commande_ocp(self):
        self.entreeCommande.setText("OCP'Allumer = 1 Eteint = 0'")

    def pre_commande_status(self):
        self.entreeCommande.setText("STATUS?")

    def pre_commande_out(self):
        self.entreeCommande.setText("OUT'Allumer = 1 Eteint = 0'")  

         
    def resdonnees(self):
        self.Temps, self.Tension, self.Current=[],[],[]
        
        
    def TimerStop(self):
        self.timerMesure.stop()
        # IMPORTANT : Déconnectez le signal pour éviter des connexions multiples
        try:
            self.timerMesure.timeout.disconnect(self.start_read_mesures_request.emit)
        except TypeError:
            # Ignore l'erreur si le signal n'était pas connecté
            pass
        
        
    def changeTimer(self, valeur):
        self.timerMesure.stop()
        self.timerMesure.start(valeur)

 
    def tableau(self, data_row_from_worker):   
        if self.aquisition is False:
            return
        else:
            acquisition_interval_s = self.pasMesures.value() / 1000.0
            if len(self.Temps) > 0:
                self.Temps.append(self.Temps[-1] + acquisition_interval_s)
            elif self.savetime :
                self.Temps.append(self.savetime + acquisition_interval_s)
            
            else:
                self.Temps.append(0)
                     
            # Si on est en mode simu, on ajoute des points aléatoires
            if(self.checkBoxSimu.isChecked()):
                self.TensionValue = (random.uniform(0, 2) + 29)
                self.CurrentValue = (random.uniform(0, 2) + 4)
            
            else:                     
            # Récuperation des tableaux :            
                self.TensionValue, self.CurrentValue = data_row_from_worker
            
            self.Tension.append(self.TensionValue)
            self.Current.append(self.CurrentValue)
                
            # Affichage de la courbe
            self.TabTension.plot(self.Temps, self.Tension, symbolBrush=(self.tab_couleur[0]))
            self.TabTension.plot(self.Temps, self.Current, symbolBrush=(self.tab_couleur[1]))
            self.TabTension.show()
            row = self.Donnees.rowCount()
            if self.row >= row:
                self.Donnees.insertRow(row)
            self.Donnees.setItem(row, self.col, 
                                 QTableWidgetItem("{:.2f}".format(self.Temps[-1])))
            self.Donnees.setItem(self.row,self.col+1,
                                  QTableWidgetItem("{:.2f}".format(self.TensionValue)))
            self.Donnees.setItem(self.row,self.col+2,
                                  QTableWidgetItem("{:.2f}".format(self.CurrentValue)))
            self.row += 1     
            
            self.Donnees.scrollToBottom()
            self.btnReiniDonnees.setEnabled(True)
            self.btnEnregistrer.setEnabled(True)
            self.btnEnregistrerGraph.setEnabled(True)
            self.btnReiniTout.setEnabled(True)
            self.btnReiniGra.setEnabled(True)

    def TimerStartMesure(self):
        if self.btnCommencer.text() != "Pause":
            if self.btnCommencer.text() == "Commencer l'enregistrement":
                self.console.append("Début de l'enregistrement des mesures")
                self.btnCommencer.setText('Pause')
                self.aquisition = True

            elif self.btnCommencer.text() == "Continuer":
                self.console.append("Reprise des mesures")
                self.btnCommencer.setText('Pause')
                self.aquisition = True

        elif self.btnCommencer.text() == "Pause":
            self.console.append("Pause, les mesures sont stopées")
            self.btnCommencer.setText('Continuer')
            self.aquisition = False


    def reiniTab(self):
        self.resdonnees()
        while self.Donnees.rowCount() > 0:
            self.Donnees.removeRow(0)
        while self.Donnees.columnCount() > 3:
            self.Donnees.removeColumn(0)            
        self.row = 0
        
        
    def reiniGraphique(self):
        self.savetime = self.Temps[-1]
        self.resdonnees()
        self.TabTension.clear()

             
    def reiniAll(self):    
        self.aquisition = False
        self.resdonnees()
        self.reiniTab()
        self.TabTension.clear() # ne pas mettre directement self.reiniGraphique() car on souhaite repartire de 0   mais ca marchr pas epiaenhpefoiefhoihioae  
        self.btnReiniDonnees.setEnabled(False)
        self.btnEnregistrer.setEnabled(False)
        self.btnEnregistrerGraph.setEnabled(False)
        self.btnReiniTout.setEnabled(False)
        self.btnReiniGra.setEnabled(False)
        self.btnCommencer.setText("Commencer l'enregistrement")
        self.console.append("Reinitialisation, les mesures sont stopées")
    
    def enregTab(self):
        """
        Pour choisir un dossier d'enregistrement   "test de commit"
        dir_name = QFileDialog.getExistingDirectory()
        print(dir_name)
        """
        # Génère un nom de fichier par défaut avec la date et l'heure actuelles
        default_file_name = "data_" + QDateTime.currentDateTime().toString("yyyy-MM-dd_hh.mm.ss")

       # Ouvre la boîte de dialogue d'enregistrement de fichier
       # Propose des filtres pour les fichiers texte et CSV
        file_path, selected_filter = QFileDialog.getSaveFileName(
           self, 'Sauvegarder les données', default_file_name,
           'Fichier CSV (*.csv);;Fichier texte (*.txt);;Tous les fichiers (*)')

       # Si l'utilisateur annule la boîte de dialogue (aucune sélection de chemin)
        if not file_path:
           self.console.append("<b style='color:red'>Enregistrement annulé</b><br>")
           return

       # Détermine le séparateur en fonction du filtre sélectionné ou de l'extension du fichier
       # Le séparateur par défaut est la virgule pour CSV, l'espace pour TXT
        separator = "," if selected_filter == 'Fichier CSV (*.csv)' or file_path.lower().endswith('.csv') else " "

       # --- Partie 1 : Enregistrement des listes self.Temps, self.Tension, self.Current ---
        try:
            with open(file_path, "w") as file:
               # Écrit les en-têtes de colonnes
                if separator == ",":
                   file.write("Temps,Tension,Courant\n")
                else:
                   file.write("Temps Tension Courant\n")

               # Écrit chaque ligne de données
                for x, y, z in zip(self.Temps, self.Tension, self.Current):
                   file.write(f"{x}{separator}{y}{separator}{z}\n")

           # Affiche un message de succès dans le widget self.console
            path_obj = pathlib.Path(file_path)
            self.console.append(f"<b style='color:green'>{path_obj.name}</b> : Enregistrement de {len(self.Temps)} points fait.<br>")

        except Exception as e:
           # Affiche un message d'erreur si l'enregistrement échoue
           self.console.appen(f"<b style='color:red'>Erreur lors de l'enregistrement des données principales : {e}</b><br>")
           return # Arrête la fonction si l'enregistrement principal échoue
       
        
    def enregGraph(self):
            """Enregistre le graphique actuel dans un fichier."""
            # Ouvrir une boîte de dialogue pour choisir le nom et le format du fichier
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Enregistrer le graphique",
                "", # Répertoire par défaut
                "Images PNG (*.png);;Images JPG (*.jpg);;Fichiers SVG (*.svg);;Tous les fichiers (*.*)"
            )
    
            if file_name: # Si l'utilisateur a sélectionné un fichier
                exporter = pg.exporters.ImageExporter(self.TabTension.plotItem)
    
                # Définir la résolution (optionnel, mais utile pour la qualité)
                # exporter.parameters()['width'] = 800 # Largeur en pixels
                # exporter.parameters()['height'] = 600 # Hauteur en pixels
    
                # Exporter vers le fichier
                exporter.export(file_name)
                self.console.append(f"<span style='color: green;'>Graphique enregistré sous : {file_name}</span>")
            else:
                self.console.append("<span style='color: orange;'>Enregistrement du graphique annulé.</span>")
    

    def ChangeMode(self, checkState):
        info_spinbox = (checkState == Qt.Checked)
        if info_spinbox:
            self.pasMesures.setMinimum(10)
        else:
            self.pasMesures.setMinimum(500)
        # Informer le worker du changement de modepour le timer de mesure
        if self.serial_worker._mesure_timer.isActive():
            self.start_mesure_timer_request.emit(self.pasMesures.value(), info_spinbox)
            
            
    def closeEvent(self, event):
        """Gère la fermeture de la fenêtre pour arrêter le thread proprement."""
        self.stop_connection() # Demande au worker de fermer le port
        self.thread.quit()     # Demande au thread de quitter sa boucle d'événements
        self.thread.wait(3000) # Attendre que le thread se termine (max 3 secondes)
        if self.thread.isRunning():
            self.thread.terminate() # Forcer l'arrêt si le thread ne répond pas
            self.console.append("<span style='color: orange;'>Le thread a dû être terminé de force.</span>")
        event.accept() # Accepter l'événement de fermeture de la fenêtre


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.showMaximized()
    sys.exit(app.exec_())
    
    