from riscemv.Tomasulo import Tomasulo

class Multithreading():
    threads = []


    def add_thread(self, thread:Tomasulo):
        self.threads.append(thread)


    def step(self):
        for thr in self.threads:
            thr.step()
