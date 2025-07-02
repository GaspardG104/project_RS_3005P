# -*- coding: utf-8 -*-
"""
Created on Fri Jun 20 15:31:12 2025

@author: gaspard.guidetti
"""
Gérer l'accès au port série avec PyQt et les threads est un sujet crucial pour assurer la réactivité de votre interface utilisateur et éviter les blocages. Voici les meilleures 
pratiques et les considérations concernant les mécanismes de synchronisation :
1. Pourquoi utiliser des threads pour le port série avec PyQt ?
Le port série est une ressource "lente" et bloquante. Si vous effectuez des opérations de lecture/écriture directement dans le thread principal (GUI), votre application gèlera pendant 
que ces opérations attendent des données ou que les données soient envoyées. Utiliser un thread séparé pour la communication série permet à l'interface utilisateur de rester réactive 
et de traiter les événements pendant que le thread série gère les opérations bloquantes en arrière-plan.
2. PyQt et QSerialPort : Approche recommandée
PyQt (et Qt en général) fournit une classe QSerialPort qui est très bien conçue pour la communication série. Elle prend en charge un mode asynchrone qui est souvent suffisant et 
préférable à l'utilisation explicite de threads pour les opérations de base de lecture/écriture si le traitement des données n'est pas intensif.
A. Approche Asynchrone (Sans Thread séparé pour QSerialPort elle-même) :
La manière la plus idiomatique de travailler avec QSerialPort dans PyQt est d'utiliser son mode asynchrone avec des signaux et des slots. QSerialPort émet des signaux comme 
readyRead() lorsque des données sont disponibles à la lecture et bytesWritten() lorsque des données ont été écrites.
 * Avantages :
   * Simplifie le code : pas besoin de gérer explicitement les threads, les mutex, les sémaphores pour l'accès à QSerialPort.
   * Optimisé pour l'intégration avec la boucle d'événements de Qt.
   * L'interface utilisateur reste fluide.
 * Inconvénients :
   * Si le traitement des données reçues est complexe ou long, cela peut toujours bloquer le thread principal. Dans ce cas, vous devrez déplacer le traitement des données vers un 
   thread séparé.
   * Les opérations de lecture/écriture bloquantes (read() sans readyRead(), write() sans bytesWritten() ou avec waitForBytesWritten()) ne doivent pas être utilisées dans le thread 
   principal.
Exemple simplifié d'utilisation asynchrone :
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt5.QtCore import QIODevice, pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit
 
class SerialCommunicator(QObject):
    data_received = pyqtSignal(bytes) # Signal pour envoyer les données reçues au thread principal
 
    def __init__(self, parent=None):
        super().__init__(parent)
        self.serial_port = QSerialPort()
        self.serial_port.readyRead.connect(self.read_data)
 
    def open_port(self, port_name, baud_rate):
        self.serial_port.setPortName(port_name)
        self.serial_port.setBaudRate(baud_rate)
        if self.serial_port.open(QIODevice.ReadWrite):
            print(f"Port {port_name} ouvert.")
            return True
        else:
            print(f"Erreur d'ouverture du port {port_name}: {self.serial_port.errorString()}")
            return False
 
    def close_port(self):
        if self.serial_port.isOpen():
            self.serial_port.close()
            print("Port fermé.")
 
    def write_data(self, data):
        if self.serial_port.isOpen():
            self.serial_port.write(data)
        else:
            print("Port non ouvert pour écriture.")
 
    def read_data(self):
        while self.serial_port.bytesAvailable():
            data = self.serial_port.readAll().data()
            self.data_received.emit(data) # Émet le signal vers le thread principal
 
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.serial_comm = SerialCommunicator()
        self.serial_comm.data_received.connect(self.display_data)
 
    def init_ui(self):
        self.text_display = QTextEdit()
        self.send_button = QPushButton("Envoyer 'Hello'")
        self.send_button.clicked.connect(self.send_hello)
        self.open_button = QPushButton("Ouvrir Port")
        self.open_button.clicked.connect(self.open_serial_port)
        self.close_button = QPushButton("Fermer Port")
        self.close_button.clicked.connect(self.close_serial_port)
 
        layout = QVBoxLayout()
        layout.addWidget(self.text_display)
        layout.addWidget(self.send_button)
        layout.addWidget(self.open_button)
        layout.addWidget(self.close_button)
        self.setLayout(layout)
        self.setWindowTitle("PyQt Serial Port Demo")
 
    def open_serial_port(self):
        # Remplacez 'COMx' par votre port série réel et 9600 par votre baud rate
        # Vous pouvez utiliser QSerialPortInfo.availablePorts() pour lister les ports
        port_name = "COM3" # ou '/dev/ttyUSB0' sur Linux
        baud_rate = 9600
        self.serial_comm.open_port(port_name, baud_rate)
 
    def close_serial_port(self):
        self.serial_comm.close_port()
 
    def send_hello(self):
        self.serial_comm.write_data(b"Hello from PyQt!\n")
 
    def display_data(self, data):
        self.text_display.append(data.decode('utf-8', errors='ignore'))
 
