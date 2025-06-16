from PyQt5.QtWidgets import QLabel, QWidget
from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt
 
class PyLedLabel(QLabel):
    """
    Une classe QLabel personnalisée qui se comporte comme une LED avec différents états.
    """
 
    # Définition des états de la LED
    StateOk = 0
    StateOkBlue = 1
    StateWarning = 2
    StateError = 3
 
    # Constantes pour la taille et les feuilles de style
    _SIZE = 30
    _greenSS = f"color: white;border-radius: {_SIZE/2};background-color: qlineargradient(spread:pad, x1:0.145, y1:0.16, x2:1, y2:1, stop:0 rgba(20, 252, 7, 255), stop:1 rgba(25, 134, 5, 255));"
    _redSS = f"color: white;border-radius: {_SIZE/2};background-color: qlineargradient(spread:pad, x1:0.145, y1:0.16, x2:0.92, y2:0.988636, stop:0 rgba(255, 12, 12, 255), stop:0.869347 rgba(103, 0, 0, 255));"
    _orangeSS = f"color: white;border-radius: {_SIZE/2};background-color: qlineargradient(spread:pad, x1:0.232, y1:0.272, x2:0.98, y2:0.959773, stop:0 rgba(255, 113, 4, 255), stop:1 rgba(91, 41, 7, 255));"
    _blueSS = f"color: white;border-radius: {_SIZE/2};background-color: qlineargradient(spread:pad, x1:0.04, y1:0.0565909, x2:0.799, y2:0.795, stop:0 rgba(203, 220, 255, 255), stop:0.41206 rgba(0, 115, 255, 255), stop:1 rgba(0, 49, 109, 255));"
 
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setText("")
        self.setFixedSize(self._SIZE, self._SIZE)
        # Définit l'état par défaut sur StateOkBlue
        self.setState(self.StateOkBlue)
    @pyqtSlot(int)
    def setState(self, state: int):
        """
        Définit l'état de la LED en utilisant les valeurs d'énumération.
        """
        # print(f"setState: {state}")
        if state == self.StateOk:
            self.setStyleSheet(self._greenSS)                                                                                                                                                                 
        elif state == self.StateWarning:                    
            self.setStyleSheet(self._orangeSS)
        elif state == self.StateError:      
            self.setStyleSheet(self._redSS)
        elif state == self.StateOkBlue:
            self.setStyleSheet(self._blueSS)
        else:
            # Gérer les cas inattendus ou définir un état par défaut
            self.setStyleSheet(self._blueSS)
 
    @pyqtSlot(bool)
    def setStateBool(self, state: bool):
        """
        Définit l'état de la LED en utilisant une valeur booléenne.
        True correspond à StateOk, False à StateError.
        """
        self.setState(self.StateOk if state else self.StateError)
    
