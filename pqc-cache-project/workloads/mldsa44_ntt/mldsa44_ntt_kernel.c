#include <stdint.h>
#include "params.h"

#define MLDSA_Q 8380417
#define MLDSA_N 256
#define MLD_FQMUL_BOUND ((5 * MLDSA_Q + 3) / 4)
#define MLD_INTT_BOUND MLDSA_Q

#include "../../liboqs/src/sig/ml_dsa/mldsa-native_ml-dsa-44_ref/mldsa/src/zetas.inc"

static int32_t mld_montgomery_reduce(int64_t a)
{
    const int64_t QINV = 58728449;
    int64_t t = (int32_t)a * QINV;
    t = (a - t * MLDSA_Q) >> 32;
    return (int32_t)t;
}

static int32_t mld_fqmul(int32_t a, int32_t b)
{
    return mld_montgomery_reduce((int64_t)a * (int64_t)b);
}

static void mld_ntt_butterfly_block(
    int32_t r[MLDSA_N],
    int32_t zeta,
    unsigned start,
    unsigned len)
{
    for (unsigned j = start; j < start + len; j++) {
        int32_t t = mld_fqmul(r[j + len], zeta);
        r[j + len] = r[j] - t;
        r[j] = r[j] + t;
    }
}

static void mld_ntt_layer(
    int32_t r[MLDSA_N],
    unsigned layer)
{
    unsigned k = 1u << (layer - 1);
    unsigned len = MLDSA_N >> layer;

    for (unsigned start = 0; start < MLDSA_N; start += 2 * len) {
        int32_t zeta = mld_zetas[k++];
        mld_ntt_butterfly_block(r, zeta, start, len);
    }
}

static void mld_poly_ntt_c(int32_t r[MLDSA_N])
{
    for (unsigned layer = 1; layer < 9; layer++) {
        mld_ntt_layer(r, layer);
    }
}

static void mld_invntt_layer(
    int32_t r[MLDSA_N],
    unsigned layer)
{
    unsigned len = MLDSA_N >> layer;
    unsigned k = (1u << layer) - 1;

    for (unsigned start = 0; start < MLDSA_N; start += 2 * len) {
        int32_t zeta = -mld_zetas[k--];

        for (unsigned j = start; j < start + len; j++) {
            int32_t t = r[j];
            r[j] = t + r[j + len];
            r[j + len] = t - r[j + len];
            r[j + len] = mld_fqmul(r[j + len], zeta);
        }
    }
}

static int32_t mld_fqscale(int32_t a)
{
    const int32_t f = 41978;
    return mld_montgomery_reduce((int64_t)a * f);
}

static void mld_poly_invntt_tomont_c(int32_t r[MLDSA_N])
{
    for (unsigned layer = 8; layer >= 1; layer--) {
        mld_invntt_layer(r, layer);
    }

    for (unsigned j = 0; j < MLDSA_N; ++j) {
        r[j] = mld_fqscale(r[j]);
    }
}

volatile int32_t mldsa_checksum;

void mldsa44_workload(void)
{
    int32_t p[MLDSA_N];

    for (unsigned i = 0; i < MLDSA_N; i++) {
        p[i] = (int32_t)(i % MLDSA_Q);
    }

    mld_poly_ntt_c(p);
    mld_poly_invntt_tomont_c(p);

    mldsa_checksum = p[0];
}
