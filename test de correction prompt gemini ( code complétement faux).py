# -*- coding: utf-8 -*-
"""
Created on Wed Jun 25 14:39:52 2025

@author: gaspard.guidetti
"""

# -*- coding: utf-8 -*-

import sys
import serial
import serial.tools.list_ports # Nécessaire pour lister les ports COM
import numpy as np
import time
import random
import pathlib

# Import de la partie graphique dessinée dans designer (assumé existant)
# from alimlabo import Ui_MainWindow
# from classesecond import PyLedLabel

# Dummy classes for demonstration if alimlabo and classesecond are not available
# You should replace these with your actual imports if running in your environment
class Ui_MainWindow:
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        # Add a basic layout and widgets for testing
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")

        self.port_combo = QtWidgets.QComboBox(self.centralwidget)
        self.port_combo.setObjectName("port_combo")
        self.verticalLayout.addWidget(self.port_combo)

        self.baud_combo = QtWidgets.QComboBox(self.centralwidget)
        self.baud_combo.setObjectName("baud_combo")
        self.verticalLayout.addWidget(self.baud_combo)

        self.open_port_btn = QtWidgets.QPushButton(self.centralwidget)
        self.open_port_btn.setObjectName("open_port_btn")
        self.open_port_btn.setText("Open Port")
        self.verticalLayout.addWidget(self.open_port_btn)

        self.close_port_btn = QtWidgets.QPushButton(self.centralwidget)
        self.close_port_btn.setObjectName("close_port_btn")
        self.close_port_btn.setText("Close Port")
        self.verticalLayout.addWidget(self.close_port_btn)
        self.close_port_btn.setEnabled(False)

        self.send_data_input = QtWidgets.QLineEdit(self.centralwidget)
        self.send_data_input.setObjectName("send_data_input")
        self.send_data_input.setPlaceholderText("Data to send")
        self.verticalLayout.addWidget(self.send_data_input)

        self.send_data_btn = QtWidgets.QPushButton(self.centralwidget)
        self.send_data_btn.setObjectName("send_data_btn")
        self.send_data_btn.setText("Send Data")
        self.verticalLayout.addWidget(self.send_data_btn)
        self.send_data_btn.setEnabled(False)

        self.data_display = QtWidgets.QTextEdit(self.centralwidget)
        self.data_display.setObjectName("data_display")
        self.verticalLayout.addWidget(self.data_display)

        # Assuming you have a QDial for Voltage and Ampere
        self.dialVoltage = QtWidgets.QDial(self.centralwidget)
        self.dialVoltage.setObjectName("dialVoltage")
        self.dialVoltage.setRange(0, 30) # Example range
        self.verticalLayout.addWidget(self.dialVoltage)
        self.labelVoltage = QtWidgets.QLabel("Voltage: 0V", self.centralwidget)
        self.verticalLayout.addWidget(self.labelVoltage)

        self.dialAmpere = QtWidgets.QDial(self.centralwidget)
        self.dialAmpere.setObjectName("dialAmpere")
        self.dialAmpere.setRange(0, 5) # Example range
        self.verticalLayout.addWidget(self.dialAmpere)
        self.labelAmpere = QtWidgets.QLabel("Current: 0A", self.centralwidget)
        self.verticalLayout.addWidget(self.labelAmpere)

        self.buttonLOCK = QtWidgets.QPushButton(self.centralwidget)
        self.buttonLOCK.setObjectName("buttonLOCK")
        self.buttonLOCK.setText("LOCK Panel")
        self.buttonLOCK.setCheckable(True)
        self.verticalLayout.addWidget(self.buttonLOCK)

        self.buttonOCP = QtWidgets.QPushButton(self.centralwidget)
        self.buttonOCP.setObjectName("buttonOCP")
        self.buttonOCP.setText("OCP On/Off")
        self.buttonOCP.setCheckable(True)
        self.verticalLayout.addWidget(self.buttonOCP)

        self.btnCommencer = QtWidgets.QPushButton(self.centralwidget)
        self.btnCommencer.setObjectName("btnCommencer")
        self.btnCommencer.setText("Commencer l'enregistrement")
        self.verticalLayout.addWidget(self.btnCommencer)

        self.spinBox = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBox.setObjectName("spinBox")
        self.spinBox.setRange(10, 5000) # Example range for interval
        self.spinBox.setValue(100)
        self.verticalLayout.addWidget(self.spinBox)

        self.checkBoxSimu = QtWidgets.QCheckBox("Simulation Mode", self.centralwidget)
        self.checkBoxSimu.setObjectName("checkBoxSimu")
        self.verticalLayout.addWidget(self.checkBoxSimu)

        self.TabTension = PlotWidget(self.centralwidget) # Placeholder for pyqtgraph PlotWidget
        self.TabTension.setObjectName("TabTension")
        self.verticalLayout.addWidget(self.TabTension)

        self.Donnees = QtWidgets.QTableWidget(self.centralwidget)
        self.Donnees.setObjectName("Donnees")
        self.Donnees.setColumnCount(3)
        self.Donnees.setHorizontalHeaderLabels(['Temps (s)', 'Tension (V)', 'Courant (A)'])
        self.verticalLayout.addWidget(self.Donnees)

        self.btnReini = QtWidgets.QPushButton(self.centralwidget)
        self.btnReini.setObjectName("btnReini")
        self.btnReini.setText("Réinitialiser Tableau")
        self.verticalLayout.addWidget(self.btnReini)

        self.btnEnregistrer = QtWidgets.QPushButton(self.centralwidget)
        self.btnEnregistrer.setObjectName("btnEnregistrer")
        self.btnEnregistrer.setText("Enregistrer Tableau")
        self.verticalLayout.addWidget(self.btnEnregistrer)

        self.btnReiniGra = QtWidgets.QPushButton(self.centralwidget)
        self.btnReiniGra.setObjectName("btnReiniGra")
        self.btnReiniGra.setText("Réinitialiser Graphique")
        self.verticalLayout.addWidget(self.btnReiniGra)

        self.btnOnoff = QtWidgets.QPushButton(self.centralwidget)
        self.btnOnoff.setObjectName("btnOnoff")
        self.btnOnoff.setText("Power On/Off")
        self.verticalLayout.addWidget(self.btnOnoff)

        self.actionQuitter = QtWidgets.QAction("Quitter", MainWindow)
        self.actionQuitter.setObjectName("actionQuitter")
        # Assuming a menu bar is present and actionQuitter is added to it
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuFile.setTitle("File")
        self.menuFile.addAction(self.actionQuitter)
        MainWindow.setMenuBar(self.menubar)
        self.menubar.addAction(self.menuFile.menuAction())

        # Dummy LedLabels for now
        self.led_ocp = PyLedLabel(self.centralwidget)
        self.led_lock = PyLedLabel(self.centralwidget)
        self.led_cv = PyLedLabel(self.centralwidget)
        self.led_cc = PyLedLabel(self.centralwidget)
        self.led_pp = PyLedLabel(self.centralwidget)
        self.led_pn = PyLedLabel(self.centralwidget)
        self.led_pgdn = PyLedLabel(self.centralwidget)

        self.data_display = QtWidgets.QTextEdit(self.centralwidget)
        self.verticalLayout.addWidget(self.data_display)

        MainWindow.setCentralWidget(self.centralwidget)
        # Create a status bar
        self.statusBar = QtWidgets.QStatusBar(MainWindow)
        self.statusBar.setObjectName("statusBar")
        MainWindow.setStatusBar(self.statusBar)

