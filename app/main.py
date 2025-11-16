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
from core.busybox import build_busybox


from tools.host_check import check_host_prerequisites

from manager.pacstrapper import RootFSPackageInstaller

from manager.apktools_builder import build_apk_tools
from manager.opkg_builder import build_opkg


from core.logger import success, info, warning, error



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

dirs = {
    "downloads": downloads_dir,
    "build": build_dir,
    "rootfs": rootfs_dir,
    "bootfs": bootfs_dir,
    "output": output_dir,
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

def configs(args):
    info("Console > Configuring BuildSystem ::::...:.. . :: .--. .")
    info("Loading Configs !!! ... .. .")
    config = load_config(Path("configs") / args.config)
    version = config["version"]
    urls = config.get("urls", {})
    cross_compile = config.get("cross_compile", {})
    extra_cfg = config.get("extra_config", {})
    config_patches = config.get("config_patch", [])
    src_dir_template = config["src_dir"]    
    busybox_src_dir = Path(src_dir_template.format(version=version))
    success(f"Loaded Configs: {version}, {urls}, {extra_cfg}, {config_patches}, {busybox_src_dir} -> from -> {config}")
    return version, urls, cross_compile, extra_cfg, config_patches, busybox_src_dir



def parse():
    parser = argparse.ArgumentParser(description="BusyBox Build System")
    
    parser.add_argument("--config", type=str, default="busybox.json", 
                        help="Pfad zur BusyBox JSON Konfig")
    parser.add_argument("--arch", type=str, 
                        help="Überschreibe die Zielarchitektur (z.B. arm64, x86_64)")
    parser.add_argument("--ignore-errors", action="store_true", 
                        help="Fehler ignorieren und weitermachen")
    parser.add_argument("--ignore-host-tools", action="store_true", 
                        help="Ignoriere fehlende Host-Tools beim Build-Prüfen")
    # parser.add_argument("--configs", type=Path, default=Path("configs"),
    #                     help="Pfad zu configs/")
    # parser.add_argument("--work-dir", type=Path, default=Path("work"),
    #                     help="Temp Build Verzeichnis")
    # parser.add_argument("--downloads-dir", type=Path, default=Path("downloads"),
    #                     help="Download Ordner")
    # parser.add_argument("--rootfs-dir", type=Path, default=Path("rootfs"),
    #                     help="Ziel-RootFS Verzeichnis")
    
    args = parser.parse_args()
    return args







# ---------------------------
# RootFS erstellen
# ---------------------------
def create_rootfs(args):
    # Creates the whole workenviroment and rootfs- folders!""
    info("[*] Starte RootFS-Erstellung...")
    create_directories()
    # Creates all neccessary configurations files in e.g. /etc
    create_etc_files()
    # Creates all neccessary device files in e.g. /dev
    create_dev_nodes()
    # Creates all neccessary configurations files in e.g. /etc/inittab, /etc/init.d/rcS and /init
    create_busybox_init()
    # Creates all neccessary symlinks
    create_symlinks()
    # Copys the Qemu- Emulations files to rootfs
    copy_qemu_user_static(arch=args.arch)
    # Sets the rootfs permissions
    set_rootfs_permissions()
    success("[*] RootFS Struktur erfolgreich erstellt!")
    


def busybox(args, work_dir, downloads_dir, rootfs_dir):
    info("[*] Starte BusyBox-Build...")
    build_busybox(
        args=args,
        work_dir=work_dir,
        downloads_dir=downloads_dir,
        rootfs_dir=rootfs_dir
    )
    # build_busybox(args, version, work_dir, busybox_src_dir, downloads_dir, url, cross_compile, rootfs_dir, extra_cfg, config_patches)
    
    success("[+] Fertig! RootFS und BusyBox sind erstellt.")



    

# ---------------------------
# Main
# ---------------------------
def main():

    args = parse()
    
    info("Checking Host Prerequisites !!! ... .. .")
    check_host_prerequisites(exit_on_fail=not args.ignore_host_tools)

    version, urls, cross_compile, extra_cfg, config_patches, busybox_src_dir = configs(args)
    
    create_rootfs(args)
    
    busybox(args, work_dir, downloads_dir, rootfs_dir)
    
    
    installer = RootFSPackageInstaller(rootfs_dir, arch="x86_64")
    installer.install_packages(["bash", "nano", "apk-tools", "wget", "curl", "gcc", "make", "cmake", "python", "python-pip", "git", "dhcpcd", "dnsmasq", "openssh", "openssl", "coreutils", "libtool", "binutils", "autoconf", "automake", "cryptsetup", "device-mapper", "dmidecode", "findutils", "flex", "bison", "fwupd", "gawk", "gettext", "gmp", "mpc", "mpfr", "hdparm", "help2man", "libgcrypt", "libusb", "lvm2", "m4", "mtools", "libgpg-error", "libsoup", "libffi", "ncurses", "pciutils", "parted", "texinfo", "util-linux", "zlib"])


    build_apk_tools(target_arch=args.arch, target_rootfs_path=rootfs_dir)

    build_opkg(args.arch, rootfs_dir)
    
    

 

    chroot_with_qemu(
        rootfs_dir=rootfs_dir,
        arch=args.arch
    )
    






if __name__ == "__main__":
    main()
