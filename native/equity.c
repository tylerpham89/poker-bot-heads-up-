/* Portable, freestanding C: no filesystem, network, threads or libc calls.
 * Official five-card scores are supplied by Python at startup.
 */
typedef unsigned long long U64;
typedef unsigned int U32;
#ifdef _WIN32
#define API __declspec(dllexport)
/* No CRT or TLS is used; satisfy the Windows shared-library entry contract. */
unsigned int _tls_index = 0;
int _DllMainCRTStartup(void *module, unsigned int reason, void *reserved) {
    (void)module; (void)reason; (void)reserved; return 1;
}
#else
#define API __attribute__((visibility("default")))
#endif
#define SIZE (1u<<20)
static U64 keys[SIZE];
static U32 values[SIZE];
static U32 hash(U64 x) { return (U32)((x * 11400714819323198485ull) >> 44); }
API void initialize(const U64 *masks, const U32 *scores, int n) {
    for (int i=0; i<n; ++i) {
        U32 h=hash(masks[i]);
        while(keys[h] && keys[h]!=masks[i]) h=(h+1)&(SIZE-1);
        keys[h]=masks[i]; values[h]=scores[i];
    }
}
static U32 lookup(U64 mask) {
    U32 h=hash(mask);
    while(keys[h]!=mask) h=(h+1)&(SIZE-1);
    return values[h];
}
static int triples(const int *b, int n, U64 *out) {
    int count=0;
    for(int i=0;i<n;i++) for(int j=i+1;j<n;j++) for(int k=j+1;k<n;k++)
        out[count++]=(1ull<<b[i])|(1ull<<b[j])|(1ull<<b[k]);
    return count;
}
static U32 eval(const int *h, const U64 *bm, int nb) {
    U32 best=0;
    for(int i=0;i<5;i++) for(int j=i+1;j<5;j++) {
        U64 pair=(1ull<<h[i])|(1ull<<h[j]);
        for(int k=0;k<nb;k++) {
            U32 score=lookup(pair|bm[k]);
            if(score>best) best=score;
        }
    }
    return best;
}
API U32 evaluate(const int *h, const int *b, int n) {
    U64 bm[10]; return eval(h,bm,triples(b,n,bm));
}
static U64 next(U64 *state) {
    U64 x=*state; x^=x>>12; x^=x<<25; x^=x>>27; *state=x;
    return x*2685821657736338717ull;
}
/* A very cheap opponent preflop descriptor, used only for range selection. */
static double prior(const int *h) {
    int rank[9]={0}, suit[4]={0}, high[4]={0}, sum=0;
    double x=0.45;
    for(int i=0;i<5;i++) {
        int r=h[i]>>2, s=h[i]&3; sum+=r; rank[r]++; suit[s]++;
        if(r>high[s]) high[s]=r;
    }
    x+=(sum-20)*0.004;
    for(int r=0;r<9;r++) {
        if(rank[r]>=2) x+=0.035+r*0.006;
        if(rank[r]>=3) x-=0.055*(rank[r]-2);
    }
    for(int s=0;s<4;s++) if(suit[s]>=2) x+=0.025+high[s]*0.003-(suit[s]-2)*0.018;
    return x;
}
/* Output columns: win share, visible opponent score, flop opponent score,
 * opponent preflop prior. Runouts and opponents are sampled without replacement.
 */
API void simulate(const int *hole, const int *board, int bn, int n, U64 seed, double *out) {
    U64 known=0, visible[10], flop[10];
    int b[5], opp[5];
    for(int i=0;i<5;i++) known|=1ull<<hole[i];
    for(int i=0;i<bn;i++) { b[i]=board[i]; known|=1ull<<board[i]; }
    int nv=triples(board,bn,visible), nf=bn>=3?triples(board,3,flop):0;
    U32 hero=bn==5?eval(hole,visible,nv):0;
    U32 pair_score[36][36];
    if(bn==5) {
        for(int a=0;a<36;a++) if(!(known&(1ull<<a)))
            for(int c=a+1;c<36;c++) if(!(known&(1ull<<c))) {
                U32 best=0; U64 p=(1ull<<a)|(1ull<<c);
                for(int k=0;k<nv;k++) { U32 v=lookup(p|visible[k]); if(v>best) best=v; }
                pair_score[a][c]=pair_score[c][a]=best;
            }
    }
    U64 state=seed?seed:1;
    for(int t=0;t<n;t++) {
        U64 used=known;
        for(int i=0;i<10-bn;i++) {
            int c;
            do { c=(int)(next(&state)%36); } while(used&(1ull<<c));
            used|=1ull<<c;
            if(i<5) opp[i]=c; else b[bn+i-5]=c;
        }
        U32 v, cur, fs;
        if(bn==5) {
            v=0;
            for(int i=0;i<5;i++) for(int j=i+1;j<5;j++) {
                U32 q=pair_score[opp[i]][opp[j]]; if(q>v) v=q;
            }
            cur=v;
        } else {
            U64 full[10]; triples(b,5,full);
            hero=eval(hole,full,10); v=eval(opp,full,10);
            cur=nv?eval(opp,visible,nv):0;
        }
        fs=bn==3?cur:(nf?eval(opp,flop,nf):0);
        out[t*4]=(hero>v)?1.0:((hero==v)?0.5:0.0);
        out[t*4+1]=(double)cur;
        out[t*4+2]=(double)fs;
        out[t*4+3]=prior(opp);
    }
}
