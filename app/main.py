import argparse
import multiprocessing
import os
import json 




from pathlib import Path


from utils.load import load_config
from utils.create import (
    create_directories,
    create_etc_files,
    create_busybox_init,
    create_dev_nodes,
    create_symlinks,
    set_rootfs_permissions,
    copy_qemu_user_static
)


from core.modify_rootfs import chroot_with_qemu

from core.busybox import get_configs, build_busybox


from tools.host_check import check_host_prerequisites

from manager.pacstrapper import RootFSPackageInstaller

from manager.apktools_builder import build_apk_tools
from manager.opkg_builder import build_opkg


from core.logger import success, info, warning, error, start, stop, pause



# ---------------------------
# Projektverzeichnisse
# ---------------------------
app_dir = Path(__file__).parent.resolve()

configs_dir = app_dir / "configs"
package_configs_dir = configs_dir / "packages"
work_dir = app_dir / "work"  # work_dir = Path("work")

downloads_dir = work_dir / "downloads"
build_dir = work_dir / "build"
output_dir = work_dir / "output"
rootfs_dir = build_dir / "rootfs"
bootfs_dir = build_dir / "bootfs"
kernel_dir = build_dir / "kernel"

kernel_output = output_dir / "kernel"
bootfs_output = output_dir / "bootfs"
rootfs_output = output_dir / "rootfs"
firmware_output = output_dir / "firmware"

dirs = {
    "downloads": downloads_dir,
    "build": build_dir,
    "output": output_dir,
    "rootfs": rootfs_dir,
    "bootfs": bootfs_dir,
    "kernel": kernel_dir,
    "kernel_output": kernel_output,
    "bootfs_output": bootfs_output,
    "rootfs_output": rootfs_output,
    "firmware_output": firmware_output
}

TARGET_PACKAGES = [
        "glibc",
        "bash",
        "nano",
        "coreutils",
        "make",
        "python",
        "apk-tool"  

]

# def configs(args):
#     """ Loads the Busybox Configs , and return the variables with the loaded values"""
    
#     info("Console > Configuring BuildSystem ::::...:.. . :: .--. .")
#     info("Loading Configs !!! ... .. .")
#     config = load_config(Path("configs") / args.config)
#     version = config["version"]
#     urls = config.get("urls", {})
#     cross_compile = config.get("cross_compile", {})
#     extra_cfg = config.get("extra_config", {})
#     config_patches = config.get("config_patch", [])
#     src_dir_template = config["src_dir"]    
#     busybox_src_dir = Path(src_dir_template.format(version=version))
#     success(f"Loaded Configs: {version}, {urls}, {extra_cfg}, {config_patches}, {busybox_src_dir} -> from -> {config}")
#     return version, urls, cross_compile, extra_cfg, config_patches, busybox_src_dir



def parse():
    parser = argparse.ArgumentParser(description="BusyBox Build System")
    
    parser.add_argument("--arch", type=str, 
                        help="Overwrite Target-Architecture (e.g. arm64, x86_64)")
    
    parser.add_argument("--jobs", type=int, 
                        help="Cores to be Enabled on Build.", default=8)
    
    parser.add_argument("--rootfs-dir", type=Path, default=Path("rootfs"),
                        help="Target RootFS Folder")
    
    parser.add_argument("--config", type=str, default="busybox.json", 
                        help="Path to Busybox's JSON-Config")
    
    parser.add_argument("--ignore-missing", action="store_true", 
                        help="Ignore missing packages and only install the available.")
    
    parser.add_argument("--ignore-errors", action="store_true", 
                        help="Ignores Errors. (Dosent Exit Building if an error occures.)")
    
    parser.add_argument("--ignore-host-tools", action="store_true", 
                        help="Ignores missing Host-Tools in check.")
    
    # parser.add_argument("--configs", type=Path, default=Path("configs"),
    #                     help="Pfad zu configs/")
    # parser.add_argument("--work-dir", type=Path, default=Path("work"),
    #                     help="Temp Build Verzeichnis")
    # parser.add_argument("--downloads-dir", type=Path, default=Path("downloads"),
    #                     help="Download Ordner")
    # 
    
    args = parser.parse_args()
    return args







