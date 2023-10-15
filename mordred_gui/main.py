from PyQt6.QtWidgets import QListView, QApplication
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PyQt6.QtCore import QStandardPaths, Qt
from PyQt6.uic import loadUi
from rdkit import Chem
from mordred import Calculator, descriptors
import pandas as pd
import rdkit, PIL
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QWheelEvent
from rdkit.Chem import PandasTools
import multiprocessing
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QCheckBox, QComboBox, QSpinBox, QTextEdit, QLabel, QLineEdit, QGroupBox, QProgressBar, QGridLayout, QGraphicsDropShadowEffect, QSplitter, QFrame, QPlainTextEdit
from PyQt6.QtCore import QStandardPaths, Qt, QThread, pyqtSignal, QPropertyAnimation, QRect
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPalette, QColor
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6 import QtCore
from PyQt6.QtGui import QImage, QPixmap, QPainter
from PIL import ImageQt
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen
from PyQt6.QtWidgets import QWidget, QApplication, QScrollArea, QVBoxLayout, QFrame
from PyQt6.QtWidgets import QWidget, QApplication, QScrollArea, QVBoxLayout, QFrame
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QWheelEvent, QMouseEvent
from PyQt6.QtCore import Qt, QPoint
from PIL import Image, ImageQt
import sys
from PyQt6.QtCore import Qt, QSortFilterProxyModel
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListView, QLineEdit
from biodeg import BioDegDescriptor

class CustomChem():
    def read_molecule_from_file(filename):
        _, file_extension = os.path.splitext(filename)
        file_extension = file_extension.lower()

        if file_extension == '.sdf':
            return Chem.SDMolSupplier(filename)
        elif file_extension == '.mol':
            return [Chem.MolFromMolFile(filename)]
        elif file_extension == '.pdb':
            return [Chem.MolFromPDBFile(filename)]
        elif file_extension == '.mol2':  # Note: RDKit has limited support for MOL2
            return [Chem.MolFromMol2File(filename)]
        elif file_extension == '.smi':
            supplier = Chem.SmilesMolSupplier(filename)
            mols = []
            for mol in supplier:
                if mol is not None:
                    mols.append(mol)
            return mols
        else:
            return None

class DescriptorThread(QThread):
    finished = pyqtSignal()

    def __init__(self, input_file, output_file, ignore_3D, processes, descriptors, mols, parent=None):
        QThread.__init__(self, parent)
        self.input_file = input_file
        self.output_file = output_file
        self.ignore_3D = ignore_3D
        self.processes = processes
        self.descriptors = descriptors
        self.mols = mols

    def read_molecule_from_file(self,filename):
        rv = CustomChem.read_molecule_from_file(filename)
        if rv is None:
            _, file_extension = os.path.splitext(filename)
            file_extension = file_extension.lower()
            QMessageBox.warning(self, "Error", f"Unsupported file extension: {file_extension}")
        return rv

    def run(self):
        descs = [BioDegDescriptor.BioDegDescriptor() if x == BioDegDescriptor.BioDegDescriptor else x for x in self.descriptors]
        calc = Calculator(descs=descs, ignore_3D=self.ignore_3D)
        desc = calc.pandas(self.mols,nproc=self.processes)
        molecule_names = [mol.GetProp('_Name') for mol in self.mols if mol.HasProp('_Name')]
        desc['name'] = molecule_names
        cols = ['name'] + [col for col in desc.columns if col != 'name' and col is not None]
        desc = desc[cols]
        desc.to_csv(self.output_file, index=False)
        self.finished.emit()