class PyLedLabel(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = 0 # Example states
        self.setFixedSize(20, 20)
        self.setStyleSheet("background-color: lightgray; border-radius: 10px;")

    def setState(self, state):
        self._state = state
        if state == 0: # On
            self.setStyleSheet("background-color: green; border-radius: 10px;")
        elif state == 1: # Off
            self.setStyleSheet("background-color: red; border-radius: 10px;")
        elif state == 2: # Flashing
            self.setStyleSheet("background-color: yellow; border-radius: 10px;")
        else: # Default
            self.setStyleSheet("background-color: lightgray; border-radius: 10px;")

# Dummy PlotWidget for pyqtgraph if not installed
try:
    from pyqtgraph import PlotWidget
except ImportError:
    print("PyQtGraph not found. Using a dummy QLabel for plot area.")
    class PlotWidget(QtWidgets.QLabel):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setAlignment(Qt.AlignCenter)
            self.setText("PyQtGraph Plot Area (Install pyqtgraph to see plots)")
            self.setStyleSheet("border: 1px solid black;")
            self._data = {'x': [], 'y1': [], 'y2': []} # Dummy data storage
            self._curves = {} # To simulate curves

        def setBackground(self, color):
            self.setStyleSheet(f"background-color: {color}; border: 1px solid black;")

        def setTitle(self, title, color='b'):
            self.setText(f"{title}\n(Install pyqtgraph to see plots)")

        def setLabel(self, axis, text, color='black'):
            pass # Dummy

        def showGrid(self, x=True, y=True, alpha=0.3):
            pass # Dummy

        def plot(self, x, y, symbolBrush=None):
            # In a real scenario, this would draw the plot
            self._data['x'] = x
            self._data['y1'] = y # Assume y is for Tension for now
            # To show multiple curves, you'd need more sophisticated dummy logic
            self.setText(f"Plotting {len(x)} points (Install pyqtgraph)")

        def clear(self):
            self._data = {'x': [], 'y1': [], 'y2': []}
            # Also clear individual curves if they existed in a real plot
            self.setText("PyQtGraph Plot Area (Cleared)")
            self.update() # Force repaint for QLabel

        def removeItem(self, item):
            pass # Dummy

# Import des widgets utilisés
from PyQt5 import QtWidgets # Add this for dummy UI classes
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow, QMessageBox, QFileDialog, QTableWidgetItem)
# Import des bibliothèques QtCore
from PyQt5.QtCore import QTimer, QFileInfo, Qt, QDateTime, QThread, pyqtSignal, QObject, QIODevice
from PyQt5.QtGui import QIcon

