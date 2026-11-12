#include <stdint.h>
#include <stddef.h>

#include "kem.h"
#include "params.h"

volatile uint64_t tohost = 0;
volatile uint64_t fromhost = 0;
volatile uint8_t checksum = 0;

static uint8_t pk[MLKEM_INDCCA_PUBLICKEYBYTES];
static uint8_t sk[MLKEM_INDCCA_SECRETKEYBYTES];
static uint8_t ct[MLKEM_INDCCA_CIPHERTEXTBYTES];
static uint8_t ss_enc[MLKEM_SSBYTES];
static uint8_t ss_dec[MLKEM_SSBYTES];

#ifndef PHASE5_RUN_ID
#define PHASE5_RUN_ID 0
#endif

static uint32_t rng_state =
    0x13579BDFu + (uint32_t)PHASE5_RUN_ID * 0x9E3779B9u;

__attribute__((optimize("O0"))) void *memset(void *dst, int value, size_t n)
{
    uint8_t *p = (uint8_t *)dst;
    while (n--)
        *p++ = (uint8_t)value;
    return dst;
}

__attribute__((optimize("O0"))) void *memcpy(void *dst, const void *src, size_t n)
{
    uint8_t *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    while (n--)
        *d++ = *s++;
    return dst;
}

static uint8_t next_random_byte(void)
{
    rng_state = rng_state * 1664525u + 1013904223u;
    return (uint8_t)(rng_state >> 24);
}

static void fill_fixed(uint8_t *p, size_t n, uint8_t base)
{
    for (size_t i = 0; i < n; i++)
        p[i] = (uint8_t)(base + (uint8_t)i);
}

static void fill_random(uint8_t *p, size_t n)
{
    for (size_t i = 0; i < n; i++)
        p[i] = next_random_byte();
}

static int run_mlkem(void)
{
    uint8_t key_coins[2 * MLKEM_SYMBYTES];
    uint8_t enc_coins[MLKEM_SYMBYTES];

#ifdef PHASE5_RANDOM_MODE
    fill_random(key_coins, sizeof(key_coins));
    fill_random(enc_coins, sizeof(enc_coins));
#else
    uint8_t key_base = (uint8_t)(0x10u + (uint32_t)PHASE5_RUN_ID * 0x17u);
    uint8_t enc_base = (uint8_t)(0x80u + (uint32_t)PHASE5_RUN_ID * 0x29u);
    fill_fixed(key_coins, sizeof(key_coins), key_base);
    fill_fixed(enc_coins, sizeof(enc_coins), enc_base);
#endif

    if (mlk_kem_keypair_derand(pk, sk, key_coins, 0) != 0)
        return -1;

    if (mlk_kem_enc_derand(ct, ss_enc, pk, enc_coins, 0) != 0)
        return -2;

    if (mlk_kem_dec(ss_dec, ct, sk, 0) != 0)
        return -3;

    checksum = 0;
    for (size_t i = 0; i < sizeof(ss_dec); i++)
        checksum ^= ss_dec[i];

    return 0;
}

int main(void)
{
    int ret = run_mlkem();
    tohost = (ret == 0) ? 1 : 0;

    while (1) {
    }

    return 0;
}
