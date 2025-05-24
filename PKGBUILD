pkgname=hypr-dots
pkgver=1.0
pkgrel=1
arch=('any')
depends=(
    'hyprland'
    # 'swww'
    'waybar'
    'libnotify'
    'dunst'
    # 'just'
    # 'wireplumber'
    # 'pipewire'
    'wlogout'
    'swaylock'
    )
source=()
license=('Apache-2.0')

package() {
    # Get actual username and home dir of non-root user
    local real_user=$(logname)
    local user_home=$(eval echo "~$real_user")

    echo "Installing dotfiles to $user_home/.config/..."
    mkdir -p "$user_home/.config"
    cp -rT "$srcdir/dotfiles" "$user_home/.config"

    echo "Installing scripts to $user_home/.local/share/bin/..."
    mkdir -p "$user_home/.local/share/bin"
    find "$srcdir/scripts" -type f -exec install -Dm755 "{}" "$user_home/.local/share/bin/$(basename "{}")" \;

    chown -R "$real_user:$real_user" "$user_home/.config" "$user_home/.local/share/bin"
}