# Import des bibliothèques QtSerialPort
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo


# La classe SerialWorker doit gérer toutes les interactions avec le port série
# et ne doit PAS contenir de références ou d'accès direct à l'interface utilisateur.
class SerialWorker(QObject):
    # Signaux pour envoyer des données et des événements au thread principal (UI)
    data_received = pyqtSignal(bytes)
    port_opened = pyqtSignal(bool, str) # bool success, str message
    port_closed = pyqtSignal()
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal() # Signal émis quand le worker est prêt à être détruit

    mesures_data_ready = pyqtSignal(list, list, list) # Pour Temps, Tension, Courant

    def __init__(self):
        super().__init__()
        self._serial_port = QSerialPort()
        # Connecter le signal errorOccurred pour la gestion des erreurs
        self._serial_port.errorOccurred.connect(self._handle_serial_error)
        # readyRead est pour la réception de données non sollicitées
        self._serial_port.readyRead.connect(self._read_data_async)

        self._is_open = False
        self._mesure_timer = QTimer(self) # Le timer doit appartenir à ce thread
        self._mesure_timer.timeout.connect(self._read_mesure_data) # Connecter le timeout

        self.Temps = []
        self.Tension = []
        self.Current = []

        self._simulation_mode = False # Attribut pour le mode simulation

    # SLOT: pour ouvrir le port série, appelé depuis le thread principal
    @pyqtSlot(str, int)
    def open_port(self, port_name, baud_rate):
        if self._serial_port.isOpen():
            # Si le port est déjà ouvert, le fermer avant de tenter de l'ouvrir à nouveau
            self._serial_port.close()

        self._serial_port.setPortName(port_name)
        self._serial_port.setBaudRate(baud_rate)
        self._serial_port.setDataBits(QSerialPort.Data8)
        self._serial_port.setParity(QSerialPort.NoParity)
        self._serial_port.setStopBits(QSerialPort.OneStop)
        self._serial_port.setFlowControl(QSerialPort.NoFlowControl)

        if self._serial_port.open(QIODevice.ReadWrite):
            self._is_open = True
            self.port_opened.emit(True, f"Port {port_name} ouvert à {baud_rate} bauds.")
            print(f"SerialWorker: Port {port_name} ouvert.")
        else:
            self._is_open = False
            error_msg = self._serial_port.errorString()
            self.port_opened.emit(False, f"Erreur d'ouverture du port {port_name}: {error_msg}")
            self.error_occurred.emit(f"Erreur QSerialPort: {error_msg}")
            print(f"SerialWorker: Erreur d'ouverture: {error_msg}")

    # SLOT: pour fermer le port série, appelé depuis le thread principal
    @pyqtSlot()
    def close_port(self):
        if self._serial_port.isOpen():
            self._mesure_timer.stop() # Arrêter le timer de mesure si le port est fermé
            self._serial_port.close()
            self._is_open = False
            self.port_closed.emit()
            print("SerialWorker: Port fermé.")
        self.finished.emit() # Le worker a terminé sa tâche

    # SLOT: pour écrire des données sur le port série, appelé depuis le thread principal
    @pyqtSlot(bytes)
    def write_data(self, data):
        if self._is_open:
            bytes_written = self._serial_port.write(data)
            if bytes_written == -1:
                self.error_occurred.emit(f"Erreur d'écriture sur le port: {self._serial_port.errorString()}")
                print(f"SerialWorker: Erreur écriture: {self._serial_port.errorString()}")
            else:
                print(f"SerialWorker: Écrit {bytes_written} octets: {data.hex()}")
        else:
            self.error_occurred.emit("Impossible d'écrire: le port n'est pas ouvert.")
            print("SerialWorker: Tentative d'écriture sur port fermé.")

    # Gère les données reçues de manière asynchrone (via readyRead)
    def _read_data_async(self):
        while self._serial_port.bytesAvailable():
            data = self._serial_port.readAll().data()
            self.data_received.emit(data)
            # print(f"SerialWorker: Données brutes reçues (async): {data.hex()}")

    # Méthode utilitaire interne au worker pour envoyer une commande et lire une ligne bloquante
    def _query(self, command, timeout_ms=500):
        if not self._is_open:
            self.error_occurred.emit("Impossible d'interroger: le port n'est pas ouvert.")
            return ""

        try:
            # Vider les données en attente pour éviter de lire des réponses obsolètes
            self._serial_port.readAll()

            self._serial_port.write(command.encode() + b'\n') # Assurez-vous d'envoyer un caractère de fin de ligne
            # Attendre que des octets soient disponibles
            if self._serial_port.waitForReadyRead(timeout_ms):
                response = self._serial_port.readLine().data().decode("utf-8").strip()
                # print(f"SerialWorker: Réponse à '{command}': '{response}'")
                return response
            else:
                print(f"SerialWorker: Timeout lors de la lecture de la réponse pour '{command}'")
                return ""
        except Exception as e:
            self.error_occurred.emit(f"Erreur lors de l'interrogation '{command}': {e}")
            print(f"SerialWorker: Erreur _query: {e}")
            return ""

    # Gère les erreurs du port série
    def _handle_serial_error(self, error):
        if error == QSerialPort.NoError:
            return
        error_msg = self._serial_port.errorString()
        self.error_occurred.emit(f"Erreur série: {error_msg} (Code: {error})")
        print(f"SerialWorker: Erreur QSerialPort: {error_msg} (Code: {error})")
        if self._is_open: # Tenter de fermer le port si une erreur grave survient
            self.close_port()

    # --- Commandes spécifiques à l'alimentation RS-3005P ---
    # Ces méthodes sont des wrappers qui utilisent _query ou _write_data
    # et sont appelées via des SIGNALS depuis l'UI (MainWindow)

    @pyqtSlot()
    def get_idn(self):
        # Cette méthode pourrait émettre un signal avec l'IDN si l'UI en a besoin
        idn = self._query("*IDN?")
        print(f"SerialWorker: IDN: {idn}")
        return idn # Retourne l'IDN mais une émission de signal est préférable pour l'UI

    @pyqtSlot()
    def get_actual_current(self):
        current_str = self._query("IOUT1?")
        try:
            current = float(current_str)
            current = current if 0 <= current <= 5 else np.nan
        except ValueError:
            current = np.nan
            self.error_occurred.emit(f"Impossible de convertir le courant: '{current_str}'")
        return current

    @pyqtSlot(float)
    def set_current(self, current):
        self.write_data(f"ISET1:{current}".encode())

    @pyqtSlot()
    def get_actual_voltage(self):
        voltage_str = self._query("VOUT1?")
        try:
            voltage = float(voltage_str)
            voltage = voltage if 0 <= voltage <= 30 else np.nan
        except ValueError:
            voltage = np.nan
            self.error_occurred.emit(f"Impossible de convertir la tension: '{voltage_str}'")
        return voltage

    @pyqtSlot(float)
    def set_voltage(self, voltage):
        self.write_data(f"VSET1:{voltage}".encode())

    @pyqtSlot(int) # 0 for unlock, 1 for lock
    def set_lock(self, loconoff):
        command = f"LOCK{loconoff}"
        self.write_data(command.encode())

    @pyqtSlot(int) # 0 for off, 1 for on
    def set_ocp(self, onoff):
        command = f"OCP{onoff}"
        self.write_data(command.encode())

    @pyqtSlot()
    def get_info_output(self):
        os_str = self._query("STATUS?")
        if os_str == "S":
            status = "connected"
        elif os_str == " ":
            status = "disconnected"
        else:
            status = "error"
        return status

    @pyqtSlot(int) # 0 for off, 1 for on
    def set_activate_output(self, outonoff):
        command = f"OUT{outonoff}"
        self.write_data(command.encode())

    # --- Gestion du timer de mesure ---
    @pyqtSlot(int, bool)
    def start_mesure_timer(self, interval_ms, simulation_mode):
        self._simulation_mode = simulation_mode # Mettre à jour le mode simulation
        if self._is_open or self._simulation_mode: # Démarrer seulement si port ouvert ou en simulation
            self.Temps.clear()
            self.Tension.clear()
            self.Current.clear()
            self._mesure_timer.start(interval_ms)
            print(f"SerialWorker: Timer de mesure démarré avec intervalle {interval_ms} ms (Simu: {simulation_mode})")
        else:
            self.error_occurred.emit("Impossible de démarrer la mesure: port non ouvert et pas en mode simulation.")
            print("SerialWorker: Mesure non démarrée: port non ouvert/simulation off.")

    @pyqtSlot()
    def stop_mesure_timer(self):
        if self._mesure_timer.isActive():
            self._mesure_timer.stop()
            print("SerialWorker: Timer de mesure arrêté.")

    def _read_mesure_data(self):
        # Cette méthode est appelée par le QTimer dans le thread du worker.
        # Elle effectue les lectures réelles ou simulées et émet les données.

        temps_actuel = 0
        if len(self.Temps) > 0:
            temps_actuel = self.Temps[-1] + (self._mesure_timer.interval() / 1000.0)
        # else: temps_actuel est déjà 0

        self.Temps.append(temps_actuel)

        if self._simulation_mode:
            tension = random.uniform(0, 2) + 19
            current = random.uniform(0, 2) + 4
        else:
            # Récupérer les vraies valeurs via le port série
            tension = self.get_actual_voltage()
            current = self.get_actual_current()

        self.Tension.append(tension)
        self.Current.append(current)

        # Émettre toutes les données pour la mise à jour de l'UI
        self.mesures_data_ready.emit(self.Temps, self.Tension, self.Current)


