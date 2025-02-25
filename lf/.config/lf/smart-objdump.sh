binary=$1
extended=$2

arch=`readelf -h $1 | grep 'Machine' | awk '{print $2}'`

objdump_args="-D --disassembler-color=extended --wide --demangle=auto"
bat_args=" --paging=always"

# XXX(pkoscik): nasty way to check for a flag
if [[ "$extended" == "--extended" ]]; then
    objdump_args="$objdump_args --visualize-jumps=extended-color -S"
fi

case "$arch" in
  "ARM")
    arm-none-eabi-objdump $objdump_args "$1" | bat $bat_args
    exit
    ;;
  "AArch64")
    aarch64-linux-gnu-objdump $objdump_args "$1" | bat $bat_args
    exit
    ;;
  "RISC-V")
    riscv64-linux-gnu-objdump $objdump_args "$1" | bat $bat_args
    exit
    ;;
  "Advanced") # XXX(pkoscik): hack for "Advanced Micro Devices X86-64"
    objdump $objdump_args "$1" | bat $bat_args
    exit
    ;;
  *)
    echo "Unsupported architecture: '$arch'!" | bat $bat_args
    exit 1
    ;;
esac
