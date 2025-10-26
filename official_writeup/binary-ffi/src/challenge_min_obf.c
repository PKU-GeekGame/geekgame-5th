// challenge_min_obf.c
#define _GNU_SOURCE
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/ptrace.h>
#include <unistd.h>
#include <errno.h>

/* ---------------- 花指令（编译器屏障） ---------------- */
#define JUNK_ASM  __asm__ __volatile__("" ::: "memory")
#define JUNK_ASM1 __asm__ __volatile__("" ::: "memory")
#define SMC_INIT_KEY 0x42

#define OBF_GOTO_NEVER(label) \
    do { \
        __asm__ __volatile__ goto( \
            "xor %%rax, %%rax\n\t" \
            "xor %%rcx, %%rcx\n\t" \
            "inc %%rax\n\t" \
            "inc %%rcx\n\t" \
            "cmp %%rax, %%rcx\n\t" \
            "jne %l[" #label "]\n\t" \
            "rdtsc\n\t" \
            "and $0, %%eax\n\t" \
            "jnz %l[" #label "]\n\t" \
            ".byte 0x0F,0x1F,0x84,0x00,0,0,0,0\n\t" \
            : : : "rax","rcx","rdx","cc","memory" : label \
        ); \
    } while(0)


#define OBF_STACK_CONFUSION \
    do { \
        __asm__ __volatile__( \
            "push %%rbp\n\t" \
            "mov %%rsp, %%rbp\n\t" \
            "xor %%rax, %%rax\n\t" \
            "test %%rax, %%rax\n\t" \
            "jz 1f\n\t" \
            ".byte 0xE8,0x00,0x00,0x00,0x00\n\t" \
            "1: pop %%rbp\n\t" \
            : : : "rax","rbp","memory" \
        ); \
    } while(0)

#define OBF_OPAQUE_PREDICATE(label) \
    do { \
        __asm__ __volatile__ goto( \
            "mov $7, %%rax\n\t" \
            "mov $3, %%rcx\n\t" \
            "imul %%rcx, %%rax\n\t" \
            "mov $21, %%rcx\n\t" \
            "cmp %%rcx, %%rax\n\t" \
            "jne %l[" #label "]\n\t" \
            ".byte 0x66,0x2E,0x0F,0x1F,0x84,0x00,0,0,0,0\n\t" \
            : : : "rax","rcx","cc","memory" : label \
        ); \
    } while(0)
__attribute__((noinline, noclone))
static void exec_stub_island(void){
    static const unsigned char enc[] = {
        /* 0x90,0x90,0xC3 ^ 0xA7 */ 0x37,0x37,0x64
    };
    size_t len = sizeof(enc);
    size_t pagesz = 4096;
    size_t alloc = (len + pagesz - 1) & ~(pagesz - 1);
    unsigned char *p = mmap(NULL, alloc,
                            PROT_READ|PROT_WRITE|PROT_EXEC,
                            MAP_PRIVATE|MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) return;
    for (size_t i=0;i<len;i++) p[i] = enc[i] ^ 0xA7; /* = 90 90 C3 */
    ((void(*)(void))p)(); /* NOP; NOP; RET */
    munmap(p, alloc);
}

#define OBF_JCC_TANGLE() \
    __asm__ __volatile__( \
        "xor %%eax, %%eax\n\t" \
        "sub $1, %%eax\n\t" \
        "inc %%eax\n\t" \
        "jns 1f\n\t" \
        "ud2\n\t" \
        "1:\n\t" \
        :::"eax","cc","memory")

static char FLAG[256];

static const unsigned char KEY_OBF[21] = {
    76, 75, 20, 113, 122, 100, 87, 87, 101, 92, 122, 20,118, 122, 86, 21, 122, 96, 101, 86, 92
};
static char KEY[sizeof(KEY_OBF)+1];

static const uint8_t FLAG1_MASKED[45] = {

   0xB4, 0x20, 0x95, 0x44, 0x0C, 0x4E, 0x37, 0x07, 0x84, 0xFB, 0xFB, 0x72, 0x94, 0x1A, 0xD0, 0xA3, 0x0A, 0x5C, 0x46, 0x91, 0x38, 0xE0, 0x4B, 0x61, 0x15, 0x1A, 0x04, 0x51, 0x38, 0xC2, 0x7D, 0x1D, 0x6C, 0xD1, 0xF1, 0x22, 0x71, 0xD6, 0xCB, 0xD3, 0x2F, 0x3C, 0x8B, 0x9F, 0x61};
