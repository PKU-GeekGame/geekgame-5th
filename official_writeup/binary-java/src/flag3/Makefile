.PHONY: all

all: Flag3.class libflag3.so blocker.jar

Flag3.class: Flag3.java
	javac $<

libflag3.so: flag3.c
	gcc -O3 -fPIC -shared -I"${JAVA_HOME}/include" -I"${JAVA_HOME}/include/linux" -o $@ $<

blocker.jar: agent/Blocker.java agent/agent.mf
	cd agent && javac Blocker.java && jar cfm ../$@ agent.mf *.class
