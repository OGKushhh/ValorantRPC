import sys
import subprocess
import os

REQUIRED_PACKAGES = [
    'urllib3',
    'iso8601',
    'flask_cors',  # Flask_Cors s'importe comme flask_cors
    'requests',
    'pypresence',
    'valclient',
    'pystray',
    'pyperclip',
    'cursor',
    'psutil',
    'flask',  # Flask s'importe comme flask
    'InquirerPy',
    'PIL',  # Pillow s'importe comme PIL
    'websockets',
]

# Mapping des noms d'import vers les noms de paquets pip
PACKAGE_MAPPING = {
    'flask_cors': 'Flask_Cors',
    'flask': 'Flask',
    'PIL': 'Pillow',
}

def check_dependencies():
    """Vérifie si toutes les dépendances sont installées."""
    missing = []
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package)
        except ImportError:
            # Utiliser le nom du paquet pip si différent
            pip_name = PACKAGE_MAPPING.get(package, package)
            missing.append(pip_name)
    
    return missing

def install_all_dependencies():
    """Installe toutes les dépendances depuis requirements.txt. Retourne True si succès."""
    requirements_path = get_requirements_path()
    if not os.path.exists(requirements_path):
        return False
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", requirements_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (subprocess.CalledProcessError, Exception):
        return False

def _is_frozen():
    """True si l'app tourne en exe PyInstaller (pas besoin de vérifier les deps)."""
    return getattr(sys, 'frozen', False)


def get_requirements_path():
    """Chemin vers requirements.txt (depuis la racine du projet ou du exe)."""
    if _is_frozen():
        # Exe : à côté de l'exécutable
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, "requirements.txt")


def install_package(pip_name):
    """Installe un seul paquet pip. Retourne True si succès."""
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", pip_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (subprocess.CalledProcessError, Exception):
        return False


def verify_and_install():
    """Vérifie et installe les dépendances si nécessaire."""
    if _is_frozen():
        # Exe packagé : tout est inclus, pas de vérification pip
        return True, []
    missing = check_dependencies()
    if missing:
        return False, missing
    return True, []
