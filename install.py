#!/usr/bin/env python
"""
Simple installer for hypr-dots dotfiles and scripts.

Place a file named `deps.txt` alongside this script, listing package names (one per line).
Comments (`# ...`) and blank lines are ignored. If no `deps.txt` is found, defaults will be used.
"""
import os
import subprocess
import shutil
import getpass
import pwd
import sys

def install_dependencies(deps):
    missing = []
    for dep in deps:
        try:
            subprocess.run(
                ['pacman', '-Qi', dep],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
        except subprocess.CalledProcessError:
            missing.append(dep)
    if not missing:
        print("All dependencies are already installed.")
        return
    if shutil.which('yay'):
        cmd = ['yay', '-S', '--needed', '--noconfirm'] + missing
    else:
        if os.geteuid() != 0:
            print("Missing dependencies: " + ", ".join(missing))
            print("Please install them manually or rerun this script as root.")
            sys.exit(1)
        cmd = ['pacman', '-S', '--needed', '--noconfirm'] + missing
    print("Installing dependencies: " + ", ".join(missing))
    subprocess.check_call(cmd)

def copy_dotfiles(src_dir, dest_dir, user_uid, user_gid):
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)
    shutil.copytree(src_dir, dest_dir)
    try:
        os.chown(dest_dir, user_uid, user_gid)
    except PermissionError:
        pass
    for root, dirs, files in os.walk(dest_dir):
        for name in dirs + files:
            path = os.path.join(root, name)
            try:
                os.chown(path, user_uid, user_gid)
            except PermissionError:
                pass

def install_scripts(scripts_dir, bin_dir, user_uid, user_gid):
    os.makedirs(bin_dir, exist_ok=True)
    for root, _, files in os.walk(scripts_dir):
        for file in files:
            src_file = os.path.join(root, file)
            dest_file = os.path.join(bin_dir, file)
            shutil.copy2(src_file, dest_file)
            os.chmod(dest_file, 0o755)
            try:
                os.chown(dest_file, user_uid, user_gid)
            except PermissionError:
                pass

def main():
    # Determine real user
    sudo_user = os.getenv('SUDO_USER')
    if sudo_user:
        real_user = sudo_user
    else:
        real_user = getpass.getuser()
    pw = pwd.getpwnam(real_user)
    user_home = pw.pw_dir
    user_uid = pw.pw_uid
    user_gid = pw.pw_gid

    script_dir = os.path.dirname(os.path.realpath(__file__))

    # Load dependencies from deps.txt or fallback to defaults
    deps_file = os.path.join(script_dir, 'deps.txt')
    if os.path.isfile(deps_file):
        with open(deps_file) as f:
            deps = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    else:
        deps = [
            'hyprland',
            'waybar',
            'libnotify',
            'dunst',
            'wlogout',
            'swaylock',
            'nerd-fonts-complete',
            'ttf-jetbrains-mono',
            'kitty',
        ]

    install_dependencies(deps)

    # Install dotfiles
    dotfiles_src = os.path.join(script_dir, 'dotfiles')
    dotfiles_dest = os.path.join(user_home, '.config')
    print(f"Installing dotfiles to {dotfiles_dest}...")
    copy_dotfiles(dotfiles_src, dotfiles_dest, user_uid, user_gid)

    # Install scripts
    scripts_src = os.path.join(script_dir, 'scripts')
    bin_dest = os.path.join(user_home, '.local', 'share', 'bin')
    print(f"Installing scripts to {bin_dest}...")
    install_scripts(scripts_src, bin_dest, user_uid, user_gid)

    print("Done.")

if __name__ == "__main__":
    main()
