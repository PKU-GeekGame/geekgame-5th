#include <jni.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static void jail() {
  if (chroot(".") != 0) {
    fprintf(stderr, "chroot failed\n");
    abort();
  }
  if (chdir("/") != 0) {
    fprintf(stderr, "chdir failed\n");
    abort();
  }
  if (setgid(65534) != 0 || setuid(65534) != 0) {
    fprintf(stderr, "setgid/setuid failed\n");
    abort();
  }
  // Try to chroot again, it should fail
  if (chroot(".") == 0) {
    fprintf(stderr, "chroot succeeded again\n");
    abort();
  }
}

JNIEXPORT jstring JNICALL Java_Flag1_getFlag(JNIEnv *env, jclass cls) {
  jail();
  const char *flag = getenv("FLAG1");
  jstring str = (*env)->NewStringUTF(env, flag ? flag : "notflag{}");
  unsetenv("FLAG1");
  return str;
}
