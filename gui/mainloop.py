import asyncio

from gi.repository import GLib, Gio


def run(initializer_coro):
    def on_activate(*args):
        loop.create_task(initializer_coro)

    async def start_application():
        app = Gio.Application()
        app.connect("activate", on_activate)
        app.register()
        app.activate()

    def repeated_iteration():
        while main_context.pending():
            main_context.iteration(False)
        loop.call_later(0.01, repeated_iteration)

    loop = asyncio.new_event_loop()
    main_context = GLib.MainContext.default()
    loop.create_task(start_application())
    repeated_iteration()
    loop.run_forever()