/* 将输入按算法编码为 hex：r = rol8( b ^ key[i%k], (i&3)+1 ) */
static void encode2_makehex(const char* in, const char* key, char* hex_out, size_t hex_cap){
    size_t n = strlen(in), k = strlen(key);
    static const char HX[] = "0123456789abcdef";
    size_t pos=0;

    OBF_GOTO_NEVER(EH0);
    OBF_STACK_CONFUSION;
EH0:;

    for (size_t i=0; i<n && pos+2<hex_cap; i++){
        uint8_t b = (uint8_t)in[i];
        uint8_t t = (uint8_t)(b ^ (uint8_t)key[i%k]);
        uint8_t sh = (uint8_t)((i & 3) + 1);
        uint8_t s = (uint8_t)((uint8_t)(t << sh) | (uint8_t)(t >> (uint8_t)(8 - sh)));
        hex_out[pos++] = HX[(s>>4)&0xF];
        hex_out[pos++] = HX[s&0xF];
        if (pos >= hex_cap) break;
        JUNK_ASM;
    }
    hex_out[pos] = '\0';
}

/* 还原 flag1 明文（运行时恢复，避免明文出现在二进制中） */
static void recover_flag1_plain(char* out, size_t outcap){
    size_t L = sizeof(FLAG1_MASKED), k = strlen(KEY);
    OBF_OPAQUE_PREDICATE(RP0);
    __asm__ __volatile__(".byte 0x2E,0x90");
RP0:;
   
    if (outcap < L+1){ out[0]='\0'; return; }
    for (size_t i=0;i<L;i++){
        uint8_t m = FLAG1_MASKED[i];
        uint8_t t = (uint8_t)(m ^ ((uint8_t)KEY[i%k] ^ 0x3C));
        uint8_t sh = (uint8_t)((i & 3) + 1);
        uint8_t r = (uint8_t)((uint8_t)(t << sh) | (uint8_t)(t >> (uint8_t)(8 - sh)));
        out[i] = (char)(r ^ 0xA5);
        JUNK_ASM1;
    }
    out[L] = '\0';
}


static int check_flag1_encrypt_cmp(const char* in){
    JUNK_ASM;

    OBF_GOTO_NEVER(L1);
    __asm__ __volatile__(".byte 0x0F,0x1F,0x00");
L1:;

    char expect_plain[128];
    recover_flag1_plain(expect_plain, sizeof(expect_plain));

    OBF_STACK_CONFUSION;
    __asm__ __volatile__(".byte 0x2E,0x90");
L2:;

    char expect_hex[1024], in_hex[1024];
    encode2_makehex(expect_plain, KEY, expect_hex, sizeof(expect_hex));
    encode2_makehex(in,           KEY, in_hex,     sizeof(in_hex));

    /* 脏边 #3 */
    OBF_OPAQUE_PREDICATE(L3);
    __asm__ __volatile__(".byte 0x66,0x0F,0x1F,0x44,0x00,0x00"); // 长 NOP
L3:;

    JUNK_ASM1;
    return strcmp(expect_hex, in_hex) == 0;
}


static int hex_to_bytes(const char* hex, uint8_t* out, size_t cap){
    size_t n = strlen(hex); if (n%2) return -1;
    size_t m = n/2; if (m>cap) return -1;
    
    OBF_STACK_CONFUSION;
    
    for (size_t i=0;i<m;i++){
        char c1=hex[2*i], c2=hex[2*i+1];
        int v1 = (c1>='0'&&c1<='9')?c1-'0':(c1>='a'&&c1<='f')?c1-'a'+10:(c1>='A'&&c1<='F')?c1-'A'+10:-1;
        int v2 = (c2>='0'&&c2<='9')?c2-'0':(c2>='a'&&c2<='f')?c2-'a'+10:(c2>='A'&&c2<='F')?c2-'A'+10:-1;
        if (v1<0||v2<0) return -1; out[i]=(uint8_t)((v1<<4)|v2);
    }
    return (int)m;
}

/* 解码： t = ror8(byte, (i&3)+1); plain = t ^ key[i%k] */
static void decode2_from_hex(const char* enc_hex, const char* key, char* out, size_t outcap){
    uint8_t buf[1024]; int m = hex_to_bytes(enc_hex, buf, sizeof(buf));
    if (m<=0 || (size_t)m+1>outcap){ out[0]='\0'; return; }
    size_t k = strlen(key);

    OBF_GOTO_NEVER(DH0);
    __asm__ __volatile__(".byte 0x0F,0x1F,0x40,0x00");
DH0:;

    for (int i=0;i<m;i++){
        uint8_t s = buf[i];
        uint8_t sh = (uint8_t)((i & 3) + 1);
        uint8_t r = (uint8_t)((uint8_t)(s >> sh) | (uint8_t)(s << (uint8_t)(8 - sh))); // ror8
        out[i] = (char)(r ^ (uint8_t)key[i%k]);
        JUNK_ASM;
    }
    out[m] = '\0';
}

