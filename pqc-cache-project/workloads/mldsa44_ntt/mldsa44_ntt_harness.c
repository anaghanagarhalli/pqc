#include <stdint.h>

extern void mldsa44_workload(void);

/* Spike HTIF */
volatile uint64_t tohost = 0;
volatile uint64_t fromhost = 0;

int main(void)
{
    mldsa44_workload();

    /* Tell Spike the bare-metal workload is complete */
    tohost = 1;

    while (1) {
    }

    return 0;
}
