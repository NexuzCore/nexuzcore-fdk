import subprocess
import os
import argparse
import shutil


from pathlib import Path

from utils.execute import run_command_live

from core.logger import success, info, warning, error


# --- Konfiguration ---
OPKG_REPO = "https://git.yoctoproject.org/opkg"
OPKG_DIR = "opkg_source"

def run_command(command, cwd=None, env=None):
    """Führt einen Shell-Befehl aus und prüft auf Fehler."""
    info(f"-> Ausführen: {' '.join(command)}")
    try:
        # check=True stellt sicher, dass eine CalledProcessError ausgelöst wird, wenn der Befehl fehlschlägt.
        subprocess.run(
            command,
            check=True,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        success("   ✅ Erfolgreich.")
    except subprocess.CalledProcessError as e:
        error(f"   ❌ Fehler beim Ausführen des Befehls: {e.cmd}")
        error(f"   Fehlerausgabe:\n{e.output}")
        # Beendet das Skript bei einem Fehler
        exit(1)
        
        
        

def build_opkg(arch: str, rootfs_dir: Path):
    """
    Klont, kompiliert (cross) und installiert opkg für die gegebene Architektur.
    
    :param arch: Zielarchitektur ('x86_64' oder 'arm64').
    :param rootfs_path: Pfad zum Ziel-Root-Dateisystem.
    """
    
    info(f"🚀 Starte den Cross-Build für opkg (Architektur: {arch}, Ziel: {rootfs_dir})")

    # 1. Toolchain-Setup für Cross-Compilation
    # HINWEIS: Die tatsächlichen Namen der Cross-Compiler-Präfixe variieren!
    # Dies sind typische Beispiele, die auf Ihrem System angepasst werden müssen.
    if arch == "x86_64":
        # Für native Kompilierung auf x86_64 ist oft kein expliziter Präfix nötig, 
        # aber für eine saubere Cross-Compilation (z.B. wenn Host != Ziel) wird es definiert.
        compiler_prefix = "x86_64-linux-gnu" # Oder lassen Sie es leer für native Builds
    elif arch == "arm64":
        # Typischer Präfix für ARM64 (AArch64) Cross-Compiler
        compiler_prefix = "aarch64-linux-gnu"
    else:
        raise ValueError(f"Nicht unterstützte Architektur: {arch}. Unterstützt: x86_64, arm64.")

    # Der vollständige Name des Cross-Compilers (z.B. aarch64-linux-gnu-gcc)
    cross_compiler = f"{compiler_prefix}-gcc"
    
    # Pfad zur Umgebungsvariable (inklusive der aktuellen Umgebung)
    # Wichtig: Der Cross-Compiler muss im PATH verfügbar sein!
    custom_env = os.environ.copy()
    
    # Setzt den Cross-Compiler für das Configure-Skript.
    # WICHTIG: Prüfen Sie, ob diese Variable in Ihrem Build-System korrekt ist!
    custom_env['CC'] = cross_compiler 
    
    # 2. Klonen des Repositorys
    info("\n--- 1. Klonen von opkg ---")
    if os.path.exists(OPKG_DIR):
        info(f"   Ordner '{OPKG_DIR}' existiert bereits. Lösche...")
        shutil.rmtree(OPKG_DIR)
    
    run_command_live(["git", "clone", OPKG_REPO, OPKG_DIR])
    os.chdir(OPKG_DIR)
    
    # 3. Vorbereitung für die Kompilierung (z.B. `autogen.sh` oder `bootstrap`)
    info("\n--- 2. Vorbereitung der Build-Umgebung ---")
    # opkg verwendet `autoreconf` oder `autogen.sh`.
    if os.path.exists("autogen.sh"):
        run_command_live(["sh", "autogen.sh"])
    
    # 4. Konfigurieren
    info("\n--- 3. Konfigurieren (Cross-Compilation) ---")
    # --host: Gibt das Zielsystem an.
    # --prefix: Gibt das Installationsziel innerhalb des Rootfs an (z.B. /usr).
    # --with-default-config-file: Setzt den Pfad zur opkg-Konfigurationsdatei.
    configure_cmd = [
        "./configure",
        f"--host={compiler_prefix}",  # Wichtig für Cross-Compilation
        f"--prefix={rootfs_dir}/usr", # Installiert in /usr im Ziel-Rootfs
        "--disable-gpg",  # Vereinfachung: GPG-Prüfungen deaktivieren
        f"--with-default-config-file={rootfs_dir}/etc/opkg.conf" # Beispiel für Konfigurationspfad
    ]
    
    # Führt configure mit der angepassten Umgebung aus (inkl. CC)
    run_command_live(configure_cmd, env=custom_env)

    # 5. Kompilieren
    info("\n--- 4. Kompilieren ---")
    # -j$(nproc) nutzt alle verfügbaren Kerne für schnelles Kompilieren
    run_command_live(["make", "-j", str(os.cpu_count() or 1)])

    # 6. Installation in das Ziel-Rootfs
    info("\n--- 5. Installation in das Ziel-Rootfs ---")
    # 'DESTDIR' stellt sicher, dass 'make install' in den Pfad von DESTDIR 
    # und nicht in das Root-Dateisystem des Hosts installiert.
    install_cmd = [
        "make",
        f"DESTDIR={rootfs_dir}", 
        "install"
    ]
    run_command_live(install_cmd)

    os.chdir("..")
    success(f"\n🎉 opkg erfolgreich in {rootfs_dir} für {arch} installiert.")

