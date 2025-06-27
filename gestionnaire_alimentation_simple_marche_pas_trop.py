# -*- coding: utf-8 -*-
"""
Created on Fri Jun 27 14:16:36 2025

@author: gaspard.guidetti
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit, QLineEdit, QLabel
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot, QIODevice
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo

class SerialWorker(QObject):
    """
    Worker pour gérer la communication série dans un thread séparé.
    Émet des signaux pour communiquer avec l'interface utilisateur.
    """
    # Signaux émis par le worker pour l'UI
    port_status = pyqtSignal(bool, str) # (succès, message)
    data_received = pyqtSignal(str)     # Données décodées reçues
    error_occurred = pyqtSignal(str)    # Messages d'erreur

    # Signal interne pour demander l'écriture (appelé par des méthodes publiques)
    _write_request = pyqtSignal(bytes)

    def __init__(self):
        super().__init__()
        self._serial_port = QSerialPort()
        # Connecte le signal 'readyRead' du QSerialPort à notre slot de lecture
        self._serial_port.readyRead.connect(self._read_data)
        # Connecte notre signal interne '_write_request' à notre slot d'écriture
        self._write_request.connect(self._write_data)
        self._is_open = False


    def open_port(self, port_name, baud_rate):
        """Ouvre le port série avec les paramètres spécifiés."""
        if self._serial_port.isOpen():
            self._serial_port.close()

        self._serial_port.setPortName(port_name)
        self._serial_port.setBaudRate(baud_rate)
        self._serial_port.setDataBits(QSerialPort.Data8)
        self._serial_port.setParity(QSerialPort.NoParity)
        self._serial_port.setStopBits(QSerialPort.OneStop)
        self._serial_port.setFlowControl(QSerialPort.NoFlowControl) # Souvent un bon défaut

        if self._serial_port.open(QIODevice.ReadWrite):
            self._is_open = True
            self.port_status.emit(True, f"Port '{port_name}' ouvert à {baud_rate} bauds.")
        else:
            self._is_open = False
            error_msg = self._serial_port.errorString()
            self.port_status.emit(False, f"Erreur d'ouverture de '{port_name}': {error_msg}")
            self.error_occurred.emit(error_msg)


    def close_port(self):
        """Ferme le port série."""
        if self._serial_port.isOpen():
            self._serial_port.close()
            self._is_open = False
            self.port_status.emit(False, "Port série fermé.")


    def _write_data(self, data):
        """Slot interne pour écrire des octets sur le port série."""
        if self._is_open:
            written_bytes = self._serial_port.write(data)
            if written_bytes == -1:
                self.error_occurred.emit(f"Erreur d'écriture: {self._serial_port.errorString()}")
        else:
            self.error_occurred.emit("Impossible d'écrire: le port n'est pas ouvert.")


    def _read_data(self):
        """Slot pour lire les données disponibles quand 'readyRead' est émis."""
        while self._serial_port.bytesAvailable():
            data = self._serial_port.readAll().data()
            try:
                # Décoder les octets reçus en chaîne (souvent 'ascii' ou 'utf-8')
                decoded_data = data.decode('ascii').strip()
                if decoded_data: # Émettre seulement si non vide après strip
                    self.data_received.emit(decoded_data)
            except UnicodeDecodeError:
                self.error_occurred.emit(f"Erreur de décodage des données: {data!r}")

    # --- Méthodes publiques pour envoyer des commandes (appelées depuis l'UI) ---
    def send_command(self, command_string):
        """Envoie une commande textuelle à l'appareil, ajoute un retour chariot."""
        # Ajouter un terminateur de ligne et encoder en octets
        self._write_request.emit((command_string + "\n").encode('ascii'))

    def request_idn(self):
        """Demande l'identification de l'appareil."""
        if self._is_open:
            self.send_command("*IDN?")
        else:
            self.error_occurred.emit("Port non ouvert pour demander l'IDN.")

    def set_voltage(self, voltage):
        """Définit la tension de sortie de l'alimentation."""
        if self._is_open:
            self.send_command(f"VSET1:{voltage}")
        else:
            self.error_occurred.emit("Port non ouvert pour définir la tension.")

    def get_voltage(self):
        """Demande la tension de sortie actuelle."""
        if self._is_open:
            self.send_command("VOUT1?")
        else:
            self.error_occurred.emit("Port non ouvert pour obtenir la tension.")

    def set_output(self, state):
        """Active (1) ou désactive (0) la sortie de l'alimentation."""
        if self._is_open:
            self.send_command(f"OUT{int(state)}")
        else:
            self.error_occurred.emit("Port non ouvert pour contrôler la sortie.")

