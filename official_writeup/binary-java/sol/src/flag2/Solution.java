import module java.base;

public class Solution {
  public static String solve(Object f) throws Throwable {
    var linker = Linker.nativeLinker();
    var getEnv = linker.downcallHandle(
      linker.defaultLookup().findOrThrow("getenv"),
      FunctionDescriptor.of(ValueLayout.ADDRESS, ValueLayout.ADDRESS)
    );
    try (var arena = Arena.ofConfined()) {
      var name = arena.allocateFrom("FLAG2");
      var ret = (MemorySegment) getEnv.invoke(name);
      return ret.reinterpret(1000).getString(0);
    }
  }
}
