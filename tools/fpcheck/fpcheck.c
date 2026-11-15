/* fpcheck: 浮動小数点の結果が計算機・コンパイラで変わるかを確かめる。
 * 使い方: cc -O2 -o fpcheck fpcheck.c -lm && ./fpcheck out.bin > out.txt
 * out.bin を別の計算機の out.bin と compare.py で比べる。 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <float.h>

#define N 20000
static uint64_t s_ = 0x9E3779B97F4A7C15ULL;
static double rnd(void){ /* 0〜32、計算機によらず同じ列（整数から 2 の累乗の掛け算だけで作るので丸めが無い） */
  s_ ^= s_ << 13; s_ ^= s_ >> 7; s_ ^= s_ << 17;
  return ldexp((double)((s_ >> 11) | 1), -48);
}
static uint64_t fnv(const double *a, int n){
  uint64_t h = 1469598103934665603ULL; const unsigned char *p = (const unsigned char*)a;
  for (size_t i = 0; i < (size_t)n * 8; i++){ h ^= p[i]; h *= 1099511628211ULL; }
  return h;
}
static FILE *fb;
static void emit(const char *name, const double *a, int n){
  printf("%-22s %016llx\n", name, (unsigned long long)fnv(a, n));
  if (fb){ char tag[24]; memset(tag, 0, 24); strncpy(tag, name, 23);
    int32_t m = n; fwrite(tag, 1, 24, fb); fwrite(&m, 4, 1, fb); fwrite(a, 8, n, fb); }
}
static double x[N], y[N], r[N];

