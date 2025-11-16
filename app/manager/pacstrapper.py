import subprocess


from pathlib import Path



class RootFSPackageInstaller:
    def __init__(self, rootfs_path: str, arch: str = "x86_64", ignore_missing: bool = False):
        self.rootfs_path = Path(rootfs_path)
        self.arch = arch
        self.pacman_cache = Path("/var/cache/pacman/pkg")
        self.ignore_missing = ignore_missing # NEU: Option speichern

        if not self.rootfs_path.exists():
            raise FileNotFoundError(f"RootFS-Pfad existiert nicht: {self.rootfs_path}")



    def _run_host_command(self, cmd):
        """Führt einen Befehl auf dem Host aus"""
        print(f"[INFO] Führe auf Host aus: {' '.join(cmd)}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Befehl fehlgeschlagen: {' '.join(cmd)}\n{result.stderr}")
        return result.stdout.strip()
    
    

    def _resolve_dependencies(self, packages):
        """Ermittelt alle Abhängigkeiten ohne Versionsnummern."""
        all_packages = set()
        to_process = set(packages)
        successful_packages = set() # Nur erfolgreich gefundene Pakete

        while to_process:
            pkg = to_process.pop()
            if pkg in all_packages:
                continue
            
            try:
                # pacman -Si liefert Abhängigkeiten
                output = self._run_host_command(["pacman", "-Si", pkg])
                all_packages.add(pkg) # Füge nur hinzu, wenn erfolgreich gefunden

                for line in output.splitlines():
                    if line.startswith("Depends On"):
                        deps = line.split(":", 1)[1].strip().split()
                        for dep in deps:
                            # Versionsangaben entfernen
                            dep_name = dep.split(">=")[0].split("<=")[0].split("=")[0]
                            if dep_name and dep_name not in all_packages:
                                to_process.add(dep_name)
            
            except RuntimeError as e:
                # NEU: Fehlerbehandlung
                if self.ignore_missing:
                    print(f"[WARN] Paket '{pkg}' nicht gefunden. Wird ignoriert. (Grund: --ignore-missing gesetzt)")
                    # Fahren Sie hier einfach mit der nächsten Iteration fort (continue)
                else:
                    raise e # Wenn --ignore-missing nicht gesetzt ist, brechen wir ab.

        return list(all_packages) # Gibt nun nur erfolgreich aufgelöste Pakete zurück



    def _download_package(self, package_name):
        """Lädt das Paket für die Zielarchitektur vom Host"""
        print(f"[INFO] Lade Paket: {package_name} für Arch {self.arch}")
        cmd = ["pacman", "-Sw", "--noconfirm", "--arch", self.arch, package_name]
        
        try:
            self._run_host_command(cmd)
            return True # Erfolgreich heruntergeladen
        except RuntimeError as e:
            # NEU: Fehlerbehandlung
            if self.ignore_missing and "Fehler: Ziel nicht gefunden" in e.args[0]:
                 print(f"[WARN] Download von Paket '{package_name}' fehlgeschlagen. Wird übersprungen. (Grund: --ignore-missing gesetzt)")
                 return False # Herunterladen fehlgeschlagen, weitermachen
            else:
                raise e # Abbruch, wenn --ignore-missing nicht gesetzt ist oder es ein anderer Fehler war



    def _extract_package(self, package_name):
        """Extrahiert das Paket in das RootFS, nur echte Pakete ohne Signaturen"""
        pkg_files = sorted(
            [f for f in self.pacman_cache.glob(f"{package_name}-*.pkg.tar.*") if not f.suffix.endswith(".sig")],
            key=lambda f: f.stat().st_mtime
        )
        
        if not pkg_files:
            raise FileNotFoundError(f"Kein heruntergeladenes Paket gefunden für: {package_name}")

        pkg_file = pkg_files[-1]  # Das neueste Paket
        print(f"[INFO] Extrahiere {pkg_file} nach {self.rootfs_path}")
        cmd = ["bsdtar", "-xpf", str(pkg_file), "-C", str(self.rootfs_path)]
        self._run_host_command(cmd)
        
        

    def install_packages(self, packages: list):
        """Installiert alle Pakete inkl. Abhängigkeiten"""
        
        # NEU: Wir brauchen eine Liste der Pakete, die erfolgreich aufgelöst wurden
        print(f"[INFO] Ermittele Abhängigkeiten für Pakete: {', '.join(packages)}")
        all_packages = self._resolve_dependencies(packages)
        print(f"[INFO] Alle Pakete inkl. Abhängigkeiten (zum Versuch der Installation): {', '.join(all_packages)}")
        
        installed_packages = []

        for pkg in all_packages:
            # Nur fortfahren, wenn der Download erfolgreich war (Rückgabewert von _download_package)
            if self._download_package(pkg):
                try:
                    self._extract_package(pkg)
                    installed_packages.append(pkg)
                except (FileNotFoundError, RuntimeError) as e:
                    # Fangen Sie Fehler beim Extrahieren ab, die z.B. auftreten,
                    # wenn der Download-Teil zwar dachte, es sei erfolgreich,
                    # aber das Paket nicht in der Cache ist (sehr selten).
                    if self.ignore_missing:
                        print(f"[WARN] Installation von Paket '{pkg}' fehlgeschlagen/Extraktionsfehler: {e}. Wird übersprungen.")
                    else:
                        raise e

        # NEU: Erfolgsmeldung basierend auf tatsächlich installierten Paketen
        if installed_packages:
            print(f"[SUCCESS] {len(installed_packages)} Pakete inkl. Abhängigkeiten erfolgreich installiert: {', '.join(installed_packages)}")
        else:
            print("[WARN] Es wurden keine Pakete erfolgreich installiert.")
            
            
# if __name__ == "__main__":
#     rootfs_dir = "/home/hexzhen3x7/Development/MetaOS/app/work/build/rootfs"
#     installer = RootFSPackageInstaller(rootfs_dir, arch="x86_64")
#     installer.install_packages(["bash", "nano", "apk-tools"])
