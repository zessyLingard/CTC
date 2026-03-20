DEFAULTPORT=9999
CC=gcc
HEADERS=main.h

#DEBUGFLAGS=-g -ggdb
CFLAGS=-Wall -W -Wextra -Wshadow -c $(DEBUGFLAGS)

OBJECTS=client.o support.o server.o iat_encode.o seq_encode.o

BUILDFLAGS=-O -lrt
SERVERBUILDFLAGS=-lm

AESFLAGS=-DUSE_AES -lcrypto

.SUFFIXES : .c .o

%.o : %.c $(HEADERS)
	$(CC) $(CFLAGS) $<

# ======================
# Default build target
# ======================
all : client server iat_encode seq_encode bch-aes

# ======================
# Core binaries
# ======================
client : client.o support.o
	$(CC) $(BUILDFLAGS) -o $@ $^

server : server.o support.o
	$(CC) $(BUILDFLAGS) $(SERVERBUILDFLAGS) -o $@ $^

iat_encode : iat_encode.o
	$(CC) $(BUILDFLAGS) -o $@ $^

seq_encode : seq_encode.o
	$(CC) $(BUILDFLAGS) -o $@ $^

# ======================
# BCH + AES ONLY
# ======================
bch-aes : bch_encode bch_decode

bch_encode : bch_encode.c
	$(CC) -Wall -O $(AESFLAGS) -o $@ $< -lm -lcrypto

bch_decode : bch_decode.c
	$(CC) -Wall -O $(AESFLAGS) -o $@ $< -lm -lcrypto

# ======================
# Utility targets
# ======================
clean :
	rm -vf client server iat_encode seq_encode \
	       bch_encode bch_decode \
	       a.out *~ *.core core $(OBJECTS)

runcli :
	./client -P $(DEFAULTPORT) -D 127.0.0.1 -d Asciii -i 123 -o 1,2,3/4,5,6/7,8,9/ -v

runser :
	./server -P $(DEFAULTPORT) -v

runserloop :
	while [ 1 ]; do ./server -q -P $(DEFAULTPORT) -v; sleep 1; done

count :
	wc -l *.c

docs :
	(cd documentation; make all)

e :
	gedit *.c || pluma *.c

