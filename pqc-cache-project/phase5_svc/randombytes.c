#include <stddef.h>
#include <stdint.h>

static uint32_t rng_state = 0x13579BDFu;

int randombytes(uint8_t *out, size_t outlen)
{
    for (size_t i = 0; i < outlen; i++) {
        rng_state = rng_state * 1664525u + 1013904223u;
        out[i] = (uint8_t)(rng_state >> 24);
    }

    return 0;
}
