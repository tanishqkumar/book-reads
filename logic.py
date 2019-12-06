# factorial
x = int(input()) # this stores how many ints we're going to input
counter = 0
oList = []

def fact(n):
    while n != 1:

    # if n == 1:
    #     return 1
    # else:
    #     return (fact(n-1) * n)

for lol in range(x): # implement Z function here
    a = int(input())
    f = fact(a)
    # implement functionality to be able to determine number of 0s trailing f
    while (f % 10) == 0:
        f /= 10
        counter += 1
    oList.append(counter)
for element in oList:
    print(element)
