import module java.base;
import static java.lang.foreign.MemoryLayout.*;

public class Flag2 {
  private static byte[] classBytes;
  private static MemorySegment sysInfoSegment;
  private static final ClassLoader classLoader;

  static {
    new SysInfo();
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
    System.out.println(sysInfo());
  }

  private static Object parseSysInfo(long sysInfo) throws Exception {
    sysInfoSegment = MemorySegment.ofAddress(sysInfo).reinterpret(SYSINFO_LAYOUT.byteSize());
    var si = new SysInfo(sysInfoSegment);

    var cls = classLoader.loadClass("Solution");
    var method = cls.getMethod("solve", Object.class);
    return method.invoke(null, si);
  }

  private static native String sysInfo();

  static {
    System.loadLibrary("flag2");
  }

  private static final MemoryLayout SYSINFO_LAYOUT = MemoryLayout.structLayout(
    ValueLayout.JAVA_LONG.withName("uptime"),
    ValueLayout.JAVA_LONG.withName("load0"),
    ValueLayout.JAVA_LONG.withName("load1"),
    ValueLayout.JAVA_LONG.withName("load2"),
    ValueLayout.JAVA_LONG.withName("totalRam"),
    ValueLayout.JAVA_LONG.withName("freeRam"),
    ValueLayout.JAVA_LONG.withName("sharedRam"),
    ValueLayout.JAVA_LONG.withName("bufferRam"),
    ValueLayout.JAVA_LONG.withName("totalSwap"),
    ValueLayout.JAVA_LONG.withName("freeSwap"),
    ValueLayout.JAVA_SHORT.withName("procs"),
    ValueLayout.JAVA_SHORT,
    ValueLayout.JAVA_SHORT,
    ValueLayout.JAVA_SHORT,
    ValueLayout.JAVA_LONG.withName("totalHigh"),
    ValueLayout.JAVA_LONG.withName("freeHigh"),
    ValueLayout.JAVA_INT.withName("memUnit")
  ).withName("SysInfo");

  private static final VarHandle SYSINFO_UPTIME =
    SYSINFO_LAYOUT.varHandle(PathElement.groupElement("uptime"));
  private static final VarHandle SYSINFO_LOAD0 =
    SYSINFO_LAYOUT.varHandle(PathElement.groupElement("load0"));
  private static final VarHandle SYSINFO_LOAD1 =
    SYSINFO_LAYOUT.varHandle(PathElement.groupElement("load1"));
  private static final VarHandle SYSINFO_LOAD2 =
    SYSINFO_LAYOUT.varHandle(PathElement.groupElement("load2"));
  private static final VarHandle SYSINFO_TOTALRAM =
    SYSINFO_LAYOUT.varHandle(PathElement.groupElement("totalRam"));
  private static final VarHandle SYSINFO_FREERAM =
    SYSINFO_LAYOUT.varHandle(PathElement.groupElement("freeRam"));
  private static final VarHandle SYSINFO_SHAREDRAM =
    SYSINFO_LAYOUT.varHandle(PathElement.groupElement("sharedRam"));
  private static final VarHandle SYSINFO_BUFFERRAM =
    SYSINFO_LAYOUT.varHandle(PathElement.groupElement("bufferRam"));
  private static final VarHandle SYSINFO_TOTALSWAP =
    SYSINFO_LAYOUT.varHandle(PathElement.groupElement("totalSwap"));
  private static final VarHandle SYSINFO_FREESWAP =
    SYSINFO_LAYOUT.varHandle(PathElement.groupElement("freeSwap"));
  private static final VarHandle SYSINFO_PROCS =
    SYSINFO_LAYOUT.varHandle(PathElement.groupElement("procs"));
  private static final VarHandle SYSINFO_TOTALHIGH =
    SYSINFO_LAYOUT.varHandle(PathElement.groupElement("totalHigh"));
  private static final VarHandle SYSINFO_FREEHIGH =
    SYSINFO_LAYOUT.varHandle(PathElement.groupElement("freeHigh"));
  private static final VarHandle SYSINFO_MEMUNIT =
    SYSINFO_LAYOUT.varHandle(PathElement.groupElement("memUnit"));

  public static class SysInfo {
    public final long uptime;
    public final long load0;
    public final long load1;
    public final long load2;
    public final long totalRam;
    public final long freeRam;
    public final long sharedRam;
    public final long bufferRam;
    public final long totalSwap;
    public final long freeSwap;
    public final short procs;
    public final long totalHigh;
    public final long freeHigh;
    public final int memUnit;

    public SysInfo() {
      uptime = 0;
      load0 = 0;
      load1 = 0;
      load2 = 0;
      totalRam = 0;
      freeRam = 0;
      sharedRam = 0;
      bufferRam = 0;
      totalSwap = 0;
      freeSwap = 0;
      procs = 0;
      totalHigh = 0;
      freeHigh = 0;
      memUnit = 0;
    }

    public SysInfo(MemorySegment sysInfoSegment) {
      uptime = (long) SYSINFO_UPTIME.get(sysInfoSegment, 0);
      load0 = (long) SYSINFO_LOAD0.get(sysInfoSegment, 0);
      load1 = (long) SYSINFO_LOAD1.get(sysInfoSegment, 0);
      load2 = (long) SYSINFO_LOAD2.get(sysInfoSegment, 0);
      totalRam = (long) SYSINFO_TOTALRAM.get(sysInfoSegment, 0);
      freeRam = (long) SYSINFO_FREERAM.get(sysInfoSegment, 0);
      sharedRam = (long) SYSINFO_SHAREDRAM.get(sysInfoSegment, 0);
      bufferRam = (long) SYSINFO_BUFFERRAM.get(sysInfoSegment, 0);
      totalSwap = (long) SYSINFO_TOTALSWAP.get(sysInfoSegment, 0);
      freeSwap = (long) SYSINFO_FREESWAP.get(sysInfoSegment, 0);
      procs = (short) SYSINFO_PROCS.get(sysInfoSegment, 0);
      totalHigh = (long) SYSINFO_TOTALHIGH.get(sysInfoSegment, 0);
      freeHigh = (long) SYSINFO_FREEHIGH.get(sysInfoSegment, 0);
      memUnit = (int) SYSINFO_MEMUNIT.get(sysInfoSegment, 0);
    }
  }
}
