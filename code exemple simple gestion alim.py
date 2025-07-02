# -*- coding: utf-8 -*-
"""
Created on Fri Jun 27 14:45:24 2025

@author: gaspard.guidetti
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit, QLineEdit, QLabel
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot, QIODevice, QEventLoop, QTimer
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo

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
    def query(self, command_string, timeout_ms=2000): # Augmenté le timeout par défaut
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
        """Demande la tension de sortie actuelle et renvoie la valeur."""
        response = self.query("VOUT1?")
        try:
            # Exemple de parsing: cherche la valeur numérique après 'VOUT1:'
            if "VOUT1:" in response:
                voltage = float(response.split("VOUT1:")[-1].strip())
                return voltage
            else:
                self.error_occurred.emit(f"Format de réponse VOUT1 inattendu: '{response}'")
                return float('nan') # Not a Number
        except ValueError:
            self.error_occurred.emit(f"Impossible de parser la tension de: '{response}'")
            return float('nan')

    def get_current(self):
        """Demande le courant de sortie actuel et renvoie la valeur."""
        response = self.query("IOUT1?")
        try:
            # Exemple de parsing: cherche la valeur numérique après 'IOUT1:'
            if "IOUT1:" in response:
                current = float(response.split("IOUT1:")[-1].strip())
                return current
            else:
                self.error_occurred.emit(f"Format de réponse IOUT1 inattendu: '{response}'")
                return float('nan')
        except ValueError:
            self.error_occurred.emit(f"Impossible de parser le courant de: '{response}'")
            return float('nan')

    def set_output(self, state):
        """Active (1) ou désactive (0) la sortie de l'alimentation."""
        self.send_command(f"OUT{int(state)}")


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
        # Connecte à une nouvelle méthode dans MainWindow pour gérer la réponse
        self.btn_idn.clicked.connect(self._on_request_idn_clicked)
        self.btn_idn.setEnabled(False)
        btn_layout.addWidget(self.btn_idn)

        self.btn_set_voltage = QPushButton("Définir V=5V")
        # Appelle directement la méthode du worker
        self.btn_set_voltage.clicked.connect(lambda: self.worker.set_voltage(5))
        self.btn_set_voltage.setEnabled(False)
        btn_layout.addWidget(self.btn_set_voltage)

        self.btn_get_voltage = QPushButton("Obtenir Tension Actuelle")
        # Connecte à une nouvelle méthode dans MainWindow pour gérer la réponse
        self.btn_get_voltage.clicked.connect(self._on_get_voltage_clicked)
        self.btn_get_voltage.setEnabled(False)
        btn_layout.addWidget(self.btn_get_voltage)

        self.btn_get_current = QPushButton("Obtenir Courant Actuel")
        # Connecte à une nouvelle méthode dans MainWindow pour gérer la réponse
        self.btn_get_current.clicked.connect(self._on_get_current_clicked)
        self.btn_get_current.setEnabled(False)
        btn_layout.addWidget(self.btn_get_current)

        self.btn_output_on = QPushButton("Sortie ON")
        # Appelle directement la méthode du worker
        self.btn_output_on.clicked.connect(lambda: self.worker.set_output(1))
        self.btn_output_on.setEnabled(False)
        btn_layout.addWidget(self.btn_output_on)

        self.btn_output_off = QPushButton("Sortie OFF")
        # Appelle directement la méthode du worker
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
        self.worker.data_received.connect(self.log_data_received) # Pour le logging générique
        self.worker.error_occurred.connect(self.log_error)

        # Démarre le thread (le worker ne fera rien tant qu'il n'est pas appelé via ses slots)
        self.thread.start()
        self.console.append("Application démarrée. Thread worker actif.")

    def start_connection(self):
        """Demande au worker d'ouvrir le port."""
        self.open_port_signal.emit("COM3", 9600) # Adaptez le port et baud rate
        self.status_label.setText("Statut: Connexion en cours...")
        self.btn_open.setEnabled(False)

    def stop_connection(self):
        """Demande au worker de fermer le port."""
        self.close_port_signal.emit()

    @pyqtSlot(bool, str)
    def update_ui_on_port_status(self, success, message):
        """Met à jour l'UI en fonction du statut du port."""
        self.console.append(message)
        connected_text = f"Connecté à {message.split(' ')[1]}" if success else "Déconnecté"
        self.status_label.setText(f"Statut: {connected_text}")

        self.btn_open.setEnabled(not success)
        self.btn_close.setEnabled(success)
        self.btn_idn.setEnabled(success)
        self.btn_set_voltage.setEnabled(success)
        self.btn_get_voltage.setEnabled(success)
        self.btn_get_current.setEnabled(success) # Activer/désactiver le bouton de courant
        self.btn_output_on.setEnabled(success)
        self.btn_output_off.setEnabled(success)

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
        command = self.command_line.text()
        if command:
            self.worker.send_command(command)
            self.console.append(f"<span style='color: green;'>Envoyé: {command}</span>")
            self.command_line.clear()

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

    def _on_get_voltage_clicked(self):
        """Gère le clic sur le bouton Get Voltage et affiche la réponse."""
        if self.worker._is_open:
            self.console.append("Demande de tension (attente de réponse)...")
            voltage = self.worker.get_voltage()
            if not isinstance(voltage, float) or not (0 <= voltage <= 30): # Validation simple
                self.console.append(f"<span style='color: orange;'>Tension reçue invalide: {voltage}</span>")
            else:
                self.console.append(f"<span style='color: darkgreen;'>Tension actuelle: {voltage:.2f} V</span>")
        else:
            self.log_error("Port non ouvert pour obtenir la tension.")

    def _on_get_current_clicked(self):
        """Gère le clic sur le bouton Get Current et affiche la réponse."""
        if self.worker._is_open:
            self.console.append("Demande de courant (attente de réponse)...")
            current = self.worker.get_current()
            if not isinstance(current, float) or not (0 <= current <= 5): # Validation simple
                self.console.append(f"<span style='color: orange;'>Courant reçu invalide: {current}</span>")
            else:
                self.console.append(f"<span style='color: darkgreen;'>Courant actuel: {current:.3f} A</span>")
        else:
            self.log_error("Port non ouvert pour obtenir le courant.")


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
    main_window.show()
    sys.exit(app.exec_())