class DescriptorsCheckBoxWidget(QWidget):

    def __init__(self,searchBar):
        super().__init__()
        self.allDescriptors = []
        self.allDescriptorsNames = []
        self.allDescriptors.extend(descriptors.all)
        self.allDescriptorsNames.extend(descriptors.__all__)
        self.allDescriptors.append(BioDegDescriptor.BioDegDescriptor)
        self.allDescriptorsNames.append("BioDegDescriptor")
        self.initUI(searchBar)


    def initUI(self,search_bar):
        layout = QVBoxLayout()

        model = QStandardItemModel()
        proxy_model = QSortFilterProxyModel()
        proxy_model.setSourceModel(model)
        proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        for descriptor_name in self.allDescriptorsNames:
            item = QStandardItem(descriptor_name)
            item.setCheckable(True)
            model.appendRow(item)

        list_view = QListView()
        list_view.setModel(proxy_model)

        search_bar.textChanged.connect(proxy_model.setFilterRegularExpression)

        layout.addWidget(list_view)
        self.setLayout(layout)
        
    def getModel(self):
        list_view = self.layout().itemAt(0).widget()
        return list_view.model()
    
    def checkedItemsAsStrings(self):
        t = []
        model = self.getModel()
        for i in range(model.rowCount()):
            index = model.index(i, 0)
            if Qt.CheckState(model.data(index, Qt.ItemDataRole.CheckStateRole)) == Qt.CheckState.Checked:
                t.append(model.data(index))
        return t

    def checkedItemsAsClasses(self):
        descriptor_names = self.checkedItemsAsStrings()
        return [mod for mod in self.allDescriptors if mod.__name__.split('.')[-1] in descriptor_names]
    
    def checkAllItems(self, state):
        model = self.getModel()
        source_model = model.sourceModel()
        for i in range(source_model.rowCount()):
            index = source_model.index(i, 0)
            item = source_model.itemFromIndex(index)
            if state:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)

class MolImageWidget(QWidget):
    def __init__(self, qimage):
        super(MolImageWidget, self).__init__()
        self.qimage = qimage
        self.zoom = 0.5
        self.drag_start_pos = QPoint(0, 0)
        self.view_pos = QPoint(0,0)

    def paintEvent(self, event):
        painter = QPainter(self)
        scaled_pixmap = QPixmap.fromImage(self.qimage).scaled(
            int(self.qimage.width() * self.zoom), 
            int(self.qimage.height() * self.zoom)
        )
        painter.drawPixmap(self.view_pos.x(), self.view_pos.y(), scaled_pixmap)
        self.pixmap = scaled_pixmap
    
    def wheelEvent(self, event: QWheelEvent):
        degrees = event.angleDelta().y() / 8
        steps = degrees / 15
        self.zoom += steps * 0.1
        self.zoom = max(0.1, self.zoom)  # Ensure zoom is not less than 0.1
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            diff = self.drag_start_pos - event.pos()
            self.view_pos -= diff
            self.drag_start_pos = event.pos()
            self.update()

class MolViewWidget(QScrollArea):
    def __init__(self, layout):
        super().__init__()
        self.setFrameShape(QFrame.Shape.Box)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.image_widget = None
        layout.addWidget(self)
    
    def resizeEvent(self, event):
        if self.image_widget:
            self.image_widget.resize(self.size())

    def set_mols(self, mols):
        if 0 < len(mols):
            img=ImageQt.toqimage(rdkit.Chem.Draw.MolsToGridImage(mols,molsPerRow=4,subImgSize=(200,200),legends=[x.GetProp("_Name") for x in mols]))
            self.image_widget = MolImageWidget(img)
            self.setWidget(self.image_widget)
            self.setWidgetResizable(True)
        else:
            self.image_widget = None
            widget = self.takeWidget()
            if widget is not None:
                widget.deleteLater()

    def save(self,outname=os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation),"/export.png")):
        if self.image_widget:
            file_name, _ = QFileDialog.getSaveFileName(self, "Save Image", outname, "Images (*.png);;All Files (*)", options=QFileDialog.Option.DontUseNativeDialog)
            if file_name:
                self.image_widget.pixmap.save(file_name)
        else:
            QMessageBox.warning(self, "Error", f"No molecules loaded")