if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
 
3. Quand utiliser des threads séparés avec QSerialPort ?
Si vous avez besoin de :
 * Effectuer des opérations série bloquantes (par exemple, attendre une réponse spécifique avec un timeout) sans bloquer l'interface utilisateur.
 * Effectuer un traitement intensif des données reçues qui prendrait trop de temps dans le thread principal.
 * Gérer plusieurs ports série simultanément avec des logiques indépendantes.
Dans ce cas, vous devrez déplacer l'objet QSerialPort dans un QThread séparé.
Méthode recommandée pour QThread et QSerialPort:
La meilleure approche est de ne jamais sous-classer QThread et d'y placer votre logique. Au lieu de cela, créez une classe QObject (votre "Worker" ou "SerialWorker") qui gérera
 QSerialPort, puis déplacez cette instance de QObject vers une instance de QThread.
Pourquoi ne pas sous-classer QThread pour la logique ?
QThread est le thread, pas l'objet qui fait le travail. Son rôle est de gérer un nouveau thread d'exécution. Si vous mettez votre logique directement dans la sous-classe de QThread,
son run() est exécuté dans le nouveau thread, mais les autres méthodes de la classe (et donc les signaux/slots connectés à l'interface utilisateur) s'exécutent par défaut dans le
thread d'où l'objet QThread a été créé (généralement le thread principal). Cela peut entraîner des problèmes de "thread affinity" (affinité de thread) et des crashs.
Voici comment faire correctement :
 * Créez une classe SerialWorker (qui hérite de QObject).                                              FAIT
 * Dans le constructeur de SerialWorker, créez votre instance QSerialPort.                             FAIT
 * Définissez des slots dans SerialWorker pour les commandes que vous voulez envoyer (par exemple, write_data). FAIT
 * Connectez les signaux de QSerialPort (comme readyRead()) à des slots dans SerialWorker pour gérer la réception.FAIT
 * Créez des signaux dans SerialWorker pour envoyer des données ou des notifications au thread principal (par exemple, data_received, error_occurred).FAIT
 * Dans votre MainWindow (thread principal) :FAIT
   * Créez une instance de QThread.FAIT
   * Créez une instance de SerialWorker.FAIT
   * Appelez worker.moveToThread(thread).FAIT
   * Connectez les signaux du worker aux slots de votre MainWindow pour la mise à jour de l'interface. ###########################################
   * Connectez les signaux de votre MainWindow (par exemple, un clic de bouton) aux slots du worker pour envoyer des commandes.
   * Connectez thread.started à la méthode d'initialisation du worker (par exemple, worker.open_port).
   * Connectez thread.finished aux méthodes de nettoyage du worker (par exemple, worker.close_port).
   * Démarrez le thread avec thread.start().
Exemple de structure avec QThread et moveToThread:
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt5.QtCore import QIODevice, QThread, pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QComboBox, QLabel
 
class SerialWorker(QObject):
    data_received = pyqtSignal(bytes)
    port_opened = pyqtSignal(bool, str) # bool success, str message
    port_closed = pyqtSignal()
    error_occurred = pyqtSignal(str)
 
    def __init__(self):
        super().__init__()
        self._serial_port = QSerialPort()
        self._serial_port.readyRead.connect(self._read_data)
        self._is_open = False
 
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
 
    def close_port(self):
        if self._serial_port.isOpen():
            self._serial_port.close()
            self._is_open = False
            self.port_closed.emit()
            print("Port fermé dans le worker.")

    def write_data(self, data):
        if self._is_open:
            self._serial_port.write(data)
        else:
            self.error_occurred.emit("Impossible d'écrire: le port n'est pas ouvert.")
 
    def _read_data(self):
        while self._serial_port.bytesAvailable():
            data = self._serial_port.readAll().data()
            self.data_received.emit(data)
    def set_current(self, current):
        self.write_data(f"ISET1:{current}")

 
class MainWindow(QWidget):
    open_port_request = pyqtSignal(str, int)
    close_port_request = pyqtSignal()
    write_data_request = pyqtSignal(bytes)
 
    def __init__(self):
        super().__init__()
        self.init_ui()
 
        self.serial_thread = QThread()
        self.serial_worker = SerialWorker()
        self.serial_worker.moveToThread(self.serial_thread)
 
        # Connexions des signaux de la GUI aux slots du worker
        self.open_port_request.connect(self.serial_worker.open_port)
        self.close_port_request.connect(self.serial_worker.close_port)
        self.write_data_request.connect(self.serial_worker.write_data)
 
        # Connexions des signaux du worker aux slots de la GUI
        self.serial_worker.data_received.connect(self.display_data)
        self.serial_worker.port_opened.connect(self.handle_port_opened)
        self.serial_worker.port_closed.connect(self.handle_port_closed)
        self.serial_worker.error_occurred.connect(self.display_error)
 
        # Démarrer le thread lorsque l'application est prête
        self.serial_thread.start()
 
    def init_ui(self):
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
 
        self.port_combo = QComboBo)
        self.baud_combo = QComboBo)
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("9600")
 
        self.refresh_ports_button = QPushButton("Actualiser Ports")
        self.refresh_ports_button.clicked.connect(self.populate_ports)
 
        self.open_button = QPushButton("Ouvrir Port")
        self.open_button.clicked.connect(self.request_open_port)
        self.close_button = QPushButton("Fermer Port")
        self.close_button.clicked.connect(self.request_close_port)
 
        self.send_input = QTextEdit()
        self.send_input.setPlaceholderText("Entrez le message à envoyer...")
        self.send_button = QPushButton("Envoyer")
        self.send_button.clicked.connect(self.request_send_data)
 
        self.status_label = QLabel("Statut: Déconnecté")
 
        # Layout
        v_layout = QVBoxLayout()
        v_layout.addWidget(QLabel("Ports disponibles:"))
        h_port_layout = QHBoxLayout()
        h_port_layout.addWidget(self.port_combo)
        h_port_layout.addWidget(self.refresh_ports_button)
        v_layout.addLayout(h_port_layout)
        v_layout.addWidget(QLabel("Baud Rate:"))
        v_layout.addWidget(self.baud_combo)
        v_layout.addWidget(self.open_button)
        v_layout.addWidget(self.close_button)
        v_layout.addWidget(QLabel("Données reçues:"))
        v_layout.addWidget(self.text_display)
        v_layout.addWidget(QLabel("Envoyer des données:"))
        v_layout.addWidget(self.send_input)
        v_layout.addWidget(self.send_button)
        v_layout.addWidget(self.status_label)
 
        self.setLayout(v_layout)
        self.setWindowTitle("PyQt Threaded Serial Port")
        self.populate_ports()
 
        # Connecter le signal finished du thread à la suppression du worker
        self.serial_thread.finished.connect(self.serial_worker.deleteLater)
        self.serial_thread.finished.connect(self.serial_thread.deleteLater)
 
 
    def populate_ports(self):
        self.port_combo.clear()
        ports = QSerialPortInfo.availablePorts()
        if not ports:
            self.port_combo.addItem("Aucun port trouvé")
            self.open_button.setEnabled(False)
        else:
            self.open_button.setEnabled(True)
            for port in ports:
                self.port_combo.addItem(port.portName())
 
    def request_open_port(self):
        port_name = self.port_combo.currentText()
        baud_rate = int(self.baud_combo.currentText())
        self.open_port_request.emit(port_name, baud_rate)
 
    def request_close_port(self):
        self.close_port_request.emit()
 
    def request_send_data(self):
        data_to_send = self.send_input.toPlainText() + "\n" # Ajouter un retour chariot pour l'exemple
        self.write_data_request.emit(data_to_send.encode('utf-8'))
        self.send_input.clear()
 
    def display_data(self, data):
        self.text_display.append(data.decode('utf-8', errors='ignore'))
 
    def handle_port_opened(self, success, message):
        self.status_label.setText(f"Statut: {message}")
        self.open_button.setEnabled(not success)
        self.close_button.setEnabled(success)
        self.send_button.setEnabled(success)
 
    def handle_port_closed(self):
        self.status_label.setText("Statut: Déconnecté")
        self.open_button.setEnabled(True)
        self.close_button.setEnabled(False)
        self.send_button.setEnabled(False)
 
    def display_error(self, message):
        self.status_label.setText(f"Erreur: {message}")
        self.open_button.setEnabled(True)
        self.close_button.setEnabled(False)
        self.send_button.setEnabled(False)
 
    def closeEvent(self, event):
        # S'assurer que le thread se termine proprement à la fermeture de l'application
        self.close_port_request.emit()
        self.serial_thread.quit()
        self.serial_thread.wait() # Attendre que le thread se termine
        super().closeEvent(event)
 
