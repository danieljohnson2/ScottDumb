import asyncio
import sys

from PySide6.QtWidgets import QApplication


def run(initializer_coro):
    app = QApplication(sys.argv)

    loop = asyncio.new_event_loop()

    def repeated_iteration():
        app.processEvents()
        loop.call_later(0.01, repeated_iteration)

    loop.create_task(initializer_coro)
    repeated_iteration()
    loop.run_forever()
