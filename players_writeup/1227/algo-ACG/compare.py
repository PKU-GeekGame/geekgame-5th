with open('hint1.txt', 'r') as f:
    a = f.read()
with open('new1.txt', 'r') as f:
    b = f.read()
c = ""    
for i in range(1416):
    if a[i]==b[i]:
        c = c + "0"
    else:
        c = c + "1"
print(c)