class MainWindow(QMainWindow):
    """
    Fenêtre principale de l'application avec l'interface utilisateur.
    Gère le cycle de vie du SerialWorker et du QThread.
    """
    # Signaux pour demander au SerialWorker d'effectuer des actions
    open_port_signal = pyqtSignal(str, int)
    close_port_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Contrôle Alimentation Labo Simple")
        self.setGeometry(100, 100, 700, 500)
        
        self.serial_thread = QThread()
        self.worker = SerialWorker()
        self.worker.moveToThread(self.serial_thread)
        # Création des composants UI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.status_label = QLabel("Statut: Déconnecté")
        layout.addWidget(self.status_label)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console)

        self.command_line = QLineEdit()
        self.command_line.setPlaceholderText("Entrez une commande SCPI (ex: VSET1:5)")
        self.command_line.returnPressed.connect(self.send_custom_command)
        layout.addWidget(self.command_line)

        # Boutons de contrôle
        btn_layout = QVBoxLayout()
        self.btn_open = QPushButton("Ouvrir COM3 @ 9600")
        self.btn_open.clicked.connect(self.start_connection)
        btn_layout.addWidget(self.btn_open)

        self.btn_close = QPushButton("Fermer Port")
        self.btn_close.clicked.connect(self.stop_connection)
        self.btn_close.setEnabled(False) # Désactivé au début
        btn_layout.addWidget(self.btn_close)

        self.btn_idn = QPushButton("Demander IDN")
        self.btn_idn.clicked.connect(self.worker.request_idn)
        self.btn_idn.setEnabled(False)
        btn_layout.addWidget(self.btn_idn)

        self.btn_set_voltage = QPushButton("Définir V=5V")
        self.btn_set_voltage.clicked.connect(lambda: self.worker.set_voltage(5))
        self.btn_set_voltage.setEnabled(False)
        btn_layout.addWidget(self.btn_set_voltage)

        self.btn_get_voltage = QPushButton("Obtenir Tension Actuelle")
        self.btn_get_voltage.clicked.connect(self.worker.get_voltage)
        self.btn_get_voltage.setEnabled(False)
        btn_layout.addWidget(self.btn_get_voltage)

        self.btn_output_on = QPushButton("Sortie ON")
        self.btn_output_on.clicked.connect(lambda: self.worker.set_output(1))
        self.btn_output_on.setEnabled(False)
        btn_layout.addWidget(self.btn_output_on)

        self.btn_output_off = QPushButton("Sortie OFF")
        self.btn_output_off.clicked.connect(lambda: self.worker.set_output(0))
        self.btn_output_off.setEnabled(False)
        btn_layout.addWidget(self.btn_output_off)


        layout.addLayout(btn_layout)


        # --- Configuration du QThread et SerialWorker ---
        self.thread = QThread()
        self.worker = SerialWorker()
        self.worker.moveToThread(self.thread) # IMPORTANT: Déplace le worker vers le nouveau thread

        # Connecte les signaux de l'UI au worker
        self.open_port_signal.connect(self.worker.open_port)
        self.close_port_signal.connect(self.worker.close_port)

        # Connecte les signaux du worker à l'UI
        self.worker.port_status.connect(self.update_ui_on_port_status)
        self.worker.data_received.connect(self.log_data_received)
        self.worker.error_occurred.connect(self.log_error)

        # Démarre le thread (le worker ne fera rien tant qu'il n'est pas appelé via ses slots)
        self.thread.start()
        self.console.append("Application démarrée. Thread worker actif.")


    def start_connection(self):
        """Demande au worker d'ouvrir le port."""
        # Remplacez "COM3" par le port de votre alimentation et 9600 par le baud rate
        # Pour trouver les ports disponibles : QSerialPortInfo.availablePorts()
        self.open_port_signal.emit("COM3", 9600)
        self.status_label.setText("Statut: Connexion en cours...")
        self.btn_open.setEnabled(False) # Désactiver pour éviter des clics multiples

    def stop_connection(self):
        """Demande au worker de fermer le port."""
        self.close_port_signal.emit()


    def update_ui_on_port_status(self, success, message):
        """Met à jour l'UI en fonction du statut du port."""
        self.console.append(message)
        if success:
            self.status_label.setText(f"Statut: Connecté à {message.split(' ')[1]}")
            self.btn_open.setEnabled(False)
            self.btn_close.setEnabled(True)
            # Activer les boutons de commande une fois connecté
            self.btn_idn.setEnabled(True)
            self.btn_set_voltage.setEnabled(True)
            self.btn_get_voltage.setEnabled(True)
            self.btn_output_on.setEnabled(True)
            self.btn_output_off.setEnabled(True)
        else:
            self.status_label.setText("Statut: Déconnecté")
            self.btn_open.setEnabled(True)
            self.btn_close.setEnabled(False)
            # Désactiver les boutons de commande si déconnecté
            self.btn_idn.setEnabled(False)
            self.btn_set_voltage.setEnabled(False)
            self.btn_get_voltage.setEnabled(False)
            self.btn_output_on.setEnabled(False)
            self.btn_output_off.setEnabled(False)


    def log_data_received(self, data):
        """Affiche les données reçues dans la console."""
        self.console.append(f"<span style='color: blue;'>Reçu: {data}</span>")


    def log_error(self, error_message):
        """Affiche les messages d'erreur dans la console."""
        self.console.append(f"<span style='color: red;'>Erreur: {error_message}</span>")

    def send_custom_command(self):
        """Envoie une commande tapée par l'utilisateur."""
        command = self.command_line.text()
        if command:
            self.worker.send_command(command)
            self.console.append(f"<span style='color: green;'>Envoyé: {command}</span>")
            self.command_line.clear() # Efface la ligne de commande

    def closeEvent(self, event):
        """Gère la fermeture de la fenêtre pour arrêter le thread proprement."""
        self.stop_connection() # Demande au worker de fermer le port
        self.thread.quit()     # Demande au thread de quitter sa boucle d'événements
        self.thread.wait(2000) # Attendre que le thread se termine (max 2 secondes)
        if self.thread.isRunning():
            self.thread.terminate() # Forcer l'arrêt si le thread ne répond pas
            self.console.append("<span style='color: orange;'>Le thread a dû être terminé de force.</span>")
        event.accept() # Accepter l'événement de fermeture de la fenêtre

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())