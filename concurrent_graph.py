import cProfile
import random
import time
from multiprocessing import Event, Lock, Manager, Process, Queue, Value
from typing import Hashable, List, Optional, Tuple


class ConcurrentGraph:
    def __init__(self):
        self.graph = {}
        self.lock = Lock()

    def add_vertex(self, vertex: Hashable) -> bool:
        with self.lock:
            if vertex in self.graph:
                return False
            self.graph[vertex] = {}
            return True

    def add_edge(self, vertex1: Hashable, vertex2: Hashable, weight: float = 0) -> bool:
        with self.lock:
            if vertex1 not in self.graph or vertex2 not in self.graph:
                return False
            if vertex2 in self.graph[vertex1]:
                return False
            self.graph[vertex1][vertex2] = weight
            return True

    def remove_vertex(self, vertex: Hashable) -> Optional[dict]:
        with self.lock:
            for v in self.graph:
                if vertex in self.graph[v]:
                    del self.graph[v][vertex]
            return self.graph.pop(vertex, None)

    def remove_edge(self, vertex1: Hashable, vertex2: Hashable) -> bool:
        with self.lock:
            if vertex1 in self.graph and vertex2 in self.graph[vertex1]:
                del self.graph[vertex1][vertex2]
                return True
            return False

    def generate_connected_graph(self, num_vertices: int) -> None:
        for vertex in range(num_vertices):
            self.add_vertex(vertex)
        for vertex in range(1, num_vertices):
            self.add_edge(vertex - 1, vertex)
        for _ in range(num_vertices * 2):
            vertex1 = random.randint(0, num_vertices - 1)
            vertex2 = random.randint(0, num_vertices - 1)
            if vertex1 != vertex2:
                self.add_edge(vertex1, vertex2)

    def get_vertices(self) -> List[Hashable]:
        with self.lock:
            return list(self.graph.keys())

    def get_edges(self) -> List[Tuple[Hashable, Hashable]]:
        with self.lock:
            edges = []
            for vertex, neighbors in self.graph.items():
                for neighbor in neighbors:
                    edges.append((vertex, neighbor))
            return edges

    def get_adjacent_vertices(self, vertex: Hashable) -> List[Hashable]:
        with self.lock:
            if vertex not in self.graph:
                raise KeyError(f"Vertex {vertex} is not in the graph.")
            return list(self.graph[vertex].keys())

    def get_degree(self, vertex: Hashable) -> int:
        with self.lock:
            if vertex not in self.graph:
                raise KeyError(f"Vertex {vertex} is not in the graph.")
            return len(self.graph[vertex])

    def is_connected(self, vertex1: Hashable, vertex2: Hashable) -> bool:
        with self.lock:
            if vertex1 not in self.graph:
                raise KeyError(f"Vertex {vertex1} is not in the graph.")
            if vertex2 not in self.graph:
                raise KeyError(f"Vertex {vertex2} is not in the graph.")
            return vertex2 in self.graph[vertex1] or vertex1 in self.graph[vertex2]

    def multiprocessing_bfs(self, start_vertex, num_processes=4):
        manager = Manager()
        visited = manager.dict()
        queue = Queue()
        queue.put(start_vertex)
        processes = []
        wait_events = []
        program_is_running = Value("b", True)
        for _ in range(num_processes):
            wait_event = Event()
            wait_events.append(wait_event)
            p = Process(
                target=self._multiprocessing_bfs_worker,
                args=(queue, visited, wait_event, program_is_running),
            )
            p.start()
            processes.append(p)
        while any(not event.is_set() for event in wait_events):
            time.sleep(1)
        program_is_running.value = False
        for _ in range(num_processes):
            queue.put(None)
        for p in processes:
            p.join()
        return list(visited)

    def _multiprocessing_bfs_worker(self, queue, visited, wait_event, keep_working, batch_size=10000):
        local_queue = []
        vertices_processed = 0
        while keep_working.value:
            if (
                vertices_processed % batch_size == 0
                and vertices_processed != 0
                and local_queue
            ):
                queue.put(local_queue.pop(0))
            if not local_queue:
                wait_event.set()
                local_queue.append(queue.get())
                wait_event.clear()
            else:
                vertex = local_queue.pop()
                if vertex is None:
                    break
                if vertex not in visited:
                    visited[vertex] = True
                    vertices_processed += 1
                    for adjacent_vertex in self.graph[vertex]:
                        local_queue.append(adjacent_vertex)

    def bfs(self, start_vertex: Hashable) -> List[Hashable]:
        visited = set()
        queue = [start_vertex]
        bfs_order = []
        while queue:
            current_vertex = queue.pop(0)
            if current_vertex not in visited:
                visited.add(current_vertex)
                bfs_order.append(current_vertex)
                for adjacent_vertex in self.graph.get(current_vertex, []):
                    if adjacent_vertex not in visited:
                        queue.append(adjacent_vertex)
        return bfs_order

    def __str__(self):
        out = ""
        for key in self.graph:
            out += str(key) + ": " + str(self.graph[key]) + "\n"
        return out


def profile_bfs_methods():
    graph = ConcurrentGraph()
    graph.generate_connected_graph(100000)
    print("Profiling regular BFS...")
    cProfile.runctx("graph.bfs(0)", globals(), locals())
    print("\nProfiling multiprocessing BFS...")
    cProfile.runctx("graph.multiprocessing_bfs(0)", globals(), locals())


if __name__ == "__main__":
    profile_bfs_methods()