# La classe Window (MainWindow) gère l'UI et la communication avec le worker
class Window(QMainWindow, Ui_MainWindow):
    # Signaux pour envoyer des commandes au SerialWorker
    open_port_request = pyqtSignal(str, int)
    close_port_request = pyqtSignal() # Pas d'arguments pour la fermeture
    write_data_request = pyqtSignal(bytes)
    set_voltage_request = pyqtSignal(float)
    set_current_request = pyqtSignal(float)
    set_lock_request = pyqtSignal(int)
    set_ocp_request = pyqtSignal(int)
    set_output_request = pyqtSignal(int) # For activate/deactivate output
    start_mesure_timer_request = pyqtSignal(int, bool) # interval_ms, simulation_mode
    stop_mesure_timer_request = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setupUi(self) # Initialise l'interface utilisateur depuis alimlabo.py

        self.serial_thread = QThread()
        self.serial_worker = SerialWorker()
        self.serial_worker.moveToThread(self.serial_thread)

        # --- Connexions des signaux de la GUI aux slots du worker (MainWindow -> Worker) ---
        self.open_port_request.connect(self.serial_worker.open_port)
        self.close_port_request.connect(self.serial_worker.close_port)
        self.write_data_request.connect(self.serial_worker.write_data)
        self.set_voltage_request.connect(self.serial_worker.set_voltage)
        self.set_current_request.connect(self.serial_worker.set_current)
        self.set_lock_request.connect(self.serial_worker.set_lock)
        self.set_ocp_request.connect(self.serial_worker.set_ocp)
        self.set_output_request.connect(self.serial_worker.set_activate_output)
        self.start_mesure_timer_request.connect(self.serial_worker.start_mesure_timer)
        self.stop_mesure_timer_request.connect(self.serial_worker.stop_mesure_timer)


        # --- Connexions des signaux du worker aux slots de la GUI (Worker -> MainWindow) ---
        self.serial_worker.data_received.connect(self.reception_data)
        self.serial_worker.port_opened.connect(self.handle_port_opened)
        self.serial_worker.port_closed.connect(self.handle_port_closed)
        self.serial_worker.error_occurred.connect(self.handle_error)
        self.serial_worker.mesures_data_ready.connect(self.update_mesure_display) # Nouveau signal pour les mesures


        # --- Connexions pour le cycle de vie du thread ---
        # Quand le worker a fini, le thread doit quitter
        self.serial_worker.finished.connect(self.serial_thread.quit)
        # Quand le thread a quitté, supprimer le worker et le thread proprement
        self.serial_thread.finished.connect(self.serial_worker.deleteLater)
        self.serial_thread.finished.connect(self.serial_thread.deleteLater)
        self.serial_thread.started.connect(lambda: print("Serial thread started."))
        self.serial_thread.finished.connect(lambda: print("Serial thread finished."))

        # Démarrer le thread du worker
        self.serial_thread.start()

        self.init_ui() # Initialisation des autres éléments de l'UI et connexions

    def init_ui(self):
        # Remplir les QComboBox pour les ports et les baud rates
        self.populate_ports()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("9600")

        # Connexions des boutons et autres widgets
        self.open_port_btn.clicked.connect(self.on_open_port_button_clicked)
        self.close_port_btn.clicked.connect(self.on_close_port_button_clicked)
        self.send_data_btn.clicked.connect(self.on_send_data_button_clicked)

        self.dialVoltage.valueChanged.connect(self.on_dial_voltage_changed)
        self.dialAmpere.valueChanged.connect(self.on_dial_ampere_changed)

        self.buttonLOCK.clicked.connect(self.bloquePanneau)
        self.buttonOCP.clicked.connect(self.actionOCP)
        self.btnOnoff.clicked.connect(self.toggle_power_output) # Renommé pour être plus clair

        self.btnCommencer.clicked.connect(self.TimerStartMesure) # Démarrage/Pause des mesures
        self.btnReini.clicked.connect(self.reiniTab)
        self.btnEnregistrer.clicked.connect(self.enregTab)
        self.btnReiniGra.clicked.connect(self.reiniGraphique)

        self.checkBoxSimu.stateChanged.connect(self.ChangeMode)

        # Initialisation du graphique pyqtgraph
        self.TabTension.setBackground("w")
        self.TabTension.setTitle('Monitoring de la tension', color='b')
        self.TabTension.setLabel('left', 'Tension (V) et Courant (A)', color='black')
        self.TabTension.setLabel('bottom', 'Temps (s)', color='black')
        self.TabTension.showGrid(x=True, y=True, alpha=0.3)

        self.color_index = 0 # Indice de couleur pour les courbes
        self.curve_colors = ['b', 'g', 'r', 'c', 'm', 'y', 'black'] # Liste des couleurs
        self.current_voltage_curve = self.TabTension.plot(pen=self.curve_colors[0])
        self.current_current_curve = self.TabTension.plot(pen=self.curve_colors[1])


        self.colonne_Labels = ['Temps (s)', 'Tension (V)', 'Courant (A)']
        self.row_count = 0

        self.actionQuitter.triggered.connect(self.close) # Utiliser self.close() pour déclencher closeEvent

        # Initialisation de l'état des boutons
        self.btnReini.setEnabled(False)
        self.btnEnregistrer.setEnabled(False)
        self.btnReiniGra.setEnabled(False)
        self.send_data_input.setEnabled(False) # Désactivé jusqu'à l'ouverture du port
        self.send_data_btn.setEnabled(False) # Désactivé jusqu'à l'ouverture du port
        self.btnCommencer.setEnabled(False) # Désactivé jusqu'à l'ouverture du port

        # Initialisation des valeurs affichées par les cadrans
        self.labelVoltage.setText(f"Voltage: {self.dialVoltage.value()}V")
        self.labelAmpere.setText(f"Current: {self.dialAmpere.value()}A")


    def populate_ports(self):
        self.port_combo.clear()
        ports = QSerialPortInfo.availablePorts()
        if not ports:
            self.port_combo.addItem("Aucun port COM trouvé")
            self.open_port_btn.setEnabled(False)
        else:
            for port in ports:
                self.port_combo.addItem(port.portName())
            self.open_port_btn.setEnabled(True)

    # --- Slots réagissant aux actions de l'UI et émettant des signaux vers le worker ---
    def on_open_port_button_clicked(self):
        port_name = self.port_combo.currentText()
        baud_rate = int(self.baud_combo.currentText())
        if port_name == "Aucun port COM trouvé":
            QMessageBox.warning(self, "Erreur", "Aucun port série disponible.")
            return
        self.data_display.append(f"Tentative d'ouverture du port {port_name} à {baud_rate} bauds...")
        self.open_port_request.emit(port_name, baud_rate)

    def on_close_port_button_clicked(self):
        self.data_display.append("Tentative de fermeture du port...")
        self.close_port_request.emit()

    def on_send_data_button_clicked(self):
        data = self.send_data_input.text()
        if data:
            self.write_data_request.emit(data.encode())
            self.data_display.append(f"<span style='color: green;'>Envoyé: {data}</span>")
            self.send_data_input.clear()

    def on_dial_voltage_changed(self, value):
        self.labelVoltage.setText(f"Voltage: {value}V")
        self.set_voltage_request.emit(float(value))

    def on_dial_ampere_changed(self, value):
        self.labelAmpere.setText(f"Current: {value}A")
        self.set_current_request.emit(float(value))

    def bloquePanneau(self):
        if self.buttonLOCK.isChecked():
            self.set_lock_request.emit(1) # Demander au worker de verrouiller
            self.led_lock.setState(0) # Vert pour verrouillé
            self.dialVoltage.setEnabled(False)
            self.dialAmpere.setEnabled(False)
            self.dialVoltage.setNotchesVisible(False)
            self.dialAmpere.setNotchesVisible(False)
        else:
            self.set_lock_request.emit(0) # Demander au worker de déverrouiller
            self.led_lock.setState(1) # Rouge pour déverrouillé
            self.dialVoltage.setEnabled(True)
            self.dialAmpere.setEnabled(True)
            self.dialVoltage.setNotchesVisible(True)
            self.dialAmpere.setNotchesVisible(True)

    def actionOCP(self):
        if self.buttonOCP.isChecked():
            self.set_ocp_request.emit(1)
            self.led_ocp.setState(0) # OCP On
        else:
            self.set_ocp_request.emit(0)
            self.led_ocp.setState(1) # OCP Off

    def toggle_power_output(self):
        # Supposons que btnOnoff gère l'activation/désactivation de la sortie
        if self.btnOnoff.text() == "Power On/Off":
            self.set_output_request.emit(1) # Activer la sortie
            self.btnOnoff.setText("Power On")
            self.led_pp.setState(0) # Allumé
            self.led_pn.setState(0) # Allumé
            self.led_pgdn.setState(0) # Allumé
            # Activer les boutons liés au port après avoir allumé
            self.send_data_input.setEnabled(True)
            self.send_data_btn.setEnabled(True)
            self.btnCommencer.setEnabled(True) # Activer le bouton commencer
        else:
            self.set_output_request.emit(0) # Désactiver la sortie
            self.btnOnoff.setText("Power On/Off")
            self.led_pp.setState(1) # Éteint
            self.led_pn.setState(1) # Éteint
            self.led_pgdn.setState(1) # Éteint
            # Désactiver les boutons
            self.send_data_input.setEnabled(False)
            self.send_data_btn.setEnabled(False)
            self.btnCommencer.setEnabled(False) # Désactiver le bouton commencer

    def ChangeMode(self, checkState):
        is_simu = (checkState == Qt.Checked)
        if is_simu:
            self.spinBox.setMinimum(10)
        else:
            self.spinBox.setMinimum(500)
        # Informer le worker du changement de mode, notamment pour le timer de mesure
        if self.serial_worker._mesure_timer.isActive():
            self.start_mesure_timer_request.emit(self.spinBox.value(), is_simu)


    # --- Slots réagissant aux signaux du worker (Worker -> MainWindow) ---
    def reception_data(self, data):
        # Gère la réception de données brutes asynchrones
        try:
            decoded_data = data.decode('utf-8', errors='replace')
            self.data_display.append(f"<span style='color: blue;'>Données reçues: {decoded_data}</span>")
        except Exception as e:
            self.data_display.append(f"<span style='color: orange;'>Données brutes reçues (hex): {data.hex()} (Erreur décodage: {e})</span>")

    def handle_port_opened(self, success, message):
        self.data_display.append(message)
        self.statusBar().showMessage(message)
        if success:
            self.open_port_btn.setEnabled(False)
            self.close_port_btn.setEnabled(True)
            # Autres boutons liés à la communication série
            self.send_data_input.setEnabled(True)
            self.send_data_btn.setEnabled(True)
            self.btnCommencer.setEnabled(True) # Activer le bouton de mesure
        else:
            self.open_port_btn.setEnabled(True)
            self.close_port_btn.setEnabled(False)
            self.send_data_input.setEnabled(False)
            self.send_data_btn.setEnabled(False)
            self.btnCommencer.setEnabled(False)

    def handle_port_closed(self):
        self.data_display.append("Port fermé.")
        self.statusBar().showMessage("Port fermé.")
        self.open_port_btn.setEnabled(True)
        self.close_port_btn.setEnabled(False)
        self.send_data_input.setEnabled(False)
        self.send_data_btn.setEnabled(False)
        self.btnCommencer.setEnabled(False) # Désactiver le bouton de mesure
        self.stop_mesure_timer_request.emit() # S'assurer que le timer est arrêté

    def handle_error(self, errorMessage):
        QMessageBox.critical(self, "Erreur Port Série", errorMessage)
        self.data_display.append(f"<span style='color: red;'>ERREUR: {errorMessage}</span>")
        self.statusBar().showMessage(f"Erreur: {errorMessage}")
        # Désactiver les boutons en cas d'erreur grave
        self.open_port_btn.setEnabled(True)
        self.close_port_btn.setEnabled(False)
        self.send_data_input.setEnabled(False)
        self.send_data_btn.setEnabled(False)
        self.btnCommencer.setEnabled(False)
        self.stop_mesure_timer_request.emit()


    def TimerStartMesure(self):
        if self.btnCommencer.text() != "Pause":
            # Démarrer ou Continuer l'enregistrement
            if self.btnCommencer.text() == "Commencer l'enregistrement":
                self.btnReini.setEnabled(True)
                self.btnEnregistrer.setEnabled(True)
                self.btnReiniGra.setEnabled(True)
                self.reiniGraphique(clear_data=True) # Réinitialiser les données aussi
                self.row_count = 0 # Réinitialiser le compteur de lignes du tableau
                self.colonne_Labels = ['Temps (s)', 'Tension (V)', 'Courant (A)'] # Réinitialiser les labels
                self.Donnees.setColumnCount(3) # Assurer qu'il y a 3 colonnes initiales
                self.Donnees.setHorizontalHeaderLabels(self.colonne_Labels)
                self.TabTension.clear() # Effacer les tracés existants

                # Changer la couleur de la courbe pour la nouvelle session
                self.color_index = (self.color_index + 1) % len(self.curve_colors)
                # Créer de nouvelles courbes pour chaque session si nécessaire, ou réinitialiser les existantes
                self.current_voltage_curve = self.TabTension.plot(pen=self.curve_colors[self.color_index])
                self.current_current_curve = self.TabTension.plot(pen=self.curve_colors[(self.color_index + 1) % len(self.curve_colors)])


            self.btnCommencer.setText('Pause')
            # Envoyer le signal au worker pour démarrer son timer
            interval = self.spinBox.value()
            simulation_mode = self.checkBoxSimu.isChecked()
            self.start_mesure_timer_request.emit(interval, simulation_mode)

        elif self.btnCommencer.text() == "Pause":
            self.btnCommencer.setText('Continuer')
            self.stop_mesure_timer_request.emit() # Envoyer le signal pour arrêter le timer du worker

    def update_mesure_display(self, Temps, Tension, Current):
        # Cette méthode est appelée par le signal `mesures_data_ready` du worker
        # Elle met à jour le graphique et le tableau avec les nouvelles données
        self.current_voltage_curve.setData(Temps, Tension)
        self.current_current_curve.setData(Temps, Current)

        # Mise à jour du tableau
        # S'assurer que le tableau a assez de lignes
        if self.row_count >= self.Donnees.rowCount():
            self.Donnees.insertRow(self.Donnees.rowCount())

        # Mettre à jour les colonnes pour la session actuelle (colonne 0, 1, 2)
        self.Donnees.setItem(self.row_count, 0, QTableWidgetItem("{:.2f}".format(Temps[-1])))
        self.Donnees.setItem(self.row_count, 1, QTableWidgetItem("{:.2f}".format(Tension[-1])))
        self.Donnees.setItem(self.row_count, 2, QTableWidgetItem("{:.2f}".format(Current[-1])))
        self.row_count += 1
        self.Donnees.scrollToBottom() # Faire défiler vers le bas

    def reiniTab(self):
        self.stop_mesure_timer_request.emit() # Arrêter le timer de mesure
        self.btnCommencer.setText("Commencer l'enregistrement")
        self.Donnees.setRowCount(0) # Effacer toutes les lignes
        self.Donnees.setColumnCount(3) # Remettre à 3 colonnes initiales
        self.Donnees.setHorizontalHeaderLabels(['Temps (s)', 'Tension (V)', 'Courant (A)'])
        self.row_count = 0
        self.btnReini.setEnabled(False)
        self.btnEnregistrer.setEnabled(False)
        self.btnReiniGra.setEnabled(False) # Réactiver si le graphique est réinitialisé

    def reiniGraphique(self, clear_data=False):
        # Efface toutes les courbes du graphique
        self.TabTension.clear()
        if clear_data: # Optionnel: effacer les données aussi
            self.serial_worker.Temps.clear()
            self.serial_worker.Tension.clear()
            self.serial_worker.Current.clear()
        self.btnReiniGra.setEnabled(False)


    def enregTab(self):
        file_name = "data" + QDateTime.currentDateTime().toString("_yyyy-MM-dd_hh.mm.ss")
        file_name, file_type = QFileDialog.getSaveFileName(
            self, 'Enregistrer les données', file_name,
            'Text file (*.txt);;CSV file (*.csv);;All files(*)')

        if file_name:
            # Récupérer les données du worker (car il les stocke)
            temps = self.serial_worker.Temps
            tension = self.serial_worker.Tension
            current = self.serial_worker.Current

            with open(file_name, "w") as file:
                # Écrire l'en-tête du CSV
                file.write("Temps (s),Tension (V),Courant (A)\n")
                for t, v, c in zip(temps, tension, current):
                    file.write(f"{t},{v},{c}\n")

            path = pathlib.Path(file_name)
            self.data_display.append(f'{path.name} : Enregistrement de {len(temps)} points fait.')
        else:
            self.data_display.append("<b style='color:red'>Enregistrement annulé</b>")

    def closeapp(self):
        # Déclenchera closeEvent automatiquement
        self.close()

    def closeEvent(self, event):
        print("MainWindow: Exécution de closeEvent.")
        # Émettre le signal pour demander au worker de fermer le port
        self.close_port_request.emit()
        # Demander au thread de quitter et attendre qu'il se termine
        self.serial_thread.quit()
        # Attendre que le thread se termine. Un délai raisonnable est important.
        # Si le worker effectue des opérations bloquantes, le thread pourrait ne pas quitter immédiatement.
        if not self.serial_thread.wait(2000): # Attendre max 2 secondes
            print("MainWindow: Le thread série ne s'est pas terminé à temps. Forçage.")
            self.serial_thread.terminate() # Forcer la terminaison si nécessaire (utiliser avec prudence)
            self.serial_thread.wait(500) # Attendre un peu après terminate

        super().closeEvent(event)
        print("MainWindow: Application fermée.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Window()
    win.show()
    sys.exit(app.exec())