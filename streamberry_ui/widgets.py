import typing
import gzip
from typing import Union

from PyQt6 import QtGui
from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QMimeData, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QDrag, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

# --------------------------------------------------------------------------------------

FILE_TAG: bytes = "sbconf01".encode(encoding="UTF-8")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("StreamBerry UI")
        self.tabContainer = TabsContainer(self)
        self.statusBar().showMessage("Ready")
        self.setCentralWidget(self.tabContainer)

        mainMenu = MainMenu(self)
        self.setMenuBar(mainMenu)
        mainMenu.saveConfigSignal.connect(self.saveConfig)
        mainMenu.loadConfigSignal.connect(self.loadConfig)

    def saveConfig(self) -> None:
        path = QFileDialog.getSaveFileName(
            self, "Save configuration", "", "StreamBerry config (*.sbconf)"
        )
        if path != ("", ""):
            self.statusBar().showMessage("Saving...")
            with gzip.open(path[0], "wb") as file:
                tag = FILE_TAG
                file.write(tag)
                self.tabContainer.saveTo(file)
                file.write(bytearray([0xFF]))
                self.statusBar().showMessage("Saved.")

    def loadConfig(self) -> None:
        path = QFileDialog.getOpenFileName(
            self, "Load configuration", "", "StreamBerry config (*.sbconf)"
        )
        if path != ("", ""):
            self.statusBar().showMessage("Loading...")
            with gzip.open(path[0], "rb") as file:
                try:
                    tag = file.read(len(FILE_TAG))
                    if tag == FILE_TAG:
                        self.tabContainer.loadFrom(file)
                        _endOfFileMarker = file.read(1)[0]
                        if _endOfFileMarker == 0xFF:
                            pass
                        else:
                            pass
                        self.statusBar().showMessage("Loaded.")
                    else:
                        self.statusBar().showMessage("Not a valid config file")
                except gzip.BadGzipFile:
                    self.statusBar().showMessage("Not a valid config file")
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Icon.Critical)
                    msg.setText("Not a valid config file")
                    #msg.setInformativeText("This is additional information")
                    msg.setWindowTitle("An error occured")
                    #msg.setDetailedText("The details are as follows:")
                    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                    retval = msg.exec()
                    print(f"value of pressed message box button: {retval}")


# --------------------------------------------------------------------------------------


class MainMenu(QMenuBar):

    loadConfigSignal = pyqtSignal(int, name="Load config")
    saveConfigSignal = pyqtSignal(int, name="Save config")

    def __init__(self, parent: typing.Optional[QWidget]) -> None:
        super().__init__(parent=parent)

        loadConfigAction = QAction(QIcon("load.png"), "&Open", self)
        loadConfigAction.setShortcut("Ctrl+O")
        loadConfigAction.setStatusTip("Open a configuration file")
        loadConfigAction.triggered.connect(self.loadConfigSignal.emit)

        saveConfigAction = QAction(QIcon("save.png"), "&Save", self)
        saveConfigAction.setShortcut("Ctrl+S")
        saveConfigAction.setStatusTip("Save the configuration")
        saveConfigAction.triggered.connect(self.saveConfigSignal.emit)

        exitAction = QAction(QIcon("exit.png"), "&Exit", self)
        exitAction.setShortcut("Ctrl+Q")
        exitAction.setStatusTip("Exit application")
        exitAction.triggered.connect(QApplication.quit)

        fileMenu = self.addMenu("&File")
        fileMenu.addAction(loadConfigAction)
        fileMenu.addAction(saveConfigAction)
        fileMenu.addSeparator()
        fileMenu.addAction(exitAction)


# --------------------------------------------------------------------------------------


