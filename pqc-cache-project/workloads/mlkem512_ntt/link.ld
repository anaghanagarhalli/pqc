ENTRY(_start)

MEMORY
{
    RAM (rwx) : ORIGIN = 0x80000000, LENGTH = 16M
}

SECTIONS
{
    .text : ALIGN(16)
    {
        *(.text.start)
        *(.text*)
    } > RAM

    .rodata : ALIGN(16)
    {
        *(.rodata*)
    } > RAM

    .data : ALIGN(16)
    {
        *(.data*)
    } > RAM

    .bss : ALIGN(16)
    {
        *(.bss*)
        *(COMMON)
    } > RAM

    . = ALIGN(16);
    . = . + 0x10000;
    _stack_top = .;
}
