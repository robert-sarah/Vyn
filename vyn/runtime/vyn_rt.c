/* Runtime Vyn — lié statiquement au binaire final */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif

void vyn_io_print_f32(float val) {
    printf("%g\n", val);
    fflush(stdout);
}

void vyn_io_println_str(const char* s) {
    printf("%s\n", s);
    fflush(stdout);
}

void vyn_sys_sleep_ms(int ms) {
#ifdef _WIN32
    Sleep((DWORD)ms);
#else
    usleep((useconds_t)ms * 1000);
#endif
}

/* Profilage — rapport minimal sur stderr */
void vyn_profile_begin(const char* name) {
    fprintf(stderr, "[VynProfile] START %s\n", name);
}

void vyn_profile_end(const char* name, double elapsed_ms) {
    fprintf(stderr, "[VynProfile] END %s — %.3f ms\n", name, elapsed_ms);
}

/* FFI externe — stub pour démo */
int raw_hardware_call(int id) {
    return id * 2;
}