int main(int argc, char **argv){
  fb = argc > 1 ? fopen(argv[1], "wb") : NULL;
  /* --- 環境 --- */
#if defined(__aarch64__)
  printf("arch                   aarch64\n");
#elif defined(__x86_64__)
  printf("arch                   x86_64\n");
#else
  printf("arch                   other\n");
#endif
#ifdef __VERSION__
  printf("compiler               %s\n", __VERSION__);
#endif
  printf("FLT_EVAL_METHOD        %d\n", (int)FLT_EVAL_METHOD);
  printf("long double mantissa   %d bit\n", LDBL_MANT_DIG);
#ifdef __FAST_MATH__
  printf("fast-math              on\n");
#else
  printf("fast-math              off\n");
#endif
  { /* a*b+c が 1 回の丸め（FMA）にまとめられているか */
    volatile double a = 1.0 + 0x1p-27, b = 1.0 - 0x1p-27, c = -1.0;
    double a1 = a, b1 = b, c1 = c;
    double t = a1 * b1 + c1;
    printf("a*b+c contracted (FMA) %s\n", t == fma(a1, b1, c1) && t != 0.0 ? "yes" : "no");
    volatile double d = DBL_MIN; double e = d / 3.0;
    printf("subnormal kept         %s\n", e > 0.0 ? "yes" : "no (flush to zero)");
  }
  for (int i = 0; i < N; i++){ x[i] = rnd(); y[i] = rnd(); }

  /* --- 1. 四則と平方根（IEEE 754 で 1 通りに決まる） --- */
  for (int i = 0; i < N; i++) r[i] = x[i] + y[i]; emit("basic add", r, N);
  for (int i = 0; i < N; i++) r[i] = x[i] - y[i]; emit("basic sub", r, N);
  for (int i = 0; i < N; i++) r[i] = x[i] * y[i]; emit("basic mul", r, N);
  for (int i = 0; i < N; i++) r[i] = x[i] / y[i]; emit("basic div", r, N);
  for (int i = 0; i < N; i++) r[i] = sqrt(x[i]);  emit("basic sqrt", r, N);

  /* --- 2. 数学関数（ライブラリで最後の桁が変わりうる） --- */
  for (int i = 0; i < N; i++) r[i] = exp(x[i] - 16.0);   emit("libm exp", r, N);
  for (int i = 0; i < N; i++) r[i] = log(x[i]);          emit("libm log", r, N);
  for (int i = 0; i < N; i++) r[i] = pow(x[i], y[i]/8.); emit("libm pow", r, N);
  for (int i = 0; i < N; i++) r[i] = sin(x[i]);          emit("libm sin", r, N);
  for (int i = 0; i < N; i++) r[i] = cos(x[i]);          emit("libm cos", r, N);
  for (int i = 0; i < N; i++) r[i] = tanh(x[i] - 16.0);  emit("libm tanh", r, N);
  for (int i = 0; i < N; i++) r[i] = atan2(x[i], y[i]);  emit("libm atan2", r, N);
  for (int i = 0; i < N; i++) r[i] = cbrt(x[i]);         emit("libm cbrt", r, N);

  /* --- 3. 式の組み立て（FMA・和の順で変わりうる） --- */
  { double s = 0; for (int i = 0; i < N; i++) s += x[i] * y[i];
    r[0] = s; s = 0; for (int i = 0; i < N; i++) s += x[i]; r[1] = s;
    for (int i = 0; i < N; i++){ int j = (i + 1) % N; r[2 + i] = x[i] * y[i] - x[j] * y[j]; }
    emit("expr a*b-c*d", r + 2, N - 2);
    emit("expr dot,sum", r, 2); printf("  dot = %.17g\n  sum = %.17g\n", r[0], r[1]); }

  /* --- 4. 収束する反復：2 次元のラプラス方程式を Gauss-Seidel で解く --- */
  { enum { M = 48 }; static double u[M][M]; memset(u, 0, sizeof u);
    for (int j = 0; j < M; j++) u[0][j] = sin(3.14159265358979323846 * j / (M - 1));
    int it = 0; double res = 1;
    while (res > 1e-13 && it < 200000){ res = 0; it++;
      for (int i = 1; i < M - 1; i++) for (int j = 1; j < M - 1; j++){
        double v = 0.25 * (u[i-1][j] + u[i+1][j] + u[i][j-1] + u[i][j+1]);
        double d = fabs(v - u[i][j]); if (d > res) res = d; u[i][j] = v; } }
    emit("steady laplace", &u[0][0], M * M);
    printf("  iterations = %d, u(center) = %.17g\n", it, u[M/2][M/2]); }

  /* --- 5. 落ち着かない計算：ローレンツ系（カオス）を RK4 で積分 --- */
  { double X = 1, Y = 1, Z = 1, h = 0.001, out[10]; int k = 0;
    for (int n = 1; n <= 50000; n++){
      double k1x, k1y, k1z, k2x, k2y, k2z, k3x, k3y, k3z, k4x, k4y, k4z, a, b, c;
#define F(a,b,c,fx,fy,fz) fx = 10.0*((b)-(a)); fy = (a)*(28.0-(c))-(b); fz = (a)*(b)-(8.0/3.0)*(c);
      F(X, Y, Z, k1x, k1y, k1z)
      a = X + 0.5*h*k1x; b = Y + 0.5*h*k1y; c = Z + 0.5*h*k1z; F(a, b, c, k2x, k2y, k2z)
      a = X + 0.5*h*k2x; b = Y + 0.5*h*k2y; c = Z + 0.5*h*k2z; F(a, b, c, k3x, k3y, k3z)
      a = X + h*k3x; b = Y + h*k3y; c = Z + h*k3z; F(a, b, c, k4x, k4y, k4z)
      X += h/6*(k1x + 2*k2x + 2*k3x + k4x); Y += h/6*(k1y + 2*k2y + 2*k3y + k4y);
      Z += h/6*(k1z + 2*k2z + 2*k3z + k4z);
      if (n % 5000 == 0) out[k++] = X; }
    emit("chaos lorenz x(t)", out, 10);
    for (int i = 0; i < 10; i++) printf("  t = %2d  x = %.17g\n", 5 * (i + 1), out[i]); }

  /* --- 6. 落ち着かない計算の時間平均（ローレンツ系の z の平均、t = 50〜2000） --- */
  { double X = 1, Y = 1, Z = 1, h = 0.005, sz = 0; long cnt = 0;
    for (long n = 1; n <= 400000; n++){
      double k1x, k1y, k1z, k2x, k2y, k2z, k3x, k3y, k3z, k4x, k4y, k4z, a, b, c;
      F(X, Y, Z, k1x, k1y, k1z)
      a = X + 0.5*h*k1x; b = Y + 0.5*h*k1y; c = Z + 0.5*h*k1z; F(a, b, c, k2x, k2y, k2z)
      a = X + 0.5*h*k2x; b = Y + 0.5*h*k2y; c = Z + 0.5*h*k2z; F(a, b, c, k3x, k3y, k3z)
      a = X + h*k3x; b = Y + h*k3y; c = Z + h*k3z; F(a, b, c, k4x, k4y, k4z)
      X += h/6*(k1x + 2*k2x + 2*k3x + k4x); Y += h/6*(k1y + 2*k2y + 2*k3y + k4y);
      Z += h/6*(k1z + 2*k2z + 2*k3z + k4z);
      if (n > 10000){ sz += Z; cnt++; } }
    r[0] = sz / cnt; emit("chaos lorenz mean z", r, 1); printf("  mean z = %.17g\n", r[0]); }
  if (fb) fclose(fb);
  return 0;
}