static int encode2(const char* user, const char* enc_hex){
    char plain[512]; 
    OBF_OPAQUE_PREDICATE(E2L);
E2L:;
    decode2_from_hex(enc_hex, KEY, plain, sizeof(plain));
    return (strcmp(user, plain) == 0);
}

/* ---------------- flag2：极简 VM + RC4 ---------------- */
enum { OP_PUSH8=1, OP_PUSH32=3, OP_POP=4, OP_DUP=5, OP_LOADB=0x20, OP_STOREB=0x21, OP_RET=0x34, OP_RC4_KSA=0x40, OP_RC4_PRGA=0x41 };
typedef struct { const uint8_t* code; size_t clen; uint8_t* heap; size_t hlen; uint32_t st[512]; int sp; size_t pc; int halted; } VM;
static inline uint8_t  rd8 (VM* v){ return v->code[v->pc++]; }
static inline uint32_t rd32(VM* v){ uint32_t x=v->code[v->pc]|(v->code[v->pc+1]<<8)|(v->code[v->pc+2]<<16)|(v->code[v->pc+3]<<24); v->pc+=4; return x; }
static inline void push(VM* v, uint32_t x){ v->st[v->sp++]=x; }
static inline uint32_t pop (VM* v){ return v->st[--v->sp]; }

#define HEAP_SIZE  0x4000
#define RC4_S      0x0000
#define RC4_I      0x0100
#define RC4_J      0x0101
#define BUF_KEY    0x0200
#define SRC        0x0600
#define DST        0x0A00

static const char *VM_KEY = "sneaky_key";
static const uint8_t VM_CT[] = { /* RC4(key="sneaky_key", pt="flag{easy_Vm_using_Rc4_algo_1S_s0_E@sy}") */
    0x1c,0x5b,0xe6,0xc0,0xe1,0x3c,0xe8,0x9e,0xd3,0xb0,0x94,0xe2,0x87,0x8c,
    0x10,0xb9,0xa4,0xbf,0x88,0xd5,0x03,0x40,0x5b,0x56,0x9e,0x81,0x9d,0xee,
    0x3b,0x90,0x41,0xf4,0x42,0x65,0xcb,0xd7,0x41,0xd5,0xbf
};
static const uint32_t VM_LEN = sizeof(VM_CT);

