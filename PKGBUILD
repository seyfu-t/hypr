pkgname=hypr-dots
pkgver=1.0
pkgrel=1
arch=('any')
depends=(
    'hyprland'
    'fish'
    'swww'
    'waybar'
    'libnotify'
    'dunst'
    'just'
    'wireplumber'
    'pipewire'
    
    
    
    
    
    )
source=()
license=('MIT')

package() {
    mkdir -p "$pkgdir/usr/share/$pkgname"
    cp -r "$srcdir/dotfiles/" "$pkgdir/usr/share/$pkgname/"
    install -Dm755 "$srcdir/scripts/setup.sh" "$pkgdir/usr/bin/mysetup"
}
