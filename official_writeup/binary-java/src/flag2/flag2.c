#include <jni.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/sysinfo.h>
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

JNIEXPORT jstring JNICALL Java_Flag2_getFlag(JNIEnv *env, jclass cls) {
  const char *flag = getenv("FLAG2");
  jstring str = (*env)->NewStringUTF(env, flag ? flag : "notflag{}");
  unsetenv("FLAG2");
  return str;
}

JNIEXPORT jstring JNICALL Java_Flag2_sysInfo(JNIEnv *env, jclass cls) {
  jail();
  struct sysinfo info;
  sysinfo(&info);
  jmethodID mid = (*env)->GetStaticMethodID(env, cls, "parseSysInfo",
                                            "(J)Ljava/lang/Object;");
  jobject obj =
      (*env)->CallStaticObjectMethod(env, cls, mid, (jlong)(uintptr_t)&info);
  if (!(*env)->IsInstanceOf(env, obj,
                            (*env)->FindClass(env, "java/lang/String"))) {
    return NULL;
  }
  return (jstring)obj;
}
