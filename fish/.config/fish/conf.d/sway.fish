if test (tty) = "/dev/tty1"
    set -x CLUTTER_BACKEND wayland
    set -x ECORE_EVAS_ENGINE wayland_egl
    set -x ELM_ENGINE wayland_wgl
    set -x GDK_BACKEND wayland
    set -x _JAVA_AWT_WM_NONREPARENTING 1
    set -x MOZ_ENABLE_WAYLAND 1
    set -x PASSWORD_STORE_ENABLE_EXTENSIONS true
    set -x QT_AUTO_SCREEN_SCALE_FACTOR 1
    set -x QT_QPA_PLATFORM wayland
    set -x QT_WAYLAND_DISABLE_WINDOWDECORATION 1
    set -x SDL_VIDEODRIVER wayland
    set -x XDG_CURRENT_DESKTOP sway
    set -x ELECTRON_OZONE_PLATFORM_HINT wayland

    exec sway
end
