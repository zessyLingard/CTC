#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/evp.h>

static EVP_CIPHER_CTX *aes_ctx = NULL;
static unsigned char aes_key[32];
static unsigned char aes_iv[16];

/* ===== READ RAW AES KEY ===== */
int read_aes_key()
{
    FILE *fp = fopen("aes_key.txt", "rb");
    if (!fp) return -1;

    size_t n = fread(aes_key, 1, 32, fp);
    fclose(fp);

    if (n != 32) return -1;

    return 0;
}

/* ===== AES INIT ===== */
int aes_init()
{
    if (read_aes_key() != 0)
        return -1;

    /* IMPORTANT:
       IV must match decoder.
       If you don't store IV separately,
       use fixed zero IV on BOTH sides.
    */
    memset(aes_iv, 0, 16);

    aes_ctx = EVP_CIPHER_CTX_new();
    if (!aes_ctx) return -1;

    if (!EVP_EncryptInit_ex(aes_ctx,
                            EVP_aes_256_ctr(),
                            NULL,
                            aes_key,
                            aes_iv))
        return -1;

    return 0;
}

int main(int argc, char *argv[])
{
    if (argc != 4) {
        fprintf(stderr,
        "Usage: %s input_file short_delay long_delay\n",
        argv[0]);
        return 1;
    }

    char *input_file = argv[1];
    double short_delay = atof(argv[2]);
    double long_delay  = atof(argv[3]);

    if (short_delay <= 0 || long_delay <= 0) {
        fprintf(stderr, "Invalid delay values\n");
        return 1;
    }

    FILE *fp = fopen(input_file, "rb");
    if (!fp) {
        perror("fopen");
        return 1;
    }

    if (aes_init() != 0) {
        fprintf(stderr, "AES init failed (aes_key.txt?)\n");
        return 1;
    }

    unsigned char inbuf[4096];
    unsigned char outbuf[4096];
    int inlen, outlen;

    while ((inlen = fread(inbuf, 1, sizeof(inbuf), fp)) > 0) {

        if (!EVP_EncryptUpdate(aes_ctx, outbuf, &outlen,
                               inbuf, inlen)) {
            fprintf(stderr, "AES encryption error\n");
            return 1;
        }

        for (int i = 0; i < outlen; i++) {
            unsigned char byte = outbuf[i];

            for (int bit = 0; bit < 8; bit++) {
                double delay =
                    (byte & (1 << bit)) ? short_delay : long_delay;

                printf("%.6f", delay);
                printf(",");
            }
        }
    }

    /* 🔥 CRITICAL FIX: flush final AES block */
    if (!EVP_EncryptFinal_ex(aes_ctx, outbuf, &outlen)) {
        fprintf(stderr, "AES finalization error\n");
        return 1;
    }

    for (int i = 0; i < outlen; i++) {
        unsigned char byte = outbuf[i];

        for (int bit = 0; bit < 8; bit++) {
            double delay =
                (byte & (1 << bit)) ? short_delay : long_delay;

            printf("%.6f", delay);
            printf(",");
        }
    }

    fclose(fp);

    if (aes_ctx)
        EVP_CIPHER_CTX_free(aes_ctx);

    return 0;
}
