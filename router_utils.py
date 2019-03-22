from haversine import haversine
from collections import defaultdict
import overpy
import pandas as pd
import networkx as nx
from networkx.algorithms.shortest_paths.generic import shortest_path
import matplotlib.pyplot as plt
from postman_problems.solver import cpp

def compute_road_length(road_nodes):
    total_distance = 0
    for i in range(len(road_nodes) - 1):
        n1 = road_nodes[i]
        n2 = road_nodes[i + 1]
        total_distance += haversine((n1.lat, n1.lon), (n2.lat, n2.lon))
    return total_distance


def get_node_to_ways_map(ways, remove_nodes):
    node_to_ways = defaultdict(list)
    for way_id, way in ways.items():
        for node in way.nodes:
            if node.id in remove_nodes:
                continue
            node_to_ways[node.id].append(way_id)
    return node_to_ways


def get_way_segments(ways, intersections, remove_nodes):
    way_segments = dict()

    dead_ends = dict()
    # print('getting_way_segments for:')
    for way_id, way in ways.items():

        # print(way_id)
        # print('way_id', way_id)
        nodes = [n for n in way.nodes if n.id not in remove_nodes]

        first_node_id = nodes[0].id
        last_node_id = nodes[-1].id
        print('way_id:{} first_id:{} last_id:{}'.format(way_id, first_node_id, last_node_id))
        if first_node_id not in intersections:
            dead_ends[first_node_id] = way
        if last_node_id not in intersections:
            dead_ends[last_node_id] = way

        current_segment = []
        i = 0
        for node in nodes:
            # print('node', node)
            if node.id in dead_ends or node.id in intersections:
                if len(current_segment):
                    current_segment.append(node)
                    way_segments[(way_id, i)] = current_segment
                    current_segment = [node]
                    i += 1
                else:
                    current_segment.append(node)
            else:
                current_segment.append(node)
    print('dead_ends')
    for k, v in dead_ends.items():
        print(k, v.id)

    print('way segments')
    for k, v in way_segments.items():
        print(k, [vi.id for vi in v])
    return way_segments


def get_cpp_circuit(query, starting_node, remove_nodes = None):
    if remove_nodes is None:
        remove_nodes = set()
    api = overpy.Overpass()
    result = api.query(query)
    node_map = {node.id: node for node in result.nodes if node.id not in remove_nodes}

    ways = {way.id: way for way in result.ways}

    print('got back {} nodes and {} ways'.format(len(node_map), len(ways)))
    for w in ways.keys():
        print(w)
    node_to_ways = get_node_to_ways_map(ways, remove_nodes)
    print('node_to_ways')
    for k, v in sorted(node_to_ways.items()):
        print(k, v)
    intersections = {k for k, v in node_to_ways.items() if len(v) > 1}
    print('intersections')
    for k in sorted(intersections):
        print(k)
    way_segments = get_way_segments(ways, intersections, remove_nodes)

    node_pair_to_way_segment = {}

    vals = []
    for key, way_segment in way_segments.items():
        sorted_pair = tuple(sorted([way_segment[0].id, way_segment[-1].id]))
        node_pair_to_way_segment[sorted_pair] = way_segment
        vals.append({
            'trail': '_'.join([str(s) for s in key]),
            'node1': way_segment[0].id,
            'node2': way_segment[-1].id,
            'lat1': way_segment[0].lat,
            'lon1': way_segment[0].lon,
            'lat2': way_segment[-1].lat,
            'lon2': way_segment[-1].lon,
            'distance': compute_road_length(way_segment)
        })
    df = pd.DataFrame(vals)
    print(df)
    df.to_csv(r'C:\tmp\cpp_df.csv')
    df = remove_unconnected_nodes(df, starting_node)
    print(df)

    path = r'C:\tmp\mountview_df.csv'
    export_datapoints(df, path)

    circuit, graph = cpp(edgelist_filename=path,
                         start_node='x_{}'.format(starting_node))

    distance = sum([c[3]['distance'] for c in circuit])
    print('total_distance:{}'.format(distance))
    circuit_node_ids = [int(x[0][2:]) for x in circuit]

    circuit_vals = []
    circuit_nodes = []
    for x in circuit:
        node_id = int(x[0][2:])
        node = node_map[node_id]
        node2_id = int(x[1][2:])
        node2 = node_map[node2_id]
        trail = x[3]['trail']
        trail_split = trail.split('_')
        way = trail_split[1]
        distance = x[3]['distance']
        augmented = x[3].get('augmented', False)
        way_segment = (int(trail_split[1]), int(trail_split[2]))

        circuit_nodes.append(node)
        circuit_vals.append({'lat': node.lat,
                             'lon': node.lon,
                             'lat2': node2.lat,
                             'lon2': node2.lon,
                             'trail': trail,
                             'distance': distance,
                             'augmented': augmented,
                             'way_segment': way_segment,
                             'way': way,
                             'node': node.id,
                             'node2': node2.id})

    circuit_df = pd.DataFrame(circuit_vals)
    for col in ['lat', 'lon']:
        circuit_df[col] = circuit_df[col].astype('float')

    return circuit_df, circuit, way_segments


