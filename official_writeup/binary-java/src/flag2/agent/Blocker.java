import module java.base;
import module java.instrument;

public class Blocker {
  public static void premain(String agentArgs, Instrumentation inst) {
    var transformer = new ClassFileTransformer() {
      @Override
      public byte[] transform(ClassLoader loader,
                              String className,
                              Class<?> classBeingRedefined,
                              ProtectionDomain protectionDomain,
                              byte[] classBytes) {
        if (loader != null && "SolutionLoader".equals(loader.getName())) {
          return block(classBytes);
        } else {
          return null;
        }
      }
    };
    inst.addTransformer(transformer, true);
  }

  private static byte[] block(byte[] classBytes) {
    var modified = new AtomicBoolean();
    var cf = ClassFile.of(ClassFile.DebugElementsOption.DROP_DEBUG);
    var classModel = cf.parse(classBytes);

    Predicate<MethodModel> invokes =
      mm -> mm.code()
              .map(cm -> cm.elementStream().anyMatch(Blocker::shouldBlock))
              .orElse(false);

    CodeTransform rewrite = (codeBuilder, codeElement) -> {
      if (shouldBlock(codeElement)) {
        var runtimeException = ClassDesc.of("java.lang.RuntimeException");
        codeBuilder.new_(runtimeException)                    
                   .dup()
                   .ldc("Calling blocked method")
                   .invokespecial(runtimeException, "<init>",
                                  MethodTypeDesc.ofDescriptor("(Ljava/lang/String;)V"),
                                  false)
                   .athrow();
        modified.set(true);
      } else {
        codeBuilder.with(codeElement);
      }
    };

    var ct = ClassTransform.transformingMethodBodies(invokes, rewrite);
    var newClassBytes = cf.transformClass(classModel, ct);
    return modified.get() ? newClassBytes : null;
  }

  private final static Set<String> blockedClasses = Set.of(
    "java/lang/Class",
    "java/lang/invoke/MethodHandles",
    "java/lang/ClassLoader",
    "java/lang/System",
    "java/lang/Runtime",
    "java/lang/ProcessBuilder"
  );

  private static boolean shouldBlock(CodeElement codeElement) {
    return codeElement instanceof InvokeInstruction i
        && blockedClasses.contains(i.owner().asInternalName());
  }
}
