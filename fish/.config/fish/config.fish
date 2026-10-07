# after conf.d/, so sway inherits wayland-env.fish etc.
if type -q sway && test (tty) = "/dev/tty1"
    exec sway
end