# ---------------------------
# RootFS erstellen
# ---------------------------
def create_rootfs(args):
    """ Creates a minimal rootfs layout !!!"""
    info("RootFS Builder Started.")
    
    start("[*] Generating Basic RootFS - Folder Structures. ...")
    create_directories()
    
    start("Generating all neccessary configuration files, deployed in '/etc/' !.")
    create_etc_files()

    start("Building all device-nodes as needed!.")
    create_dev_nodes()

    start("Generating: Initializing System")
    create_busybox_init()

    start("Linking Binarys & Folders !. - (SYMLINKS)")
    create_symlinks()

    start("Copying QEMU- Static Console Emulation File to RootFS !.")
    copy_qemu_user_static(arch=args.arch)

    start("Settings-UP: All File's and Folders expected Permissions & Privileges!... .. .")
    set_rootfs_permissions()
    
    success("[*] RootFS Struktur erfolgreich erstellt!")
    


def busybox(args, work_dir, downloads_dir, rootfs_dir):
    """ Start Building and Installing Busybox !!!"""
    start(f"Building BusyBox & installing ALL BusyBox-Applets into the RootFS: {rootfs_dir}")    
    build_busybox(
        args=args,
        work_dir=work_dir,
        downloads_dir=downloads_dir,
        rootfs_dir=rootfs_dir
    )
    success("[+] Fertig! RootFS und BusyBox sind erstellt.")



def packages_installer(args, packages_config):
    """ [ArchLinux] - Install Pacman's Packages INTO RootFS !!! """
    arch = args.arch if args.arch else "x86_64"
    env = os.environ.copy()

    if arch in ("x86_64", "amd64"):
        arch_str = "x86_64"
    elif arch in ("arm64", "aarch64"):
        arch_str = "aarch64"
    else:
        raise RuntimeError(f"Unsupported architecture: {arch}")

    path = Path(configs_dir / packages_config)
    start(f"Loading Packages-List from: {path}")
    
    data = json.loads(path.read_text())
    packages = data.get("packages", [])
    
    info(f"Packages To be Installed:  {len(packages)}")
    for pkg in packages:
        info(f"Added:  {pkg}")
    
    
    start("Downloading & Installing the Packages Now!... .. .")
    installer = RootFSPackageInstaller(rootfs_dir, arch=arch_str, ignore_missing=args.ignore_missing)
    installer.install_packages(packages)
    # installer.install_packages(["bash", "nano", "apk-tools", "wget", "curl", "gcc", "make", "cmake", "python", "python-pip", "git", "dhcpcd", "dnsmasq", "openssh", "openssl", "coreutils", "libtool", "binutils", "autoconf", "automake", "cryptsetup", "device-mapper", "dmidecode", "findutils", "flex", "bison", "fwupd", "gawk", "gettext", "gmp", "mpc", "mpfr", "hdparm", "help2man", "libgcrypt", "libusb", "lvm2", "m4", "mtools", "libgpg-error", "libsoup", "libffi", "ncurses", "pciutils", "parted", "texinfo", "util-linux", "zlib"])
    success("All Packages should be installed now on your system!")


# ---------------------------
# Main
# ---------------------------
def main():
    """ NexuzCore - Firmware Buildsystem's Main Function """

    args = parse()
    
    start("Checking Host Prerequisites!.")
    check_host_prerequisites(exit_on_fail=not args.ignore_host_tools)
    
    
    create_rootfs(args)
    
    busybox(args, work_dir, downloads_dir, rootfs_dir)
    
    packages_installer(args, packages_config="packages.json")
    
 
    build_apk_tools(arch=args.arch, rootfs_dir=rootfs_dir)

    build_opkg(args.arch, rootfs_dir)
    
    

 

    chroot_with_qemu(
        rootfs_dir=rootfs_dir,
        arch=args.arch
    )
    






if __name__ == "__main__":
    main()
