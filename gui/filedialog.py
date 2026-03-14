import asyncio

from PySide6.QtWidgets import QFileDialog


async def file_dialog_open(parent, title, filters):
    """Opens a file dialog for selecting a file to open.
    Returns the path, or None if cancelled."""
    future = asyncio.get_running_loop().create_future()
    dlg = QFileDialog(parent, title)
    dlg.setNameFilters(filters)
    dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
    dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)

    def on_finished(result):
        if result == QFileDialog.DialogCode.Accepted:
            files = dlg.selectedFiles()
            future.set_result(files[0] if files else None)
        else:
            future.set_result(None)
        dlg.deleteLater()

    dlg.finished.connect(on_finished)
    dlg.open()
    return await future


async def file_dialog_save(parent, title, filters):
    """Opens a file dialog for selecting a file to save.
    Returns the path, or None if cancelled."""
    future = asyncio.get_running_loop().create_future()
    dlg = QFileDialog(parent, title)
    dlg.setNameFilters(filters)
    dlg.setFileMode(QFileDialog.FileMode.AnyFile)
    dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)

    def on_finished(result):
        if result == QFileDialog.DialogCode.Accepted:
            files = dlg.selectedFiles()
            future.set_result(files[0] if files else None)
        else:
            future.set_result(None)
        dlg.deleteLater()

    dlg.finished.connect(on_finished)
    dlg.open()
    return await future
