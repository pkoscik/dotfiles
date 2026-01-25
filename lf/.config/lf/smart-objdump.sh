binary=$1
extended=$2

arch=`readelf -h $1 | grep 'Machine' | awk '{print $2}'`

objdump_args="-D --wide --demangle=auto"

# XXX(pkoscik): nasty way to check for a flag
if [[ "$extended" == "--extended" ]]; then
    objdump_args="$objdump_args --visualize-jumps=extended -S"
fi

case "$arch" in
  "ARM")
    arm-none-eabi-objdump $objdump_args "$1" > "$binary.map"
    exit
    ;;
  "AArch64")
    aarch64-linux-gnu-objdump $objdump_args "$1" > "$binary.map"
    exit
    ;;
  "RISC-V")
    riscv64-linux-gnu-objdump $objdump_args "$1" > "$binary.map"
    exit
    ;;
  "Advanced") # XXX(pkoscik): hack for "Advanced Micro Devices X86-64"
    objdump $objdump_args "$1" > "$binary.map"
    exit
    ;;
  *)
    echo "Unsupported architecture: '$arch'!" > "$binary.map"
    exit 1
    ;;
esac
