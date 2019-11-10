from PyQt5 import QtWidgets, QtGui, QtCore


class ResStationsViewer(QtWidgets.QFrame):
    def __init__(self, RS):
        super(ResStationsViewer, self).__init__()
        self.RS = RS
        self.setLayout(QtWidgets.QVBoxLayout())

        title = QtWidgets.QLabel()
        title.setText("Reservation Stations:")
        self.layout().addWidget(title)

        self.rs_table = QtWidgets.QTableWidget()
        self.rs_table.setColumnCount(10)
        self.rs_table.verticalHeader().setVisible(False)
        self.rs_table.setHorizontalHeaderLabels(
            ['Cycles Left', 'Tag', 'Busy', 'Instruction', 'Vj', 'Vk', 'Qj', 'Qk', 'A', 'Result']
        )
        self.rs_table.horizontalHeader().setStretchLastSection(True) # setResizeMode(QtWidgets.QTableWidget.QHeaderView.Stretch)
        self.rs_table.setFont(QtGui.QFont('monospace'))

        self.layout().addWidget(self.rs_table)
        self.setMinimumHeight(300)

        self.load_contents()



    def load_contents(self):
        self.rs_table.setRowCount(0)
        self.rs_table.setRowCount(len(self.RS))

        for i, r in enumerate(self.RS):
            self.rs_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(r.time_remaining) if r.time_remaining is not None else ''))
            self.rs_table.setItem(i, 1, QtWidgets.QTableWidgetItem(r.name))
            self.rs_table.setItem(i, 2, QtWidgets.QTableWidgetItem('Yes' if r.busy else 'No'))
            self.rs_table.setItem(i, 3, QtWidgets.QTableWidgetItem(str(r.instruction) if r.instruction is not None else ''))
            self.rs_table.setItem(i, 4, QtWidgets.QTableWidgetItem(r.Vj))
            self.rs_table.setItem(i, 5, QtWidgets.QTableWidgetItem(r.Vk))
            self.rs_table.setItem(i, 6, QtWidgets.QTableWidgetItem(r.Qj))
            self.rs_table.setItem(i, 7, QtWidgets.QTableWidgetItem(r.Qk))
            self.rs_table.setItem(i, 8, QtWidgets.QTableWidgetItem(str(r.A) if r.A is not None else ''))
            self.rs_table.setItem(i, 9, QtWidgets.QTableWidgetItem(str(r.result) if r.result is not None else ''))

        # self.rs_table.setMaximumHeight(
        #     self.rs_table.horizontalHeader().height()
        #     + self.rs_table.rowHeight(0)
        #     + self.rs_table.horizontalScrollBar().height()
        # )

        # self.rs_table.resizeColumnsToContents()