def remove_unconnected_nodes(df, starting_node):
    to_remove = []
    G = nx.Graph()
    for i, row in df.iterrows():
        G.add_edge(row['node1'], row['node2'], attr=row['trail'])

    for n in G.nodes:
        try:
            x = shortest_path(G, n, starting_node)
        except Exception:
            to_remove.append(n)
    print('removing {} unconnected nodes'.format(len(to_remove)))
    df = df.loc[~df['node1'].isin(to_remove)].loc[~df['node2'].isin(to_remove)]
    return df


def export_datapoints(df, path):
    for col in ['node1', 'node2', 'trail']:
        df[col] = df[col].astype('str')

    # the library likes strings
    df['node1'] = df['node1'].apply(lambda x: 'x_{}'.format(x))
    df['node2'] = df['node2'].apply(lambda x: 'x_{}'.format(x))
    df['trail'] = df['trail'].apply(lambda x: 'x_{}'.format(x))
    df[['node1', 'node2', 'trail', 'distance']].to_csv(path, index=False)


import matplotlib.pyplot as plt
import tilemapbase


def draw_circuit(circuit_df, filepath):
    tilemapbase.start_logging()
    tilemapbase.init(create=True)

    # Use open street map
    t = tilemapbase.tiles.OSM

    delta = 0.002
    min_lat = circuit_df['lat'].min()
    max_lat = circuit_df['lat'].max()
    min_lon = circuit_df['lon'].min()
    max_lon = circuit_df['lon'].max()

    extent = tilemapbase.Extent.from_lonlat(min_lon - delta,
                                            max_lon + delta,
                                            min_lat - delta,
                                            max_lat + delta)
    extent = extent.to_aspect(1.0)

    longs = circuit_df['lon'].astype('float').to_list()
    lats = circuit_df['lat'].astype('float').to_list()
    nodeids = circuit_df['node'].astype('float').to_list()
    path = [tilemapbase.project(x, y) for x, y in zip(longs, lats)]
    x, y = zip(*path)

    fig, ax = plt.subplots(figsize=(40, 40))

    plotter = tilemapbase.Plotter(extent, tilemapbase.tiles.OSM, width=400)
    plotter.plot(ax)
    import matplotlib.cm as cm
    import numpy as np
    colors = cm.rainbow(np.linspace(0, 1, len(y)))

    for i in range(len(y)-2):
        plt.plot(x[i:i+2], y[i:i+2], linewidth=10)#, color=colors[i], markersize=20)#, "ro-", markersize=20)

    # ax.plot(x, y, "ro-", markersize=20)

    node_to_num = defaultdict(list)
    for i, node_id in enumerate(nodeids):
        node_to_num[node_id].append(i)


    # unique = set()
    # for xi, yi, ni in zip(x, y, nodeids):
    #     if (xi, yi) not in unique:
    #         unique.add((xi, yi))
    #         label = ','.join(map(str, node_to_num[ni]))
    #         plt.annotate(i, label, (xi + .0000003, yi), size=40)

    plt.savefig(filepath, format='jpg')


