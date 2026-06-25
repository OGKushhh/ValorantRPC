from PIL import Image
from pystray import Icon as icon, Menu as menu, MenuItem as item
import ctypes, os, urllib.request, sys

from .filepath import Filepath
from ..localization.localization import Localizer
from .gui import MainWindow, GUIState

kernel32 = ctypes.WinDLL('kernel32')
user32   = ctypes.WinDLL('user32')
hWnd     = kernel32.GetConsoleWindow()


class Systray:

    def __init__(self, client, config):
        self.client = client
        self.config = config
        self._win   = None   # set in run()

    def run(self):
        Systray.generate_icon()

        # ── spin up the real GUI window ───────────────────────────────────────
        self._win = MainWindow(on_exit_callback=self.exit)
        MainWindow._instance = self._win

        systray_image = Image.open(
            Filepath.get_path(
                os.path.join(Filepath.get_appdata_folder(), 'favicon.ico')))

        systray_menu = menu(
            item('Show / Hide', self._toggle,  default=True),
            item('Reload',      Systray.restart),
            item('Exit',        self.exit),
        )
        self.systray = icon("valorant-rpc", systray_image,
                            "valorant-rpc", systray_menu)

        # Double-click tray icon → toggle window
        self.systray.run()

    # ── tray callbacks ────────────────────────────────────────────────────────

    def _toggle(self, _icon=None, _item=None):
        if self._win:
            self._win.toggle()

    def exit(self, _icon=None, _item=None):
        if self._win:
            self._win.destroy()
        try:
            self.systray.visible = False
            self.systray.stop()
        except Exception:
            pass
        try:
            os._exit(0)
        except Exception:
            pass

    @staticmethod
    def generate_icon():
        try:
            urllib.request.urlretrieve(
                'https://raw.githubusercontent.com/colinhartigan/valorant-rpc/v2/favicon.ico',
                Filepath.get_path(
                    os.path.join(Filepath.get_appdata_folder(), 'favicon.ico')))
        except Exception:
            pass   # use whatever icon is already cached

    @staticmethod
    def restart(_icon=None, _item=None):
        os.execl(sys.executable, os.path.abspath(sys.executable), *sys.argv)
