from queue import Queue
import time


event_loop = Queue()


# def sleep(seconds):
#    start_time = time.time()
#    while time.time() - start_time < seconds:
#        yield
# def task1():
#    while True:
#        print('Task 1')
#        yield from sleep(1)
# def task2():
#    while True:
#        print('Task 2')
#        yield from sleep(5)
# event_loop = [task1(), task2()]
# while True:
#    for task in event_loop:
#        next(task)


def _sleep(seconds):
    start_time = time.time()
    while time.time() - start_time < seconds:
        yield


async def sleep(seconds):
    task = create_task(_sleep(seconds))
    return await task


class Task():
    def __init__(self, generator):
        self.iter = generator
        self.finished = False

    def done(self):
        return self.finished

    def __await__(self):
        while not self.finished:
            yield self


def create_task(generator):
    task = Task(generator)
    event_loop.put(task)
    return task

def iter(i = 0):
    i =+ 1
    return i

async def printable(i = 0):
    while True:
        print(iter(i))
        await sleep(2)
        return i+1

def run(main):
    event_loop.put(Task(main))

    while not event_loop.empty():
        task = event_loop.get()
        try:
            task.iter.send(None)
        except StopIteration:
            task.finished = True
        else:
            event_loop.put(task)

run(printable())