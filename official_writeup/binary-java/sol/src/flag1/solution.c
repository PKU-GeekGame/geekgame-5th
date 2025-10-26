#include <jni.h>

JNIEXPORT jstring JNICALL Java_Solution_getFlag(JNIEnv *env, jclass cls, jobject obj) {
  jclass flagClass = (*env)->GetObjectClass(env, obj);
  jfieldID flagFieldID = (*env)->GetFieldID(env, flagClass, "flag", "Ljava/lang/String;");
  jstring flag = (jstring)(*env)->GetObjectField(env, obj, flagFieldID);
  return flag;
}