class TabsContainer(QTabWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.loading = False

        self.tab1 = Page(self)

        self.addTab(self.tab1, "Page 1")
        self.addTab(QWidget(), "+")
        self.currentChanged.connect(self.onChange)
        self.tabBarDoubleClicked.connect(self.onDoubleClick)

    def onChange(self, index: int) -> None:
        if not self.loading:
            if index == self.count() - 1:
                self.insertTab(index, Page(self), f"{index + 1}")
                self.setCurrentIndex(index)

    def onDoubleClick(self, index: int) -> None:
        self.removeTab(index)
        for idx in range(self.count() - 1):
            self.setTabText(idx, f"{'Page ' if not idx else ''}{idx + 1}")

    def saveTo(self, file: gzip.GzipFile) -> None:
        # Iterate over every tab
        for idx in range(self.count() - 1):
            page: Page = self.widget(idx)  # type: ignore
            file.write(bytearray([0x01, idx]))
            page.saveTo(file)
            file.write(bytearray([0xFE]))

    def loadFrom(self, file: gzip.GzipFile) -> None:
        # First we need to remove any existing page.
        self.loading = True
        for _ in range(self.count() - 1):
            self.removeTab(0)

        # Then we reset our page number
        _currentPage = 0

        # Now we check for a page marker in the file
        _done: bool = False
        while not _done:
            _pageMarker = file.peek(1)[0]
            if _pageMarker == 0x01:
                file.read(1)
                # Good, now let's check that we're at the correct page.
                _pageNumber = file.read(1)[0]
                if _pageNumber == _currentPage:
                    # All good ! We can create the empty page
                    _newPage = Page(self)
                    self.insertTab(
                        _currentPage,
                        _newPage,
                        f"{'Page ' if _currentPage == 0 else ''}{_currentPage + 1}",
                    )
                    _newPage.loadFrom(file)
                    _endOfPageMarker = file.read(1)[0]
                    if _endOfPageMarker == 0xFE:
                        _currentPage += 1
                    else:
                        pass
            else:
                _done = True

        self.loading = False
        self.setCurrentIndex(0)


# --------------------------------------------------------------------------------------


class Page(QWidget):
    def __init__(self, parent: typing.Optional["QWidget"]) -> None:
        super().__init__(parent=parent)
        self.setLayout(QVBoxLayout(self))
        self.layout().setContentsMargins(10, 10, 10, 10)
        self.layout().setSpacing(10)

        grid = QWidget(self)
        self.gridLayout = QGridLayout()
        grid.setLayout(self.gridLayout)
        self.gridLayout.setContentsMargins(3, 0, 3, 0)

        for row in range(3):
            for column in range(5):
                dropTarget = DropTarget()
                self.gridLayout.addWidget(dropTarget, row, column)

        self.layout().addWidget(grid)

    def saveTo(self, file: gzip.GzipFile) -> None:
        layout = self.gridLayout
        # Iterate over every button on the page.
        for row in range(3):
            for column in range(5):
                item = layout.itemAtPosition(row, column)
                dropTarget: DropTarget = item.widget()  # type: ignore
                if dropTarget.pixmap() is not None:
                    pixmap: QPixmap = dropTarget.pixmap()  # type: ignore
                    byteArray = QByteArray()
                    buffer = QBuffer(byteArray)
                    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                    saved = pixmap.save(buffer, "png")
                    if saved:
                        pixmapBytes = byteArray.data()
                        file.write(bytearray([0x02, row, column]))
                        file.write(len(pixmapBytes).to_bytes(4, "big"))
                        file.write(pixmapBytes)
                        file.write(bytearray([0xFD]))

    def loadFrom(self, file: gzip.GzipFile) -> None:
        # Check the icon marker
        _done: bool = False
        while not _done:
            iconMarker = file.peek(1)[0]
            if iconMarker == 0x02:
                file.read(1)
                buffer = file.read(2)
                row = buffer[0]
                column = buffer[1]
                buffer = file.read(4)
                length = int.from_bytes(buffer, "big")
                buffer = file.read(length)
                pixmap = QPixmap()
                loaded = pixmap.loadFromData(buffer, "png")
                if loaded:
                    item = self.gridLayout.itemAtPosition(row, column)
                    dropTarget: DropTarget = item.widget()  # type: ignore
                    dropTarget.setPixmap(pixmap)

                endOfIconMaker = file.read(1)[0]
                if endOfIconMaker == 0xFD:
                    pass
                else:
                    pass
            else:
                _done = True

# --------------------------------------------------------------------------------------

class DropTarget(QLabel):

    _pixmap: Union[QPixmap, None] = None

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("border: 2px dashed #aaa;")
        self.setPixmap(None)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._pixmap is None:
            return
        if event.buttons() != Qt.MouseButton.LeftButton:
            return
        mimeData = QMimeData()
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        self._pixmap.save(buffer, "PNG")
        mimeData.setData("application/x-dnditemdata", data)

        drag = QDrag(self)
        drag.setMimeData(mimeData)
        drag.setPixmap(self._pixmap)
        drag.setHotSpot(event.position().toPoint() - self.rect().topLeft())  # type: ignore
        dropAction = drag.exec()
        if dropAction == Qt.DropAction.MoveAction:
            self.setPixmap(None)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._pixmap is not None:
            print(f"mousePressEvent !")
        return super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._pixmap is not None:
            self.setPixmap(None)
        return super().mouseDoubleClickEvent(event)

    def setPixmap(self, pixmap: Union[QtGui.QPixmap, None]) -> None:
        self._pixmap = pixmap
        if pixmap is None:
            return super().setPixmap(QPixmap("assets/button_empty.png"))

        return super().setPixmap(pixmap)

    def pixmap(self) -> Union[QPixmap, None]:
        return self._pixmap

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasImage:
            event.accept()
            self.setStyleSheet("border: 2px dashed #aaa; background-color: #aaa;")
        else:
            event.ignore()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:
        if event.source is None:
            event.accept()
        return super().dragMoveEvent(event)

    def dragLeaveEvent(self, event: QtGui.QDragLeaveEvent) -> None:
        self.setStyleSheet("border: 2px dashed #aaa;")
        return super().dragLeaveEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        if event.mimeData().hasFormat("x-special/gnome-icon-list") and self._pixmap is None:
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            filePath = event.mimeData().urls()[0].toLocalFile()
            pixmap = QPixmap(filePath)
            pixmap = pixmap.scaled(150, 130, Qt.AspectRatioMode.KeepAspectRatio)
            self.setPixmap(pixmap)
            self.setStyleSheet("border: 2px dashed #aaa;")
        elif event.mimeData().hasFormat("application/x-dnditemdata"):
            if event.source() == self or self._pixmap is not None:
                event.setDropAction(Qt.DropAction.IgnoreAction)
            else:
                event.setDropAction(Qt.DropAction.MoveAction)
                pixmap = QPixmap()
                pixmap.loadFromData(event.mimeData().data("application/x-dnditemdata"))
                self.setPixmap(pixmap)
            self.setStyleSheet("border: 2px dashed #aaa;")
        else:
            event.setDropAction(Qt.DropAction.IgnoreAction)
        event.accept()

        return super().dropEvent(event)
