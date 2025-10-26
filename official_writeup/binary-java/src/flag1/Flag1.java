import module java.base;

public class Flag1 {
  private static byte[] classBytes;
  private static final ClassLoader classLoader;

  static {
    classLoader = new ClassLoader("SolutionLoader", ClassLoader.getSystemClassLoader()) {
      @Override
      protected Class<?> findClass(String name) throws ClassNotFoundException {
        return defineClass(name, classBytes, 0, classBytes.length);
      }
    };
  }

  public static void main(String[] args) throws Exception {
    var filePath = Paths.get(args[0]);
    classBytes = Files.readAllBytes(filePath);

    var f = new Flag1();

    var cls = classLoader.loadClass("Solution");
    var method = cls.getMethod("solve", Object.class);
    method.invoke(null, f);
  }

  private String flag;

  Flag1() {
    this.flag = getFlag();
  }

  private static native String getFlag();

  static {
    System.loadLibrary("flag1");
  }
}
