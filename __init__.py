# Author: Austin Hasten
# Initial Commit: Mar 16 2021

import random
from aqt.qt import *
from PyQt5.QtCore import *
from aqt import mw, gui_hooks
from aqt.utils import showInfo
import math

class StackWidget(QWidget):
    periods = {'Month':31, 'Year':365, 'All Time':365000}
    defaultTargetRetention = 85
    
    def __init__(self, deck):
        super().__init__()
        self.deck = deck
        self.optionsGroup = mw.col.decks.get_config(self.deck['conf'])
        self.currentIvlFct = self.optionsGroup['rev']['ivlFct']
        self.currentRetention = round(calcCurrentRetention(self.deck['id'], 31), 2)
        # Formula uses targetRetentionSpin's value, so calc after that's created
        self.idealIvlFct = None
        
        self.buildGUI()
        
    def buildGUI(self):
        self.layout = QGridLayout(self)
        
        self.periodLbl = QLabel('Retention Period:')
        self.periodCombo = QComboBox()
        self.periodCombo.addItems(self.periods.keys())
        self.periodCombo.currentTextChanged.connect(self.periodChanged)
        
        self.optionsGroupLbl = QLabel('Options Group:')
        self.optionsGroupInput = QLineEdit(self.optionsGroup['name'])
        self.optionsGroupInput.setEnabled(False)
        
        self.currentIvlFctLbl = QLabel('Current Interval Modifier:')
        self.currentIvlFctInput = QLineEdit(str(self.currentIvlFct))
        self.currentIvlFctInput.setEnabled(False)
        
        self.targetRetentionLbl = QLabel(f'Target Retention:')
        self.targetRetentionSpin = QSpinBox()
        self.targetRetentionSpin.setRange(1, 100)
        self.targetRetentionSpin.setSuffix('%')
        self.targetRetentionSpin.setValue(self.defaultTargetRetention)
        self.targetRetentionSpin.valueChanged.connect(self.targetRetentionChanged)
        
        self.currentRetentionLbl = QLabel('Current Retention:')
        self.currentRetentionInput = QLineEdit(str(self.currentRetention)+'%')
        self.currentRetentionInput.setEnabled(False)
        
        self.errorLbl = QLabel('100% retention breaks the equation. Update Interval Modifier manually.')
        
        self.newIvlFctLbl = QLabel('New Interval Modifier:')
        self.newIvlFctInput = QLineEdit(str(self.idealIvlFct))
        
        self.setButton = QPushButton('Set')
        self.setButton.pressed.connect(self.setPressed)
        
        # We can calculate this now that the GUI exists.
        self.updateIdealIvlFct()
        
        self.layout.addWidget(self.periodLbl, 0, 0)
        self.layout.addWidget(self.periodCombo, 0, 1)
        self.layout.addWidget(self.optionsGroupLbl, 1, 0)
        self.layout.addWidget(self.optionsGroupInput, 1, 1)
        self.layout.addWidget(self.currentIvlFctLbl, 2, 0)
        self.layout.addWidget(self.currentIvlFctInput, 2, 1)
        self.layout.addWidget(self.targetRetentionLbl, 3, 0)
        self.layout.addWidget(self.targetRetentionSpin, 3, 1)
        self.layout.addWidget(self.currentRetentionLbl, 4, 0)
        self.layout.addWidget(self.currentRetentionInput, 4, 1)
        if self.currentRetention == 100:
            self.layout.addWidget(self.errorLbl, 5, 0, 1, 2)
        self.layout.addWidget(self.newIvlFctLbl, 6, 0)
        self.layout.addWidget(self.newIvlFctInput, 6, 1)
        self.layout.addWidget(self.setButton, 7, 0)
        
    def periodChanged(self, newPeriod):
        self.currentRetention =  calcCurrentRetention(self.deck['id'], self.periods[newPeriod])
        self.currentRetentionInput.setText(str(self.currentRetention)+'%')
        self.updateIdealIvlFct()
        
    def setPressed(self):
        self.optionsGroup['rev']['ivlFct'] = float(self.newIvlFctInput.text())
        mw.col.decks.save(self.optionsGroup)
        showInfo('Set')
        self.currentIvlFct = float(self.newIvlFctInput.text())
        self.currentIvlFctInput.setText(self.newIvlFctInput.text())
        self.updateIdealIvlFct()
        
    def updateIdealIvlFct(self):
        # If current retention is 100, logCurrent will be zero, leading to divbyzero.
        if self.currentRetention == 100:
            self.idealIvlFct = 1
        else:
            logCurrent = math.log(self.currentRetention/100, 10)
            logDesired = math.log(self.targetRetentionSpin.value()/100, 10)
            self.idealIvlFct = round(self.currentIvlFct * logDesired / logCurrent, 2)
        self.newIvlFctInput.setText(str(self.idealIvlFct))
       
    def targetRetentionChanged(self, newtargetRetention):
        self.targetRetention = newtargetRetention
        self.updateIdealIvlFct()

class Display(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)
        self.stack = QStackedWidget()
        self.deckInfo = mw.col.decks.all_names_and_ids(include_filtered=False)
        self.decks = [mw.col.decks.get(d.id) for d in self.deckInfo]
        
        self.leftList = QListWidget()
        for deck in self.decks:
            QListWidgetItem(deck['name'], self.leftList)
            self.stack.addWidget(StackWidget(deck))
            
        self.layout.addWidget(self.leftList)
        self.layout.addWidget(self.stack)
        
        self.leftList.currentRowChanged.connect(self.display)

    def display(self, i):
        self.stack.setCurrentIndex(i)

# Taken from True Retention
def calcCurrentRetention(did, span):
    span = (mw.col.sched.dayCutoff-86400*span)*1000
    flunked, passed = mw.col.db.first("""
    select
    sum(case when ease = 1 and type == 1 then 1 else 0 end), /* flunked */
    sum(case when ease > 1 and type == 1 then 1 else 0 end) /* passed */
    from revlog where id > ? and cid in (select id from cards where did = """ + str(did) + """)""", span, )
    flunked = flunked or 0
    passed = passed or 0
    try:
        return (passed/float(passed+flunked)*100)
    except ZeroDivisionError:
        return 100.0

def showConfig() -> None:
    mw.w = d = Display()
    d.show()

def addConfigButton():
    action = QAction("AutoIntervalModifier", mw)
    qconnect(action.triggered, showConfig)
    mw.form.menuTools.addAction(action)

addConfigButton()