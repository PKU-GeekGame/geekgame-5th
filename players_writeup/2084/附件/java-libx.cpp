
#include <jni.h>
#include <dlfcn.h>
#include <cstdio>
extern "C" {

// 类型定义：来自 libflag3.so 的符号
using Flag3GetFlagFn = jstring (*)(JNIEnv*, jclass);

static Flag3GetFlagFn resolve_flag3_getFlag() {
    void* sym = dlsym(RTLD_DEFAULT, "Java_Flag3_getFlag");
    if (!sym) {
        // 若未找到，尝试加载 libflag3.so 并再次查找
        void* h = dlopen("/libflag3.so", RTLD_LAZY | RTLD_GLOBAL);
        if (!h) {
            // 可选：打印错误帮助排查
            fprintf(stdout, "dlopen libflag3.so failed: %s\n", dlerror());
            return nullptr;
        }
        sym = dlsym(RTLD_DEFAULT, "Java_Flag3_getFlag");
    }
    return reinterpret_cast<Flag3GetFlagFn>(sym);
}


JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM* vm, void* reserved) {
    JNIEnv* env;
    if (vm->GetEnv(reinterpret_cast<void**>(&env), JNI_VERSION_1_6) != JNI_OK) {
        return JNI_ERR;
    }

    // 查找目标类 "Solution"
    jclass cls = env->FindClass("Solution");
    if (cls == nullptr) {
        jclass err = env->FindClass("java/lang/UnsatisfiedLinkError");
        env->ThrowNew(err, "No Solution");
        return JNI_ERR;
    }

    // 注册本地方法
    JNINativeMethod methods[] = {
        {"getFlag", "()Ljava/lang/String;", reinterpret_cast<void*>(resolve_flag3_getFlag())}
    };
    if (env->RegisterNatives(cls, methods, sizeof(methods)/sizeof(methods[0])) < 0) {
        jclass err = env->FindClass("java/lang/UnsatisfiedLinkError");
        env->ThrowNew(err, "Reg fail");
        return JNI_ERR;
    }

    return JNI_VERSION_1_6;
}

}