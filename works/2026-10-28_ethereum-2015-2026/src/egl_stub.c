/* Minimal EGL stub: skia-python links these three symbols but CPU raster never calls them. */
#include <stddef.h>
void *eglGetCurrentDisplay(void) { return NULL; }
void *eglGetProcAddress(const char *name) { (void)name; return NULL; }
const char *eglQueryString(void *dpy, int name) { (void)dpy; (void)name; return NULL; }
