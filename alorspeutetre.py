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

import random
import pathlib
from math import log
import time

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
    # Signal interne pour les requêtes, utilisé par la fonction query
    _query_response_received = pyqtSignal(str)
    
    table_mesures_ready = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self._serial_port = QSerialPort()
        self._serial_port.readyRead.connect(self._read_data)
        self._write_request.connect(self._write_data)
        self._is_open = False
        # Variables pour la fonction query
        self._query_data_buffer = ""
        self._query_waiting_for_response = False
        self._query_event_loop = None
        self._query_timeout_timer = QTimer(self)
        self._query_timeout_timer.setSingleShot(True)
        self._query_timeout_timer.timeout.connect(self._on_query_timeout)
        self.query("IOUT1?")
    @pyqtSlot(str, int)
    def open_port(self, port_name, baud_rate):
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
            
        else:
            self._is_open = False
            error_msg = self._serial_port.errorString()
            self.port_status.emit(False, f"Erreur d'ouverture de '{port_name}': {error_msg}")
            self.error_occurred.emit(error_msg)

    @pyqtSlot()
    def close_port(self):
        """Ferme le port série."""
        if self._serial_port.isOpen():
            self._serial_port.close()
            self._is_open = False
            self.port_status.emit(False, "Port série fermé.")
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
                if decoded_data:
                    self.data_received.emit(decoded_data) # Émet pour la console générale

                    # Si une query est en attente, capturer cette réponse
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

    # --- Méthode principale de requête ---
    @pyqtSlot(str, int, result=str)
    def query(self, command_string, timeout_ms=1000): # Augmenté le timeout par défaut
        """
        Envoie une commande à l'appareil et attend une réponse.
        Bloque le thread du SerialWorker pendant l'attente (pas l'UI).
        """
        if not self._is_open:
            self.error_occurred.emit("Impossible d'effectuer la requête: le port n'est pas ouvert.")
            return ""

        if self._query_waiting_for_response:
            self.error_occurred.emit("Une autre requête est déjà en attente de réponse. Veuillez patienter.")
            return "" # Évite d'empiler les requêtes

        self._query_waiting_for_response = True
        self._query_data_buffer = "" # Réinitialise le buffer pour la nouvelle requête

        # Envoie la commande
        self._write_request.emit((command_string + "\n").encode('ascii'))

        # Crée et exécute une boucle d'événements pour attendre la réponse
        self._query_event_loop = QEventLoop()
        self._query_timeout_timer.start(timeout_ms)
        self._query_event_loop.exec_() # Bloque le thread du worker ici

        # Nettoyage après la fin de la boucle (timeout ou réponse reçue)
        self._query_event_loop = None # Libère la référence à la boucle

        return self._query_data_buffer # Retourne ce qui a été stocké dans le buffer

    # --- Méthodes publiques pour envoyer des commandes (appelées depuis l'UI) ---
    # Ces méthodes utilisent maintenant la fonction query si elles attendent une réponse.
    # Elles sont désormais appelées depuis la MainWindow via self.worker.methode()

    def send_command(self, command_string):
        """Envoie une commande textuelle sans attendre de réponse immédiate."""
        self._write_request.emit((command_string + "\n").encode('ascii'))

    def request_idn(self):
        """Demande l'identification de l'appareil et renvoie la réponse."""
        return self.query("*IDN?")

    def set_voltage(self, voltage):
        """Définit la tension de sortie de l'alimentation."""
        # Pas besoin de query ici car pas de réponse attendue immédiatement
        self.send_command(f"VSET1:{voltage}")

    def get_voltage(self):
        #Demande la tension de sortie actuelle et renvoie la valeur.
        # try:
        responsev = float(self.query("VOUT1?"))
        return responsev
        # except ValueError:
        #     self.error_occurred.emit(f"Format de réponse inattendu: '{responsev}'")
        #     return float('nan') # Not a Number
        # except Exception as a:
        #     self.error_occurred.emit(f"Impossible de parser la tension de: '{responsev}'")
        #     return float('nan')


    def set_ampere(self, ampere):
        """Définit la tension de sortie de l'alimentation."""
        # Pas besoin de query ici car pas de réponse attendue immédiatement
        self.send_command(f"ISET1:{ampere}")

    def get_current(self):
        #Demande le courant de sortie actuel et renvoie la valeur.
        # try:
        responsec = float(self.query('IOUT1?'))
        return responsec
        # except ValueError:
        #         self.error_occurred.emit(f"Format de réponse inattendu: '{responsec}'")
        #         return float('nan')
        # except Exception as a:
        #     self.error_occurred.emit(f"Impossible de parser le courant de: '{responsec}'")
        #     return float('nan')

    def set_output(self, state):
        """Active (1) ou désactive (0) la sortie de l'alimentation."""
        self.send_command(f"OUT{int(state)}")
        
    @pyqtSlot()
    def _read_mesures(self):
        if not self._is_open:
            self.error_occurred.emit("Port non ouvert pour la lecture des données.")
            return
        
        TensionValue = self.get_voltage() # Appelle votre méthode get_voltage qui utilise query
        CurrentValue = self.get_current() # Appelle votre méthode get_current qui utilise query
        
        self.table_mesures_ready.emit([TensionValue, CurrentValue])
        
        

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

        self.btnOn.clicked.connect(self.start_connection)
        self.btnOff.clicked.connect(self.stop_connection)
        self.btnCommencer.clicked.connect(self.TimerStartMesure)
        self.btn_idn.clicked.connect(self._on_request_idn_clicked)

        # Appelle directement la méthode du worker
        self.spinVoltage.valueChanged.connect(self.worker.set_voltage)
        self.spinAmpere.valueChanged.connect(self.worker.set_ampere)

        self.btnReiniGra.clicked.connect(self.reiniGraphique)
        self.btnReini.clicked.connect(self.reiniTab)
        self.btnEnregistrer.clicked.connect(self.enregTab)
        # self.btn_get_voltage = QPushButton("Obtenir Tension Actuelle")
        # # Connecte à une nouvelle méthode dans MainWindow pour gérer la réponse
        # self.btn_get_voltage.clicked.connect(self._on_get_voltage_clicked)
        # self.btn_get_voltage.setEnabled(False)
        # btn_layout.addWidget(self.btn_get_voltage)

        # self.btn_get_current = QPushButton("Obtenir Courant Actuel")
        # # Connecte à une nouvelle méthode dans MainWindow pour gérer la réponse
        # self.btn_get_current.clicked.connect(self._on_get_current_clicked)
        # self.btn_get_current.setEnabled(False)
        # btn_layout.addWidget(self.btn_get_current)

        # self.btn_output_on = QPushButton("Sortie ON")
        # # Appelle directement la méthode du worker
        # self.btn_output_on.clicked.connect(lambda: self.worker.set_output(1))
        # self.btn_output_on.setEnabled(False)
        # btn_layout.addWidget(self.btn_output_on)

        # self.btn_output_off = QPushButton("Sortie OFF")
        # # Appelle directement la méthode du worker
        # self.btn_output_off.clicked.connect(lambda: self.worker.set_output(0))
        # self.btn_output_off.setEnabled(False)
        # btn_layout.addWidget(self.btn_output_off)

        # layout.addLayout(btn_layout)
        
        self.worker.table_mesures_ready.connect(self.tableau)
        
        # tableau graphe, je pense qu'il faut les déclarés que une fois mais jsp où et comment...
        self.Temps = []
        self.Tension = []
        self.Current=[]
        
        self.timerMesure = QTimer()

        
        
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


        # Connecte les signaux de l'UI au worker
        self.open_port_signal.connect(self.worker.open_port)
        self.close_port_signal.connect(self.worker.close_port)
        self.start_read_mesures_request.connect(self.worker._read_mesures)
        #timer : 
        # self.start_timer_read_signal.connect(self.worker._data_read_timer.start) # Nécessite que le timer soit dans le worker
        # self.stop_timer_read_signal.connect(self.worker._data_read_timer.stop)

        # Connecte les signaux du worker à l'UI
        self.worker.data_received.connect(self.log_data_received) # Pour le logging générique
        self.worker.error_occurred.connect(self.log_error)

        # Démarre le thread (le worker ne fera rien tant qu'il n'est pas appelé via ses slots)
        self.thread.start()
        self.console.append("Application démarrée. Thread worker actif.")

    def start_connection(self):
        """Demande au worker d'ouvrir le port."""
        self.open_port_signal.emit("COM3", 9600) # Adaptez le port et baud rate
        self.console.append("Statut: Connexion en cours...")



    def stop_connection(self):
        """Demande au worker de fermer le port."""
        self.close_port_signal.emit()
        self.console.append("Statut: Deconnexion en cours...")


    @pyqtSlot(str)
    def log_data_received(self, data):
        """Affiche les données reçues génériques dans la console."""
        self.console.append(f"<span style='color: blue;'>Reçu (générique): {data}</span>")

    @pyqtSlot(str)
    def log_error(self, error_message):
        """Affiche les messages d'erreur dans la console."""
        self.console.append(f"<span style='color: red;'>Erreur: {error_message}</span>")

    def send_custom_command(self):
        """Envoie une commande tapée par l'utilisateur."""
        command = self.entreeCommande.text()
        if command:
            self.worker.send_command(command)
            self.console.append(f"<span style='color: green;'>Envoyé: {command}</span>")
            self.entreeCommande.clear()

    # --- Nouvelles méthodes pour gérer les réponses des requêtes (appelant worker.query) ---
    def _on_request_idn_clicked(self):
        """Gère le clic sur le bouton IDN et affiche la réponse."""
        if self.worker._is_open:
            self.console.append("Demande d'IDN envoyée (attente de réponse)...")
            # Appel bloquant pour le worker, non pour l'UI
            idn_response = self.worker.request_idn()
            if idn_response:
                self.console.append(f"<span style='color: darkgreen;'>IDN de l'appareil: {idn_response}</span>")
            else:
                self.console.append("<span style='color: orange;'>Aucune réponse IDN ou timeout.</span>")
        else:
            self.log_error("Port non ouvert pour demander l'IDN.")


    def closeEvent(self, event):
        """Gère la fermeture de la fenêtre pour arrêter le thread proprement."""
        self.stop_connection() # Demande au worker de fermer le port
        self.thread.quit()     # Demande au thread de quitter sa boucle d'événements
        self.thread.wait(3000) # Attendre que le thread se termine (max 3 secondes)
        if self.thread.isRunning():
            self.thread.terminate() # Forcer l'arrêt si le thread ne répond pas
            self.console.append("<span style='color: orange;'>Le thread a dû être terminé de force.</span>")
        event.accept() # Accepter l'événement de fermeture de la fenêtre


        
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
    
            
 
    def tableau(self, data_row_from_worker):   
        # Génération de l'axe X 
        # if len(self.Temps) > 0 and self.row > 0:
        #     # Si le point 0 existe, on créé le nouveau point en ajoutant le
        #     # point précédent à la valeur de la vitesse d'acquisition
        #     self.Temps.append(self.Temps[-1] + self.spinBox.value()/1000.0)
        acquisition_interval_s = self.spinBox.value() / 1000.0
        if len(self.Temps) > 0:
            self.Temps.append(self.Temps[-1] + acquisition_interval_s)
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
        #if self.row >= row:
        #    self.Donnees.insertRow(row)
        self.Donnees.insertRow(row)
        self.Donnees.setItem(row, self.col, 
                             QTableWidgetItem("{:.2f}".format(self.Temps[-1])))
        self.Donnees.setItem(self.row,self.col+1,
                              QTableWidgetItem("{:.2f}".format(self.TensionValue)))
        self.Donnees.setItem(self.row,self.col+2,
                              QTableWidgetItem("{:.2f}".format(self.CurrentValue)))
        self.row += 1     
        
        self.Donnees.scrollToBottom()

    def TimerStartMesure(self):
        
        if self.btnCommencer.text() != "Pause":
            if self.btnCommencer.text() == "Commencer l'enregistrement":
                self.console.append("Début de l'enregistrement des mesures")
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
                self.timerMesure.timeout.connect(self.start_read_mesures_request.emit) 
                self.timerMesure.start(self.spinBox.value())
                # if(self.checkBoxSimu.isChecked()):
                #     self.spinBox.value()                
                # else:
                #     self.spinBox.value()                   
                
            elif self.btnCommencer.text() == "Continuer":
                self.console.append("Reprise des mesures")
                self.btnCommencer.setText('Pause')
                self.timerMesure.timeout.connect(self.start_read_mesures_request.emit)
                self.timerMesure.start(self.spinBox.value())
            
        elif self.btnCommencer.text() == "Pause":
            self.console.append("Pause, les mesures sont stopées")
            self.TimerStop()
            self.btnCommencer.setText('Continuer')    


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
        self.TabTension.clear()
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
                file.write("{} {} {}\n".format(x, y, z))
        path = pathlib.Path(file_name)
        self.Data.appendHtml(path.name +
                      ' : Enregistrement de {} points fait\n'.format(
                          len(self.Temps)))
        
        
        if not file_name:
            self.Data.appendHtml("<b style='color:red'>Enregistrement annulé</b><br>")
            return
        

        # selected = self.Donnees.selectedRanges()
        # if len(selected) > 0:
        #     texte = "","",""
        #     ligne = ""
        #     with open(file_name+"Selected.txt", "w") as file:
        #         for i in range(selected[0].topRow(), selected[0].bottomRow() + 1):
        #             for j in range(selected[0].leftColumn(), selected[0].rightColumn() + 1):
        #                 if self.Donnees.item(i, j) != None:
        #                     texte += self.Donnees.item(i, j).text() + "\t"
        #                     ligne += self.Donnees.item(i, j).text() + "\t"
        #                 else:
        #                     # Sur les colonnes de temps, on ajoute le temps
        #                     if j%2==0:
        #                         texte += str(i*(float(self.Donnees.item(1, j).text())-float(self.Donnees.item(0, j).text())))+"\t"
        #                         ligne += str(i*(float(self.Donnees.item(1, j).text())-float(self.Donnees.item(0, j).text())))+"\t"
        #                     else:
        #                         texte += "0\t"
        #                         ligne += "0\t"
                                
        #             texte = texte[:-1] + "\n"  # le [:-1] élimine le '\t' en trop
        #             file.write(ligne[:-1] + "\n")
        #             ligne = ""
        #         QApplication.clipboard().setText(texte)





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

            # Affiche un message de succès dans le widget self.Data
            path_obj = pathlib.Path(file_path)
            self.Data.appendHtml(f"<b style='color:green'>{path_obj.name}</b> : Enregistrement de {len(self.Temps)} points fait.<br>")

        except Exception as e:
            # Affiche un message d'erreur si l'enregistrement échoue
            self.Data.appendHtml(f"<b style='color:red'>Erreur lors de l'enregistrement des données principales : {e}</b><br>")
            return # Arrête la fonction si l'enregistrement principal échoue
        
    def ChangeMode(self, checkState):
        info_spinbox = (checkState == Qt.Checked)
        if info_spinbox:
            self.spinBox.setMinimum(10)
        else:
            self.spinBox.setMinimum(500)
        # Informer le worker du changement de modepour le timer de mesure
        if self.serial_worker._mesure_timer.isActive():
            self.start_mesure_timer_request.emit(self.spinBox.value(), info_spinbox)
            

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())