class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi(os.path.join(os.path.dirname(__file__), "molecular_descriptors.ui"), self)

        self.input_button.clicked.connect(self.input_molecules)
        self.output_button.clicked.connect(self.output_file)
        self.compute_button.clicked.connect(self.compute_descriptors)
        self.preview_button.clicked.connect(self.preview_result)
        self.input_file_preview_copy.clicked.connect(self.input_file_preview_copy_clicked)
        self.input_smiles_molecule_button.clicked.connect(self.input_smiles_molecule_button_clicked)
        self.input_file_molecule_preview_export.clicked.connect(self.input_file_molecule_preview_export_clicked)
        self.output_path.setText(os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation),'molecular_descriptors.csv'))
        self.processes_input.setValue(multiprocessing.cpu_count())
        self.descriptors_checkbox_widget = DescriptorsCheckBoxWidget(self.compute_settings_descriptor_search)
        self.compute_settings_descriptor_check_box.addWidget(self.descriptors_checkbox_widget)
        self.thread = None
        self.compute_settings_descriptor_select_all.stateChanged.connect(self.descriptors_checkbox_widget.checkAllItems)
        self.inputMoleculePreview = MolViewWidget(self.input_file_molecule_preview)
        self.loadDemoDefaults()

    def loadDemoDefaults(self):
        self.input_smiles_molecule_text.setText("O=C1CCCCCO1")
        self.input_smiles_molecule_button_clicked()
   
    def input_smiles_molecule_button_clicked(self):
        smiles = self.input_smiles_molecule_text.text()
        mols = []
        for smile in smiles.split(';'):
            if 0 < len(smile):
                mol = Chem.MolFromSmiles(smile)
                if mol is None:
                    QMessageBox.warning(self, "Error", f"Invalid SMILES")
                else:
                    mol.SetProp('_Name',f'{smile}')
                mols.append(mol)
        self.set_mols(mols)

    def set_mols(self,mols):
        self.mols = mols
        self.inputMoleculePreview.set_mols(self.mols)

    def read_molecule_from_file(self,filename):
        rv = CustomChem.read_molecule_from_file(filename)
        if rv is None:
            _, file_extension = os.path.splitext(filename)
            file_extension = file_extension.lower()
            QMessageBox.warning(self, "Error", f"Unsupported file extension: {file_extension}")
        return rv
    
    def load_input_file_in_gui(self,file_name):
        if file_name:
            self.input_path.setText(file_name)
            with open(file_name, 'r') as f:
                self.input_file_preview_text.setPlainText(f.read())
            self.set_mols(self.read_molecule_from_file(file_name))
            self.inputMoleculePreview.set_mols(self.mols)
        
    def input_molecules(self):
        options = QFileDialog.Option.ReadOnly
        file_name, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "", "Molecule Files (*.sdf *.mol *.pdb *.mol2 *.smi)", options=options)
        self.load_input_file_in_gui(file_name)
 

    def output_file(self):
        options = QFileDialog.Option.DontUseNativeDialog
        file_name, _ = QFileDialog.getSaveFileName(self, "QFileDialog.getSaveFileName()", self.output_path.text(), "CSV Files (*.csv)", options=options)
        if file_name:
            self.output_path.setText(file_name)

    def input_file_preview_copy_clicked(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.input_file_preview_text.toPlainText())

    def input_file_molecule_preview_export_clicked(self):
        base_name = os.path.basename(self.input_path.text())
        file_name_without_extension = os.path.splitext(base_name)[0]
        self.inputMoleculePreview.save(
            os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation),file_name_without_extension + ".png")
        )

    def compute_descriptors(self):
        if self.mols is None or len(self.mols) == 0 or not self.output_path.text():
            QMessageBox.warning(self, "Warning", "Please input at least one molecule and an output file.")
            return

        self.compute_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.feedback_label.setText('Computing descriptors...')

        self.thread = DescriptorThread(self.input_path.text(), self.output_path.text(), not self.checkbox.isChecked(), self.processes_input.value(), self.descriptors_checkbox_widget.checkedItemsAsClasses(), self.mols)
        self.thread.finished.connect(self.on_finished)
        self.thread.start()

    def on_finished(self):
        self.compute_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.feedback_label.setText(f'Success! Descriptors saved to {self.output_path.text()}')
        if self.result_preview.isVisible():
            self.update_preview_result()

    def update_preview_result(self):
        with open(self.output_path.text(), 'r') as f:
            self.result_preview.setPlainText(f.read())

    def preview_result(self):
        self.update_preview_result()
        if not self.result_preview.isVisible():
            animation = QPropertyAnimation(self.result_preview, b"geometry")
            animation.setDuration(1000)
            animation.setStartValue(QRect(0, 0, 0, 0))
            animation.setEndValue(QRect(0, 0, int(self.width() / 2), self.height()))
            animation.start()
            self.result_preview.show()

def main():
    app = QApplication([])
    window = MyApp()
    window.show()
    app.exec()

if __name__ == '__main__':
    main()
