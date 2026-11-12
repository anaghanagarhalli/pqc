#ifndef FIPS202_H
#define FIPS202_H

#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint8_t state[200];
    size_t pos;
} shake128ctx;

typedef struct {
    uint8_t state[200];
    size_t pos;
} shake256ctx;

void shake128_absorb_once(shake128ctx *ctx, const uint8_t *input, size_t inlen);
void shake128_squeezeblocks(uint8_t *output, size_t nblocks, shake128ctx *ctx);
void shake128_init(shake128ctx *ctx);
void shake128_release(shake128ctx *ctx);

void shake256(uint8_t *output, size_t outlen,
              const uint8_t *input, size_t inlen);

void sha3_256(uint8_t *output,
              const uint8_t *input, size_t inlen);

void sha3_512(uint8_t *output,
              const uint8_t *input, size_t inlen);

#define SHAKE128_RATE 168
#define SHAKE256_RATE 136
#define mlk_shake128ctx shake128ctx
#define mlk_shake128_absorb_once shake128_absorb_once
#define mlk_shake128_squeezeblocks shake128_squeezeblocks
#define mlk_shake128_init shake128_init
#define mlk_shake128_release shake128_release
#define mlk_shake256 shake256
#define mlk_sha3_256 sha3_256
#define mlk_sha3_512 sha3_512


#endif
