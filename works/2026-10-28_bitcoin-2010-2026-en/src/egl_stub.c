/* CPU-only skia never calls EGL; these stubs only satisfy the dynamic loader. */
#include <stddef.h>
void *eglGetCurrentDisplay(void) { return NULL; }
void *eglGetProcAddress(const char *name) { (void)name; return NULL; }
const char *eglQueryString(void *dpy, int name) { (void)dpy; (void)name; return NULL; }