def plot_nodes_ways(nodes, ways):
    tilemapbase.start_logging()
    tilemapbase.init(create=True)

    # Use open street map
    t = tilemapbase.tiles.OSM

    delta = 0.002
    min_lat = circuit_df['lat'].min()
    max_lat = circuit_df['lat'].max()
    min_lon = circuit_df['lon'].min()
    max_lon = circuit_df['lon'].max()

    extent = tilemapbase.Extent.from_lonlat(min_lon - delta,
                                            max_lon + delta,
                                            min_lat - delta,
                                            max_lat + delta)
    extent = extent.to_aspect(1.0)

    longs = circuit_df['lon'].astype('float').to_list()
    lats = circuit_df['lat'].astype('float').to_list()
    path = [tilemapbase.project(x, y) for x, y in zip(longs, lats)]
    x, y = zip(*path)

    fig, ax = plt.subplots(figsize=(40, 40))

    plotter = tilemapbase.Plotter(extent, tilemapbase.tiles.OSM, width=1200)
    plotter.plot(ax)
    ax.plot(x, y, "ro", markersize=20)

    i = 1
    unique = set()
    for xi, yi in zip(x, y):
        if (xi, yi) not in unique:
            unique.add((xi, yi))
            plt.annotate(str(i), (xi + .0000003, yi), size=40)
            i += 1
    plt.savefig(filepath, format='jpg')

def generate_gpx(circuit_df, way_segments, filepath):

#def generate_gpx(circuit, way_segments, filepath):
    header = '''<?xml version="1.0" encoding="UTF-8"?>
    <gpx creator="StravaGPX" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd http://www.garmin.com/xmlschemas/GpxExtensions/v3 http://www.garmin.com/xmlschemas/GpxExtensionsv3.xsd http://www.garmin.com/xmlschemas/TrackPointExtension/v1 http://www.garmin.com/xmlschemas/TrackPointExtensionv1.xsd" version="1.1" xmlns="http://www.topografix.com/GPX/1/1" xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1" xmlns:gpxx="http://www.garmin.com/xmlschemas/GpxExtensions/v3">
     <metadata>
      <time>{time:%Y-%m-%d}T{time:%H:%M:%S}Z</time>
     </metadata>
     <trk>
      <name>20T with Eric in Toronto</name>
      <type>9</type>
      <trkseg>'''

    point_template = '''<trkpt lat="{lat}" lon="{lon}">
    <ele>113.0</ele>
    <time>{time:%Y-%m-%d}T{time:%H:%M:%S}Z</time>
    <extensions>
     <gpxtpx:TrackPointExtension>
      <gpxtpx:hr>95</gpxtpx:hr>
      <gpxtpx:cad>57</gpxtpx:cad>
     </gpxtpx:TrackPointExtension>
    </extensions>
   </trkpt>'''

    footer = '''</trkseg>
     </trk>
    </gpx>'''

    from datetime import timedelta
    import datetime as dt
    current_time = dt.datetime(2019, 3, 7, 12, 0, 0)

    total_nodes = 0
    gpx_txt = header.format(time=current_time)
    last_node = None
    first_node = None
    for i, row in circuit_df.iterrows():
        node1 = row['node']
        node2 = row['node2']
        trail = row['trail']
        # node1, node2, i, seg_dict
        #
        # trail = seg_dict['trail']
        _, way_id, num = trail.split('_')
        way_id = int(way_id)
        num = int(num)
        # print(way_id)
        nodes = way_segments[(way_id, num)]
        node1_int = node1
        if nodes[0].id != node1_int:
            nodes = reversed(nodes)
        # print(nodes)
        for node in nodes:
            if first_node == None:
                first_node = node
            if node != last_node:
                if last_node != None:
                    length = compute_road_length([last_node, node])
                else:
                    length = None
                last_node = node

                if total_nodes < 20000:
                    # print(length)
                    if length is None or length > 0:
                        total_nodes += 1
                        gpx_txt += point_template.format(lon=node.lon, lat=node.lat,
                                                         time=current_time)
            current_time += timedelta(seconds=5)
    gpx_txt += point_template.format(lon=first_node.lon, lat=first_node.lat,
                                     time=current_time)

    gpx_txt += footer

    with open(filepath, 'w') as f:
        f.write(gpx_txt)