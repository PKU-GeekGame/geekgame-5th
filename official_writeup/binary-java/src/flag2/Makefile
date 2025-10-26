.PHONY: all

all: Flag2.class libflag2.so blocker.jar

Flag2.class: Flag2.java
	javac $<

libflag2.so: flag2.c
	gcc -O3 -fPIC -shared -I"${JAVA_HOME}/include" -I"${JAVA_HOME}/include/linux" -o $@ $<

blocker.jar: agent/Blocker.java agent/agent.mf
	cd agent && javac Blocker.java && jar cfm ../$@ agent.mf *.class
