import json
import subprocess
import shutil


from pathlib import Path


from utils.execute import run_command_live

from core.logger import success, info, warning, error, start, stop, pause, install




# =============================================================================
# KERNEL BUILDER
# =============================================================================

def load_kernel_config(configs_dir: Path, arch: str):
    config_file = configs_dir / "kernel.json"

    if not config_file.exists():
        error(f"kernel.json nicht gefunden: {config_file}")
        raise SystemExit(1)

    with open(config_file, "r") as f:
        data = json.load(f)

    if arch not in data:
        error(f"Arch '{arch}' nicht in kernel.json definiert!")
        raise SystemExit(1)

    return data[arch]


def clone_or_update_repo(repo_url: str, dest: Path):
    if dest.exists():
        info(f"[kernel] Repository existiert bereits. Pull...")
        run_command_live(["git", "-C", str(dest), "pull"])
    else:
        info(f"[kernel] Klone Kernel-Repository {repo_url} ...")
        run_command_live(["git", "clone", "--depth=1", repo_url, str(dest)])


def apply_defconfig(kernel_src: Path, defconfig: str, arch: str):
    info(f"[kernel] Verwende Defconfig: {defconfig}")

    env = dict(**{**dict()}, ARCH=arch)

    if arch == "arm64":
        env["CROSS_COMPILE"] = "aarch64-linux-gnu-"

    run_command_live(
        ["make", defconfig],
        cwd=str(kernel_src),
        env=env
    )


def build_kernel_commands(kernel_src: Path, arch: str, jobs: int):
    info(f"[kernel] Kompiliere Kernel für {arch} ...")

    env = {"ARCH": arch}

    if arch == "arm64":
        env["CROSS_COMPILE"] = "aarch64-linux-gnu-"

    # Kernel
    run_command_live(
        ["make", f"-j{jobs}"],
        cwd=str(kernel_src),
        env=env
    )

    # Module
    run_command_live(
        ["make", "modules", f"-j{jobs}"],
        cwd=str(kernel_src),
        env=env
    )

    # Device Trees für ARM
    if arch == "arm64":
        run_command_live(
            ["make", "dtbs", f"-j{jobs}"],
            cwd=str(kernel_src),
            env=env
        )


def install_kernel(kernel_src: Path, output_dir: Path, arch: str):
    boot_dir = output_dir / "boot"
    modules_dir = output_dir / "lib/modules"

    boot_dir.mkdir(parents=True, exist_ok=True)
    modules_dir.mkdir(parents=True, exist_ok=True)

    if arch == "x86_64":
        kernel_image = kernel_src / "arch/x86/boot/bzImage"
    else:
        kernel_image = kernel_src / "arch/arm64/boot/Image"

    if not kernel_image.exists():
        error("Kernel Image wurde nicht erstellt!")
        raise SystemExit(1)

    shutil.copy(kernel_image, boot_dir / "kernel.img")

    # Module installieren
    run_command_live([
        "make",
        f"INSTALL_MOD_PATH={output_dir}",
        "modules_install"
    ], cwd=str(kernel_src))

    # Device Trees für ARM64
    if arch == "arm64":
        dtb_dir = kernel_src / "arch/arm64/boot/dts"
        out = boot_dir / "dtbs"
        shutil.copytree(dtb_dir, out, dirs_exist_ok=True)

    success("[kernel] Kernel erfolgreich installiert.")


# =============================================================================
# MAIN ENTRY FUNCTION
# =============================================================================

def build_kernel(args, work_dir: Path, downloads_dir: Path, output_dir: Path):
    arch = args.arch
    jobs = getattr(args, "jobs", 8)

    configs_dir = Path(args.configs_dir)

    # 1) Kernel-Konfiguration aus kernel.json laden
    kernel_cfg = load_kernel_config(configs_dir, arch)
    repo_url = kernel_cfg["repo_url"]
    defconfig = kernel_cfg["defconfig"]

    kernel_src = downloads_dir / f"kernel-{arch}"

    # 2) Repository klonen oder aktualisieren
    clone_or_update_repo(repo_url, kernel_src)

    # 3) Defconfig anwenden
    apply_defconfig(kernel_src, defconfig, arch)

    # 4) Kernel kompilieren
    build_kernel_commands(kernel_src, arch, jobs)

    # 5) Kernel & Module ins Output-Verzeichnis installieren
    install_kernel(kernel_src, output_dir, arch)

    success(f"[kernel] Build für {arch} abgeschlossen.")