static const uint8_t VM_CODE[] = {
    OP_PUSH32, RC4_I&0xFF,(RC4_I>>8)&0xFF,(RC4_I>>16)&0xFF,(RC4_I>>24)&0xFF, OP_PUSH8, 0x00, OP_STOREB,
    OP_PUSH32, RC4_J&0xFF,(RC4_J>>8)&0xFF,(RC4_J>>16)&0xFF,(RC4_J>>24)&0xFF, OP_PUSH8, 0x00, OP_STOREB,
    OP_PUSH32, RC4_S&0xFF,(RC4_S>>8)&0xFF,(RC4_S>>16)&0xFF,(RC4_S>>24)&0xFF,
    OP_PUSH32, BUF_KEY&0xFF,(BUF_KEY>>8)&0xFF,(BUF_KEY>>16)&0xFF,(BUF_KEY>>24)&0xFF,
    OP_PUSH32, (BUF_KEY-1)&0xFF,((BUF_KEY-1)>>8)&0xFF,((BUF_KEY-1)>>16)&0xFF,((BUF_KEY-1)>>24)&0xFF,
    OP_LOADB, OP_RC4_KSA,
    OP_PUSH32, RC4_I&0xFF,(RC4_I>>8)&0xFF,(RC4_I>>16)&0xFF,(RC4_I>>24)&0xFF,
    OP_PUSH32, RC4_J&0xFF,(RC4_J>>8)&0xFF,(RC4_J>>16)&0xFF,(RC4_J>>24)&0xFF,
    OP_PUSH32, RC4_S&0xFF,(RC4_S>>8)&0xFF,(RC4_S>>16)&0xFF,(RC4_S>>24)&0xFF,
    OP_PUSH32, SRC&0xFF,(SRC>>8)&0xFF,(SRC>>16)&0xFF,(SRC>>24)&0xFF,
    OP_PUSH32, DST&0xFF,(DST>>8)&0xFF,(DST>>16)&0xFF,(DST>>24)&0xFF,
    OP_PUSH32, VM_LEN&0xFF,(VM_LEN>>8)&0xFF,(VM_LEN>>16)&0xFF,(VM_LEN>>24)&0xFF,
    OP_RC4_PRGA, OP_RET
};
static int is_traced_via_proc(void){
    FILE *f = fopen("/proc/self/status", "r");
    if (!f) return 0;
    char line[256];
    int traced = 0;
    
    OBF_STACK_CONFUSION;
    
    while (fgets(line, sizeof(line), f)) {
        if (line[0]=='T' && !strncmp(line, "TracerPid:", 10)) {
            char *p = line + 10;
            while (*p==' ' || *p=='\t') ++p;
            traced = atoi(p);
            break;
        }
    }
    fclose(f);
    return traced != 0;
}
static void vm_run(VM* v){
    OBF_GOTO_NEVER(VM0);
    __asm__ __volatile__(".byte 0x0F,0x1F,0x84,0x00,0,0,0,0");
VM0:;
    while(!v->halted && v->pc < v->clen){
        uint8_t op = rd8(v);
        
        OBF_STACK_CONFUSION;
        
        switch(op){
            case OP_PUSH8:  push(v, rd8(v)); break;
            case OP_PUSH32: push(v, rd32(v)); break;
            case OP_POP: (void)pop(v); break;
            case OP_DUP: push(v, v->st[v->sp-1]); break;
            case OP_LOADB:{ uint32_t a=pop(v); if (a>=v->hlen){ v->halted=1; break; } push(v, v->heap[a]); } break;
            case OP_STOREB:{uint32_t a=pop(v), x=pop(v); if (a>=v->hlen){ v->halted=1; break; } v->heap[a]=(uint8_t)x; } break;
            case OP_RC4_KSA:{
                uint32_t klen=pop(v), kptr=pop(v), sptr=pop(v);
                if (sptr+256>v->hlen || kptr+klen>v->hlen){ v->halted=1; break; }
                uint8_t* S=v->heap+sptr; uint8_t j=0;
                for (uint32_t i=0;i<256;i++) S[i]=(uint8_t)i;
                for (uint32_t i=0;i<256;i++){ j=(uint8_t)(j+S[i]+v->heap[kptr+(i%klen)]); uint8_t t=S[i]; S[i]=S[j]; S[j]=t; }
            } break;
            case OP_RC4_PRGA:{
                uint32_t len=pop(v), dst=pop(v), src=pop(v), sptr=pop(v), iptr=pop(v), jptr=pop(v);
                if (sptr+256>v->hlen || src+len>v->hlen || dst+len>v->hlen || iptr+1>v->hlen || jptr+1>v->hlen){ v->halted=1; break; }
                uint8_t* S=v->heap+sptr; uint8_t i=v->heap[iptr], j=v->heap[jptr];
                for (uint32_t n=0;n<len;n++){ i=(uint8_t)(i+1); j=(uint8_t)(j+S[i]); uint8_t t=S[i]; S[i]=S[j]; S[j]=t; uint8_t K=S[(uint8_t)(S[i]+S[j])]; v->heap[dst+n]=v->heap[src+n]^K; }
                v->heap[iptr]=i; v->heap[jptr]=j;
            } break;
            case OP_RET: v->halted=1; break;
            default: v->halted=1; break;
        }
        JUNK_ASM1;
    }
}

static int check_flag2_vm_rc4(const char* in){
    size_t n = strlen(in);
    if (n != sizeof(VM_CT)) return 0;
    
    OBF_OPAQUE_PREDICATE(VM3L);
VM3L:;
    
    uint8_t heap[HEAP_SIZE]; memset(heap,0,sizeof(heap));
    size_t k = strlen(VM_KEY);
    heap[BUF_KEY-1] = (uint8_t)k;
    memcpy(heap+BUF_KEY, VM_KEY, k);
    memcpy(heap+SRC, in, n);

    VM v = (VM){0}; v.code=VM_CODE; v.clen=sizeof(VM_CODE); v.heap=heap; v.hlen=sizeof(heap);
    vm_run(&v);
    if (DST + sizeof(VM_CT) > HEAP_SIZE) return 0;
    return memcmp(heap+DST, VM_CT, sizeof(VM_CT)) == 0;
}



