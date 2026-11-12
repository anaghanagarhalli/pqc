#include "fips202.h"

#include <string.h>

#include "/home/cnc_susindharan/pqc-cache-project/liboqs/src/common/sha3/xkcp_low/KeccakP-1600/plain-64bits/KeccakP-1600-SnP.h"

static void sponge_init(uint8_t *state)
{
    KeccakP1600_Initialize(state);
}

static void absorb(uint8_t *state,
                   const uint8_t *input,
                   size_t inlen,
                   uint8_t domain,
                   size_t rate)
{
    size_t offset = 0;

    while (inlen - offset >= rate) {
        KeccakP1600_AddBytes(state, input + offset, 0, (unsigned int)rate);
        KeccakP1600_Permute_24rounds(state);
        offset += rate;
    }

    uint8_t block[168];
    memset(block, 0, rate);

    size_t remaining = inlen - offset;
    memcpy(block, input + offset, remaining);

    block[remaining] ^= domain;
    block[rate - 1] ^= 0x80;

    KeccakP1600_AddBytes(state, block, 0, (unsigned int)rate);
    KeccakP1600_Permute_24rounds(state);
}

static void squeeze(uint8_t *output,
                    size_t outlen,
                    uint8_t *state,
                    size_t rate)
{
    size_t offset = 0;

    while (outlen - offset >= rate) {
        KeccakP1600_ExtractBytes(state, output + offset, 0,
                                 (unsigned int)rate);
        KeccakP1600_Permute_24rounds(state);
        offset += rate;
    }

    if (outlen > offset) {
        KeccakP1600_ExtractBytes(state, output + offset, 0,
                                 (unsigned int)(outlen - offset));
    }
}

void shake128_absorb_once(shake128ctx *ctx,
                          const uint8_t *input,
                          size_t inlen)
{
    sponge_init(ctx->state);
    absorb(ctx->state, input, inlen, 0x1F, 168);
    ctx->pos = 0;
}

void shake128_squeezeblocks(uint8_t *output,
                            size_t nblocks,
                            shake128ctx *ctx)
{
    for (size_t i = 0; i < nblocks; i++) {
        KeccakP1600_ExtractBytes(ctx->state, output + i * 168, 0, 168);
        KeccakP1600_Permute_24rounds(ctx->state);
    }
}

void shake128_init(shake128ctx *ctx)
{
    memset(ctx, 0, sizeof(*ctx));
}

void shake128_release(shake128ctx *ctx)
{
    memset(ctx, 0, sizeof(*ctx));
}

void shake256(uint8_t *output,
              size_t outlen,
              const uint8_t *input,
              size_t inlen)
{
    uint8_t state[200];

    sponge_init(state);
    absorb(state, input, inlen, 0x1F, 136);
    squeeze(output, outlen, state, 136);

    memset(state, 0, sizeof(state));
}

void sha3_256(uint8_t *output,
              const uint8_t *input,
              size_t inlen)
{
    uint8_t state[200];

    sponge_init(state);
    absorb(state, input, inlen, 0x06, 136);
    squeeze(output, 32, state, 136);

    memset(state, 0, sizeof(state));
}

void sha3_512(uint8_t *output,
              const uint8_t *input,
              size_t inlen)
{
    uint8_t state[200];

    sponge_init(state);
    absorb(state, input, inlen, 0x06, 72);
    squeeze(output, 64, state, 72);

    memset(state, 0, sizeof(state));
}
