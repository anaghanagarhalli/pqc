#include <stdint.h>

#include "../../liboqs/src/kem/ml_kem/mlkem-native_ml-kem-512_ref/mlkem/src/poly.h"

volatile int16_t mlkem_checksum;

/* Spike HTIF */
volatile uint64_t tohost = 0;
volatile uint64_t fromhost = 0;

void mlkem512_workload(void)
{
    mlk_poly p;

    for (int i = 0; i < MLKEM_N; i++) {
        p.coeffs[i] = (int16_t)(i % 3329);
    }

    mlk_poly_ntt(&p);
    mlk_poly_invntt_tomont(&p);

    mlkem_checksum = p.coeffs[0];
}

int main(void)
{
    mlkem512_workload();

    /* Tell Spike the bare-metal workload is complete */
    tohost = 1;

    while (1) {
    }

    return 0;
}