__attribute__((section(".text.encrypted")))
static void __libc_csu_init_encrypted(void){
    OBF_GOTO_NEVER(INIT_L1);
    __asm__ __volatile__(
        ".byte 0x48,0x31,0xC0\n\t"           // xor rax, rax
        ".byte 0x48,0xFF,0xC0\n\t"           // inc rax
        ".byte 0x48,0xFF,0xC8\n\t"           // dec rax
        ".byte 0x0F,0x1F,0x44,0x00,0x00\n\t" // NOP
    );
INIT_L1:;
    volatile size_t dummy = 0;
    for (size_t i=0;i<sizeof(KEY_OBF);++i) {
        OBF_STACK_CONFUSION;
        KEY[i]=(char)(KEY_OBF[i]^0x25);
        dummy += i;
    }
    KEY[sizeof(KEY_OBF)] = '\0';

    OBF_OPAQUE_PREDICATE(INIT_L2);
    __asm__ __volatile__(
        ".byte 0x66,0x2E,0x0F,0x1F,0x84,0x00,0,0,0,0\n\t"
    );
INIT_L2:;
    OBF_GOTO_NEVER(INIT_L3);
    __asm__ __volatile__(
        "push %%rax\n\t"
        "xor %%rax, %%rax\n\t"
        "cpuid\n\t"
        "pop %%rax\n\t"
        ".byte 0x0F,0x1F,0x00\n\t"
        : : : "rax","rbx","rcx","rdx","memory"
    );
INIT_L3:; 
    OBF_STACK_CONFUSION; 
    if (is_traced_via_proc()) {
        __asm__ __volatile__(
            "xor %%rdi, %%rdi\n\t"
            "mov $60, %%rax\n\t"
            "syscall\n\t"
            : : : "rax","rdi"
        );
        _exit(0);
    }

    OBF_OPAQUE_PREDICATE(INIT_L4);
    __asm__ __volatile__(
        ".byte 0x48,0x89,0xE5\n\t"
        ".byte 0x48,0x89,0xEC\n\t"
        ".byte 0x90\n\t"
    );
INIT_L4:;
}

static void __libc_csu_init(void){
    OBF_STACK_CONFUSION;
    void *func_ptr = (void*)__libc_csu_init_encrypted;
    size_t func_size = 0x21F3-0x20A0;
    
    size_t page_size = 4096;
    void *page_start = (void*)((uintptr_t)func_ptr & ~(page_size - 1));
    size_t offset = (uintptr_t)func_ptr - (uintptr_t)page_start;
    size_t total_size = offset + func_size;
    
    OBF_GOTO_NEVER(SMC_L1);
SMC_L1:;
    

    if (mprotect(page_start, total_size, PROT_READ | PROT_WRITE | PROT_EXEC) != 0) {
        return;
    }
    
    OBF_OPAQUE_PREDICATE(SMC_L2);
SMC_L2:;
    

    unsigned char *code = (unsigned char*)func_ptr;
    for (size_t i = 0; i < func_size; i++) {
        OBF_STACK_CONFUSION;
        code[i] ^= (SMC_INIT_KEY + (i & 0xFF));
        JUNK_ASM;
    }
    
    OBF_GOTO_NEVER(SMC_L3);
SMC_L3:;
    

    mprotect(page_start, total_size, PROT_READ | PROT_EXEC);
    
    OBF_STACK_CONFUSION;
    JUNK_ASM1;

    __libc_csu_init_encrypted();
}


__attribute__((used, section(".init_array.0102")))
static void (*__early_init_entry)(void) = __libc_csu_init;





static int check_all(const char* in){
    JUNK_ASM;
    OBF_STACK_CONFUSION;

    JUNK_ASM1;

    OBF_GOTO_NEVER(CHK_L1);
CHK_L1:;
    int ok1 = check_flag1_encrypt_cmp(in);     // flag1：XOR +位移→hex 对比
    JUNK_ASM;

    OBF_OPAQUE_PREDICATE(CHK_L2);
CHK_L2:;

    int ok2 = check_flag2_vm_rc4(in);          // flag2：VM+RC4
    JUNK_ASM1;

    OBF_STACK_CONFUSION;
    
    return (ok1 | ok2);
}

/* ---------------- main：简易交互 ---------------- */
int main(void){
    OBF_OPAQUE_PREDICATE(MAIN_L1);
MAIN_L1:;
    
    printf("Enter your flag:\n");
    fflush(stdout);
    OBF_STACK_CONFUSION;
    
    if (!fgets(FLAG, sizeof(FLAG), stdin)) return 0;
    size_t L = strlen(FLAG); if (L && FLAG[L-1]=='\n') FLAG[L-1]='\0';

    OBF_GOTO_NEVER(MAIN_L2);
MAIN_L2:;

    puts(check_all(FLAG) ? "Correct!" : "Incorrect!");
    return 0;
}