if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
 
4. Mutex, Sémaphores et autres mécanismes de synchronisation
Dans l'approche recommandée avec QSerialPort et moveToThread, l'accès au port série lui-même (les appels open(), close(), read(), write()) est géré au sein du même thread où 
réside l'objet QSerialPort (le thread du worker). Par conséquent, vous n'avez pas besoin de mutex ou de sémaphores pour protéger l'accès à l'objet QSerialPort lui-même.
Les signaux et les slots de Qt sont intrinsèquement thread-safe lorsqu'ils sont utilisés entre des objets résidant dans des threads différents. Qt s'occupe de la sérialisation 
des appels, garantissant que les slots sont exécutés dans le thread de l'objet récepteur.
Quand pourriez-vous avoir besoin de mutex/sémaphores ?
Vous auriez besoin de ces mécanismes si :
 * Vous partagez d'autres données ou ressources entre le thread GUI et le thread série (ou entre plusieurs threads de workers). Par exemple, si le thread série lit des données et
 met à jour une structure de données complexe qui est également lue par le thread GUI, alors cette structure de données commune devrait être protégée par un QMutex (ou threading.Lock 
de Python si vous utilisez les threads Python standard, mais QMutex est recommandé avec PyQt).
 * Vous avez plusieurs threads qui tentent d'accéder au même port série directement (ce qui est déconseillé). 
 Dans ce scénario, un QMutex serait indispensable pour garantir qu'un seul thread accède au port à la fois. Cependant, la conception avec un seul SerialWorker qui encapsule le QSerialPort est bien supérieure.
 * Vous avez des scénarios plus complexes où vous devez limiter le nombre de threads accédant à une ressource limitée (comme des connexions réseau multiples) ou synchroniser 
 des tâches complexes. Les sémaphores (QSemaphore) pourraient être utiles ici.
En résumé :
 * Pour la gestion du port série avec PyQt, l'approche la plus propre et la plus robuste est d'utiliser QSerialPort dans un thread séparé en déplaçant une instance de QObject (votre SerialWorker) vers une instance de QThread.
 * Avec cette conception, les signaux et slots de Qt s'occupent de la communication inter-threads de manière thread-safe.
 * Vous n'aurez pas besoin de mutex ou de sémaphores pour protéger l'accès à l'objet QSerialPort lui-même.
 * Les mutex/sémaphores deviennent nécessaires si vous partagez d'autres ressources ou données mutables entre vos threads, au-delà de la communication via signaux/slots.
Concentrez-vous sur la conception de votre SerialWorker et l'utilisation correcte des signaux et slots de PyQt pour la communication entre le thread GUI et le thread série. 
C'est la solution la plus "PyQt-native" et la plus facile à déboguer.
 
 