import itertools as it
import functools as ft
import time
def FPS(func):
    @ft.wraps(func)
    def agument(*args,**kwargs):
        def _fps():
            while True:
                yield time.time()
                func(*args,**kwargs)
        return it.pairwise(_fps())
    return agument


if __name__ == "__main__":
    # sp = FPS(time.sleep)
    # timepair = sp(1)
    # for i in timepair:
    #     print(i)
    pass