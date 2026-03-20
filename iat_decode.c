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

    /* MUST MATCH ENCODER */
    memset(aes_iv, 0, 16);

    aes_ctx = EVP_CIPHER_CTX_new();
    if (!aes_ctx) return -1;

    if (!EVP_DecryptInit_ex(aes_ctx,
                            EVP_aes_256_ctr(),
                            NULL,
                            aes_key,
                            aes_iv))
        return -1;

    return 0;
}

/* ===== MAIN ===== */
int main(int argc, char *argv[])
{
    if (argc != 3) {
        fprintf(stderr,
        "Usage: %s timing.txt threshold\n",
        argv[0]);
        return 1;
    }

    char *input_file = argv[1];
    double threshold = atof(argv[2]);

    if (threshold <= 0) {
        fprintf(stderr, "Invalid threshold\n");
        return 1;
    }

    if (aes_init() != 0) {
        fprintf(stderr, "AES init failed (aes_key.txt?)\n");
        return 1;
    }

    FILE *fp = fopen(input_file, "r");
    if (!fp) {
        perror("fopen");
        return 1;
    }

    unsigned char current_byte = 0;
    int bit_count = 0;
    double value;

    unsigned char decrypt_out[1];
    int outlen;

    while (fscanf(fp, " %lf%*[, \n]", &value) == 1) {

        int bit = (value < threshold) ? 1 : 0;

        /* LSB-first packing */
        current_byte |= (bit << bit_count);
        bit_count++;

        if (bit_count == 8) {

            /* Decrypt 1 byte in CTR stream */
            if (!EVP_DecryptUpdate(aes_ctx,
                                   decrypt_out,
                                   &outlen,
                                   &current_byte,
                                   1)) {
                fprintf(stderr, "AES decrypt error\n");
                return 1;
            }

            fwrite(decrypt_out, 1, 1, stdout);

            current_byte = 0;
            bit_count = 0;
        }
    }

    fclose(fp);

    if (aes_ctx)
        EVP_CIPHER_CTX_free(aes_ctx);

    return 0;
}
