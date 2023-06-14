import threading
import os


x = 0




def task1():
    global x
    print("Task 1 assigned to thread: {}".format(threading.current_thread().name))
    for i in range(10):
        x += 1
        print("T1: X value = " + str(x))
    print("ID of process running task 1: {}".format(os.getpid()))


def task2():
    global x
    print("Task 2 assigned to thread: {}".format(threading.current_thread().name))
    for i in range(10):
        x += 1
        print("T2: X value = " + str(x))
    print("ID of process running task 2: {}".format(os.getpid()))


if __name__ == "__main__":
    # print ID of current process
    print("ID of process running main program: {}".format(os.getpid()))

    # print name of main thread
    print("Main thread name: {}".format(threading.current_thread().name))

    # creating threads
    t1 = threading.Thread(target=task1, name='t1')
    t2 = threading.Thread(target=task2, name='t2')

    # starting threads
    t1.start()
    t2.start()

    # wait until all threads finish
    t1.join()
    t2.join()