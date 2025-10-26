.PHONY: all

all: Flag1.class libflag1.so blocker.jar

Flag1.class: Flag1.java
	javac $<

libflag1.so: flag1.c
	gcc -O3 -fPIC -shared -I"${JAVA_HOME}/include" -I"${JAVA_HOME}/include/linux" -o $@ $<

blocker.jar: agent/Blocker.java agent/agent.mf
	cd agent && javac Blocker.java && jar cfm ../$@ agent.mf *.class
