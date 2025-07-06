import asyncio

from gi.repository import GLib, Gtk


def make_filter(name, pattern):
    """Builds a GTK file-filter conveniently."""
    f = Gtk.FileFilter()
    f.set_name(name)
    f.add_pattern(pattern)
    return f


dialog_error_quark = GLib.quark_to_string(Gtk.DialogError.quark())


def _file_dialog_open_async(dlg, parent):
    ended = asyncio.get_running_loop().create_future()

    def on_ready(dlg, result):
        try:
            file = dlg.open_finish(result)
            ended.set_result(file)
        except GLib.GError as err:
            if (
                err.domain == dialog_error_quark
                and err.code == Gtk.DialogError.DISMISSED
            ):
                ended.set_result(None)
            else:
                ended.set_exception(err)

    dlg.open(parent, None, on_ready)
    return ended


def _file_dialog_save_async(dlg, parent):
    ended = asyncio.get_running_loop().create_future()

    def on_ready(dlg, result):
        try:
            file = dlg.save_finish(result)
            ended.set_result(file)
        except GLib.GError as err:
            if (
                err.domain == dialog_error_quark
                and err.code == Gtk.DialogError.DISMISSED
            ):
                ended.set_result(None)
            else:
                ended.set_exception(err)

    dlg.save(parent, None, on_ready)
    return ended


Gtk.FileDialog.open_async = _file_dialog_open_async
Gtk.FileDialog.save_async = _file_dialog_save_async
