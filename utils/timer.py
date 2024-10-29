import time

class Timer:
    start: float = 0

    def __init__(self):
        self.start = time.time()

    def get_elapsed_time(self):
        hour, rem = divmod(time.time() - self.start, 3600) # get hours
        minutes, seconds = divmod(rem, 60) # get minutes and seconds
        elapsed_time = f"Elapsed time: {int(hour)} hours, {int(minutes)} minutes, {seconds:.2f} seconds"
        return elapsed_time