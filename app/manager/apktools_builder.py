import os
import subprocess
import shutil


from pathlib import Path

from core.logger import success, info, warning, error



def build_apk_tools(arch: str, rootfs_dir: str, source_dir: str = "apk-tools_src"):
    """
    Klont, kompiliert (statisch) und installiert apk-tools in das Ziel-RootFS.

    :param arch: Die Zielarchitektur ('x86_64' oder 'aarch64').
    :param rootfs_dir: Der Pfad zum BusyBox-Ziel-RootFS.
    :param source_dir: Der lokale Ordner, in den das Repository geklont wird.
    """
    
    
    info(f"🏗️ Starte den Build-Prozess für apk-tools ({arch})...")
    
    # --- Pfade definieren ---
    repo_url = "https://github.com/alpinelinux/apk-tools"
    rootfs_path = Path(rootfs_dir)
    build_dir = Path(source_dir) / "build_static"
    
    # --- 1. Toolchain und Cross File definieren ---
    if arch == 'aarch64':
        compiler_prefix = 'aarch64-linux-gnu'
        cross_file_content = f"""
[binaries]
c = '{compiler_prefix}-gcc'
cpp = '{compiler_prefix}-g++'
ar = '{compiler_prefix}-ar'
strip = '{compiler_prefix}-strip'

[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
"""
    elif arch == 'x86_64':
        # Für x86_64 verwenden wir oft den systemeigenen Compiler, 
        # aber wir definieren ihn explizit für eine Cross-Umgebung.
        compiler_prefix = 'x86_64-linux-gnu'
        cross_file_content = f"""
[binaries]
c = '{compiler_prefix}-gcc'
cpp = '{compiler_prefix}-g++'
ar = '{compiler_prefix}-ar'
strip = '{compiler_prefix}-strip'

[host_machine]
system = 'linux'
cpu_family = 'x86_64'
cpu = 'x86_64'
endian = 'little'
"""
    else:
        raise ValueError(f"Unbekannte Architektur: {arch}. Unterstützt: 'aarch64', 'x86_64'.")

    # Cross File erstellen
    cross_file_path = Path(source_dir) / f"crossfile-{arch}.txt"
    cross_file_path.write_text(cross_file_content)
    info(f"   ☑️ Cross File ({cross_file_path}) erstellt.")

    try:
        # --- 2. Klonen des Repositorys ---
        if not Path(source_dir).exists():
            info(f"   ⬇️ Klone Repository in {source_dir}...")
            subprocess.run(['git', 'clone', '--depth', '1', repo_url, source_dir], check=True)
            info("   ☑️ Klonen abgeschlossen.")
        else:
            info(f"   ℹ️ Quellverzeichnis {source_dir} existiert bereits, überspringe Klonen.")
        
        os.chdir(source_dir)
        
        # --- 3. Meson Konfiguration (statisch) ---
        info("   ⚙️ Konfiguriere Meson für statischen Build...")
        meson_setup_cmd = [
            'meson', 'setup', '--reconfigure', 
            '--cross-file', str(cross_file_path.name), 
            '-Ddefault_library=static', 
            '-Dprefer_static=true', 
            '-Dc_link_args=-static', 
            str(build_dir.name)
        ]
        subprocess.run(meson_setup_cmd, check=True)
        info("   ☑️ Meson Konfiguration abgeschlossen.")

        # --- 4. Kompilierung mit Ninja ---
        info("   🔨 Kompiliere mit Ninja...")
        subprocess.run(['ninja', '-C', str(build_dir.name)], check=True)
        info("   ☑️ Kompilierung abgeschlossen.")
        
        # --- 5. Installation in das Ziel-RootFS ---
        info(f"   📦 Installiere in Ziel-RootFS: {rootfs_path}...")
        
        # Pfad zum kompilierten Binary
        apk_binary_path = build_dir / "src" / "apk"
        target_sbin_path = rootfs_path / "sbin"
        target_apk_path = target_sbin_path / "apk"
        
        # Sicherstellen, dass die Zielverzeichnisse existieren
        target_sbin_path.mkdir(parents=True, exist_ok=True)
        (rootfs_path / "etc" / "apk").mkdir(parents=True, exist_ok=True)
        
        # Kopieren des statischen Binaries
        shutil.copy(apk_binary_path, target_apk_path)
        os.chmod(target_apk_path, 0o755) # Ausführbar machen
        
        # Minimal benötigte Konfigurationsdatei (Beispiel)
        if not (rootfs_path / "etc" / "apk" / "repositories").exists():
            info("   📝 Erstelle /etc/apk/repositories...")
            # Alpine Edge ist oft die aktuellste Quelle für arm64/x86_64
            repo_content = "http://dl-cdn.alpinelinux.org/alpine/edge/main\n"
            (rootfs_path / "etc" / "apk" / "repositories").write_text(repo_content)
            
        success("   ✅ Installation abgeschlossen. 'apk' ist nun im Ziel-RootFS verfügbar.")

    except subprocess.CalledProcessError as e:
        error(f"❌ Fehler während der Ausführung eines Befehls: {e}")
        error(f"Ausgabe: {e.output}")
    except FileNotFoundError as e:
        error(f"❌ Fehler: Eines der benötigten Tools (git, meson, ninja oder die Toolchain) wurde nicht gefunden: {e}")
    finally:
        os.chdir("..") # Zurück ins Ausgangsverzeichnis

# --- Beispiel für die Verwendung ---
# if __name__ == "__main__":
#     # BITTE PASSEN SIE DIESE PFADE AN IHRE UMGEBUNG AN!
#     ARCH = 'aarch64' # oder 'x86_64'
#     ROOTFS_PATH = './my_busybox_rootfs' # Beispielpfad

#     # Stellen Sie sicher, dass das Ziel-RootFS-Verzeichnis existiert (oder BusyBox ist dort installiert)
#     Path(ROOTFS_PATH).mkdir(exist_ok=True) 

#     build_apk_tools(arch=ARCH, rootfs_dir=ROOTFS_PATH)