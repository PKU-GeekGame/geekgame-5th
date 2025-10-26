
import java.lang.foreign.*;
import java.lang.invoke.MethodHandle;
import java.nio.charset.StandardCharsets;

public class Solution {
    public static Object solve(Object sysInfo) throws Throwable {
        Linker linker = Linker.nativeLinker();
        SymbolLookup stdlib = linker.defaultLookup();
        MemorySegment getenv_addr = stdlib.find("getenv").orElseThrow();
        FunctionDescriptor getenv_desc = FunctionDescriptor.of(ValueLayout.ADDRESS, ValueLayout.ADDRESS);
        MethodHandle getenv = linker.downcallHandle(getenv_addr, getenv_desc);
        try (Arena arena = Arena.ofConfined()) {
            MemorySegment name = arena.allocateFrom("FLAG2");
            MemorySegment resultSegment = (MemorySegment) getenv.invoke(name);
            if (resultSegment.equals(MemorySegment.NULL)) {
                return "FLAG2 environment variable not set.";
            } else {
                return resultSegment.reinterpret(1024).getString(0, StandardCharsets.UTF_8);
//                return resultSegment.getString(0);
            }
        }
    }

    public static void main(String[] args) throws Throwable {
        System.out.println(solve(null));
    }
}