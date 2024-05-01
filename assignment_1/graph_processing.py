"""
This is a skeleton for the graph processing assignment.

We define a graph processor class with some function skeletons. Test
"""

from typing import List, Tuple

import numpy as np
import scipy as sp


class IDNotFoundError(Exception):
    pass


class InputLengthDoesNotMatchError(Exception):
    pass


class IDNotUniqueError(Exception):
    pass


class EdgePairNotUniqueError(Exception):
    pass


class GraphNotFullyConnectedError(Exception):
    pass


class GraphCycleError(Exception):
    pass


class EdgeAlreadyDisabledError(Exception):
    pass

# vertex_ids = [0, 1, 2, 3, 4, 5]
# edge_ids = [1, 2, 3, 4, 5]
# edge_vertex_id_pairs = [(0, 1), (1, 2), (1, 3), (3, 4), (3, 5)]
# edge_enabled = [True, True, True, True, True]
# source_vertex_id = 0

# class ParentError(Exception):
#     # print('Attempt to ')
#     pass


class GraphProcessor:
    """
    General documentation of this class.
    You need to describe the purpose of this class and the functions in it.
    We are using an undirected graph in the processor.
    """

    # add parent list, adjacency list and potentially more
    def __init__(
        self,
        vertex_ids: List[int],
        edge_ids: List[int],
        edge_vertex_id_pairs: List[Tuple[int, int]],
        edge_enabled: List[bool],
        source_vertex_id: int,
    ) -> None:
        """
        Initialize a graph processor object with an undirected graph.
        Only the edges which are enabled are taken into account.
        Check if the input is valid and raise exceptions if not.
        The following conditions should be checked:
            1. vertex_ids and edge_ids should be unique. (IDNotUniqueError)
            2. edge_vertex_id_pairs should have the same length as edge_ids. (InputLengthDoesNotMatchError)
            3. edge_vertex_id_pairs should contain valid vertex ids. (IDNotFoundError)
            4. edge_enabled should have the same length as edge_ids. (InputLengthDoesNotMatchError)
            5. source_vertex_id should be a valid vertex id. (IDNotFoundError)
            6. The graph should be fully connected. (GraphNotFullyConnectedError)
            7. The graph should not contain cycles. (GraphCycleError)
        If one certain condition is not satisfied, the error in the parentheses should be raised.

        Args:
            vertex_ids: list of vertex ids
            edge_ids: list of edge ids
            edge_vertex_id_pairs: list of tuples of two integer
                Each tuple is a vertex id pair of the edge.
            edge_enabled: list of bools indicating of an edge is enabled or not
            source_vertex_id: vertex id of the source in the graph
        """
        # put your implementation here
    
        # 1. vertex_ids and edge_ids should be unique
        if len(set(vertex_ids)) != len(vertex_ids):
            raise IDNotUniqueError("Vertex IDs are not unique")
        if len(set(edge_ids)) != len(edge_ids):
            raise IDNotUniqueError("Edge IDs are not unique")
        pass

        # 2. edge_vertex_id_pairs should have the same length as edge_ids
        if len(edge_vertex_id_pairs) != len(edge_ids):
            raise InputLengthDoesNotMatchError("Length of vertex-edge pairs list does not match edge ID list")

        # 3. edge_vertex_id_pairs should contain valid vertex ids
        for i in range(len(edge_ids)):
            vertex1, vertex2 = edge_vertex_id_pairs[i]

            if vertex1 not in vertex_ids or vertex2 not in vertex_ids:
                raise IDNotFoundError("Edge-vertex ID pair contains non-valid vertex ID")

        # 4. edge_enabled should have the same length as edge_ids
        if len(edge_enabled) != len(edge_ids):
            raise InputLengthDoesNotMatchError("Length of enabled edge list does not match edge ID list")

        # 5. source_vertex_id should be a valid vertex id
        if source_vertex_id not in vertex_ids:
            raise IDNotFoundError("Source vertex ID is not a valid vertex ID")
        
        # 6.  The graph should be fully connected

        # custom Errors
        if len(edge_vertex_id_pairs) != len(set(sort_tuple_list(edge_vertex_id_pairs))):
            raise EdgePairNotUniqueError("Multiple edges connecting same 2 vertices found")

        # 6. The graph should be fully connected
        # 7. The graph should not contain cycles (checked inside DFS)
        vertex_visited = []
        vertex_parents = {}
        # receive adjacency list
        adjacency_list = self.build_adjacency_list(edge_vertex_id_pairs, edge_enabled)
        self.DFS(adjacency_list, vertex_visited, float("Nan"), vertex_parents, source_vertex_id)
        
        if len(vertex_visited) != len(vertex_ids):
            raise GraphNotFullyConnectedError("Graph not fully connected")

        # 7. The graph should not contain cycles
        graph = {vertex: [] for vertex in vertex_ids}
        for edge_id, (u, v) in zip(edge_ids, edge_vertex_id_pairs):
            if edge_enabled[edge_id - 1]:
                graph[u].append(v)

        color = {}
        parent = {}
        for u in graph.keys():
            color[u] = 'W'
            parent[u] = None

        def dfs(u, color, parent):
            color[u] = 'G'
            for v in graph[u]:
                if color[v] == 'W':
                    parent[v] = u
                    cycle = dfs(v, color, parent)
                    if cycle == True:
                        return True
                elif color[v] == "G" and parent[u]!=v:
                    print ("Cycle found", u, v)
                    return True
            color[u] = "B"
            return False
        
        is_cyclic = False
        for u in graph.keys():
            if color[u] == 'W':
                is_cyclic = dfs(u, color, parent)
                if is_cyclic == True:
                    break
        
        if is_cyclic == True:
            raise GraphCycleError("There is a cycle in the graph")

        if len(vertex_visited) != len(vertex_ids):
            raise GraphNotFullyConnectedError("Graph not fully connected. Cannot reach all vertices.")

        return
    

    def DFS(self, adjacency_list, visited, parent, parent_list, start_node) -> List[int]:
        """
        Given an GraphProcessor, return Depth First Search visited nodes list and parent list.
        """

        # start DFS from start_node
        if start_node not in visited:  # check if node has been visited

            visited.append(start_node)
            parent_list[start_node] = parent  # assign parent of node

            for adjacent_vertex in adjacency_list[start_node]:
                if (adjacent_vertex in visited) & (adjacent_vertex != parent):
                    raise GraphCycleError("Cycle detected")
                self.DFS(adjacency_list, visited, start_node, parent_list, adjacent_vertex)

        return

    def build_adjacency_list(self, edge_vertex_id_pairs, edge_enabled):
        """
        Given an GraphProcessor, return an undirected adjacency list (only enabled edges used).
        """

        adjacency_list = {}
        enabled_edges = [num for num, m in zip(edge_vertex_id_pairs, edge_enabled) if m]

        for edge in enabled_edges:  # cycle through edge IDs
            u, v = edge  # tuple unpacking

            if u not in adjacency_list:  # check if list for vertex u exists
                adjacency_list[u] = []
            if v not in adjacency_list:  # check if list for vertex u exists
                adjacency_list[v] = []

            adjacency_list[u].append(v)
            adjacency_list[v].append(u)

        return adjacency_list

    def find_downstream_vertices(self, edge_id: int) -> List[int]:
        """
        Given an edge id, return all the vertices which are in the downstream of the edge,
            with respect to the source vertex.
            Including the downstream vertex of the edge itself!

        Only enabled edges should be taken into account in the analysis.
        If the given edge_id is a disabled edge, it should return empty list.
        If the given edge_id does not exist, it should raise IDNotFoundError.


        For example, given the following graph (all edges enabled):

            vertex_0 (source) --edge_1-- vertex_2 --edge_3-- vertex_4

        Call find_downstream_vertices with edge_id=1 will return [2, 4]
        Call find_downstream_vertices with edge_id=3 will return [4]

        Args:
            edge_id: edge id to be searched

        Returns:
            A list of all downstream vertices.
        """
        # put your implementation here
        pass

    def find_alternative_edges(self, disabled_edge_id: int) -> List[int]:
        """
        Given an enabled edge, do the following analysis:
            If the edge is going to be disabled,
                which (currently disabled) edge can be enabled to ensure
                that the graph is again fully connected and acyclic?
            Return a list of all alternative edges.
        If the disabled_edge_id is not a valid edge id, it should raise IDNotFoundError.
        If the disabled_edge_id is already disabled, it should raise EdgeAlreadyDisabledError.
        If there are no alternative to make the graph fully connected again, it should return empty list.


        For example, given the following graph:

        vertex_0 (source) --edge_1(enabled)-- vertex_2 --edge_9(enabled)-- vertex_10
                 |                               |
                 |                           edge_7(disabled)
                 |                               |
                 -----------edge_3(enabled)-- vertex_4
                 |                               |
                 |                           edge_8(disabled)
                 |                               |
                 -----------edge_5(enabled)-- vertex_6

        Call find_alternative_edges with disabled_edge_id=1 will return [7]
        Call find_alternative_edges with disabled_edge_id=3 will return [7, 8]
        Call find_alternative_edges with disabled_edge_id=5 will return [8]
        Call find_alternative_edges with disabled_edge_id=9 will return []

        Args:
            disabled_edge_id: edge id (which is currently enabled) to be disabled

        Returns:
            A list of alternative edge ids.
        """
        # put your implementation here

        

        pass

graph_processor = GraphProcessor(
    vertex_ids=vertex_ids,
    edge_ids=edge_ids,
    edge_vertex_id_pairs=edge_vertex_id_pairs,
    edge_enabled=edge_enabled,
    source_vertex_id=source_vertex_id
)

# other functions not dependent on specific class


def sort_tuple_list(edge_vertex_id_pairs) -> List[Tuple[int, int]]:

    # sort each tuple in ascending order
    sorted_tuple_list = [tuple(sorted(t)) for t in edge_vertex_id_pairs]

    # sort each tuple based on initial value
    sorted_tuple_list = sorted(sorted_tuple_list, key=lambda x: x[0])

    return sorted_tuple_list
