#include <jni.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sysinfo.h>
#include <unistd.h>

static jstring stripped_flag = NULL;

static void jail(JNIEnv *env) {
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
  // Read flag
  char *flag = getenv("FLAG3");
  if (!flag) return;
  // Strip `flag{` and `}`
  flag = strdup(flag);
  while (*flag != '{') ++flag;
  flag[strlen(flag) - 1] = '\0';
  // Create Java string and unset environment variable
  stripped_flag = (*env)->NewStringUTF(env, flag + 1);
  unsetenv("FLAG3");
}

JNIEXPORT jstring JNICALL Java_Flag3_getFlag(JNIEnv *env, jclass cls) {
  return stripped_flag;
}

JNIEXPORT jstring JNICALL Java_Flag3_sysInfo(JNIEnv *env, jclass cls) {
  jail(env);
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
