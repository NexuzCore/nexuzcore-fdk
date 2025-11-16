#!/usr/bin/env python3
import os
from pathlib import Path

from core.logger import info, success, warning, error
from utils.execute import run_command_live

# >>> Deine neuen Utils werden HIER verwendet
from utils.download import download_file, extract_archive, download_and_extract


class APKInstaller:
    """
    Installiert apk-tools in ein RootFS und initialisiert alpine-baselayout.
    Unterstützte Architekturen: x86_64, arm64
    """

    ALPINE_REPO = "https://dl-cdn.alpinelinux.org/alpine/latest-stable"
    ARCH_MAPPING = {
        "x86_64": "x86_64",
        "arm64": "aarch64",
    }

    def __init__(self, rootfs_dir: Path, arch: str):
        self.rootfs_dir = Path(rootfs_dir)
        self.arch = arch

        if arch not in self.ARCH_MAPPING:
            raise ValueError(f"Unsupported architecture: {arch}")

        self.alpine_arch = self.ARCH_MAPPING[arch]

    def install(self):
        """Hauptfunktion zum Installieren von apk in das rootfs"""
        info(f"[APK] Starte Installation für Architektur: {self.arch}")

        apk_static_path = self._download_and_extract_apk_tools()

        if not apk_static_path.exists():
            error("[APK] apk.static wurde nicht gefunden!")
            return False

        self._init_apk_database(apk_static_path)
        self._write_repositories()
        self._install_base_packages(apk_static_path)

        success("[APK] apk-tools erfolgreich in das RootFS installiert!")
        return True

    # -------------------------------------------------------------
    # Schritt 1: apk-tools-static herunterladen und extrahieren
    # -------------------------------------------------------------
    def _download_and_extract_apk_tools(self) -> Path:
        info("[APK] Lade apk-tools-static herunter...")

        # Die URL für STATIC apk-tools ist IMMER gleich, aber arch-spezifisch
        url_main = f"{self.ALPINE_REPO}/main/{self.alpine_arch}/apk-tools-static-latest.apk"
        mirrors = [
            url_main,
            url_main.replace("dl-cdn", "dl-4"),   # Mirror fallback
            url_main.replace("dl-cdn", "dl-2"),
        ]

        download_dir = Path("downloads") / "apk-tools"
        extract_dir = download_dir / f"extracted-{self.arch}"

        # Nutzt deine download_and_extract Funktion!
        apk_extract_path = download_and_extract(
            mirrors,
            dest_dir=download_dir,
            extract_to=extract_dir,
        )

        # apk-tools-static entpackt in sbin/apk.static
        apk_static = apk_extract_path / "sbin" / "apk.static"

        if apk_static.exists():
            info(f"[APK] apk.static gefunden: {apk_static}")
        else:
            error("[APK] apk.static NICHT gefunden!")

        return apk_static

    # -------------------------------------------------------------
    # Schritt 2: APK Datenbank initialisieren
    # -------------------------------------------------------------
    def _init_apk_database(self, apk_static: Path):
        info("[APK] Initialisiere APK Datenbank...")

        run_command_live([
            str(apk_static),
            "-X", f"{self.ALPINE_REPO}/main",
            "--arch", self.alpine_arch,
            "--root", str(self.rootfs_dir),
            "--initdb"
        ])

    # -------------------------------------------------------------
    # Schritt 3: /etc/apk/repositories schreiben
    # -------------------------------------------------------------
    def _write_repositories(self):
        repo_file = self.rootfs_dir / "etc/apk/repositories"
        repo_file.parent.mkdir(parents=True, exist_ok=True)

        info("[APK] Schreibe /etc/apk/repositories...")

        repo_file.write_text(
            f"{self.ALPINE_REPO}/main\n"
            f"{self.ALPINE_REPO}/community\n"
        )

    # -------------------------------------------------------------
    # Schritt 4: Basis-Pakete installieren
    # -------------------------------------------------------------
    def _install_base_packages(self, apk_static: Path):
        info("[APK] Installiere Basis-Pakete (busybox, alpine-baselayout, apk-tools)...")

        run_command_live([
            str(apk_static),
            "-X", f"{self.ALPINE_REPO}/main",
            "--arch", self.alpine_arch,
            "--root", str(self.rootfs_dir),
            "--update-cache",
            "--allow-untrusted",
            "add",
            "alpine-baselayout",
            "busybox",
            "apk-tools"
        ])


# -------------------------------------------------------------
# Standalone-Nutzung
# -------------------------------------------------------------
# if __name__ == "__main__":
#     import argparse

#     parser = argparse.ArgumentParser(description="Install apk into a rootfs")
#     parser.add_argument("--rootfs", required=True, help="RootFS directory")
#     parser.add_argument("--arch", required=True, choices=["x86_64", "arm64"])
#     args = parser.parse_args()

    # installer = APKInstaller(Path(args.rootfs), args.arch)
    # installer.install()
