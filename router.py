

mountview_query = '''((way[highway~"^(residential)$"]
  (43.23407,-79.92975,43.24457,-79.9156);
- way(id:35293308,
                 441472728,
                 441472731,
                 465328794,
      100763472,
      184336259,
      184336260,
      35292044,
      35291798,
      35295208,
      35292558,
     27726852);

                 );

way(id:100763473);
                 );

out body;
>;
out skel qt;'''
mountview_starting_node = 210842205

gilbert_query = '''((way(poly:"43.23292 -79.91145 43.22624 -79.91478 43.22391 -79.905254 43.2311 -79.90197")[highway~"(residential|secondary)"];
 way(377392508);); 
 );
out body;
>;
out skel qt;'''

gilbert_start = 4556442359

iroquois_height_query = '''((way[highway~"(path|footway)"](43.2354, -79.9481, 43.2458, -79.9342);
-
 way(id:50525780);
);
way(id:281458431);
);
out body;
>;
out skel qt;'''
iroquois_starting_node = 4959344315

dvca_query = '''((way[highway~"(path|footway)"](43.2166, -80.0342,43.2571, -79.9454);

way(id:148998895,178208755,23842147,194434747,179780233,248315310); 

);
 - way(id:194434747);
);
out body;
>;
out skel qt;'''
dvca_starting_node = 244444276

sir_allen_query = '''((way[highway~"(residential)"](43.2262, -79.93,43.2335, -79.9142);

 - way(id:318893169,35296504, 35288783,35300998,35290726,669410986,100763937,100763929,100763930, 100763933,100763931,100763928,100763935,100763932,35294317,35294247,35298278, 487972246,35298871,262613530,35298648,35291752,35296616
);

);
 way(id:28284428,100763855,448424152,262613551,459926739);
 );

out body;
>;
out skel qt;
'''
sir_all_starting_point = 35195047

west_query = '''((way[highway~"(residential|secondary)"](43.2308,  -79.9167,43.24585, -79.8989);

 - way(id:27828859,465327308,20879447,262613551,459926739,28284409,435213738,511322002,511322001,54740356,435213737,435213731,435213735,465327305,299675993,27925282,54738917
);

);
 way(id:20252436,20252469,438189804,299675995,465664297);
 );

out body;
>;
out skel qt;'''
west_starting_point = 224348259

gurnett_query = """way(poly:"43.22112 -79.92948 43.21873 -79.91867 43.22583 -79.91551 43.22900 -79.92989")[highway~"(residential|secondary)"];

out body;
>;
out skel qt;"""
gurnett_start = 299182061

west1_query = """(way(poly:"43.23570 -79.91603 43.24570 -79.91225 43.24495 -79.90701 43.23510 -79.91139")[highway~"(residential|secondary)"];

- way(id:465328794);
 );
out body;
>;
out skel qt;"""
west1_start = 224348259

mount2_query = '''((way(poly:"43.23448 -79.91603 43.24192 -79.91444 43.24261 -79.91693 43.24123 -79.92495 43.23792 -79.92615 43.23685 -79.92397 43.23445 -79.92319")[highway~"(residential|secondary)"];
 way(100763473););
- way(id:465327309,27726852,35292044,35291798,35295208,35292558,100763558,100763548);
 );
out body;
>;
out skel qt;
'''

mount2_start = 1164614493

falkirk_west_query = '''((way(poly:"43.2195 -79.92386 43.21797 -79.91815 43.20962 -79.92193 43.211 -79.92772")[highway~"(residential|secondary)"];
/* way(377392508);*/); 
 - way(id:35299369,35295612,100755563);
 );
out body;
>;
out skel qt;'''

falkirk_west_start = 2918852312

from router_utils import get_cpp_circuit, draw_circuit, generate_gpx

def get_num_turns(circuit_df):
    circuit_df['turn'] = circuit_df['way'] != circuit_df['way'].shift(1).fillna(circuit_df['way'].iloc[-1])
    circuit_df['u-turn'] = circuit_df['way_segment'] == circuit_df['way_segment'].shift(1)

    num_turns = len(circuit_df[circuit_df['turn']])
    num_u_turns = len(circuit_df[circuit_df['u-turn']])
    # print('num turns:', num_turns)
    # print('num u-turns:', num_u_turns)
    return num_turns, num_u_turns

def permute(circuit_df, row1, row2):
    reverse_circuit_df = circuit_df[row1:row2]
    reverse_circuit_df = reverse_circuit_df.rename(columns={'node': 'node2', 'node2': 'node'})
    reverse_circuit_df = reverse_circuit_df.sort_index(ascending=False)
    import pandas as pd
    final = pd.concat([circuit_df[:row1], reverse_circuit_df, circuit_df[row2:]])
    final = final.reset_index(drop=True)
    num_turns_orig, num_u_turns_orig = get_num_turns(circuit_df)

    num_turns_final, num_u_turns_final = get_num_turns(final)
    assert len(circuit_df) == len(final)

    if num_u_turns_final < num_u_turns_orig:
        print('u turn improvement {} -> {}'.format(num_u_turns_orig, num_u_turns_final))
        return final
    if num_u_turns_final == num_u_turns_orig and num_turns_final < num_turns_orig:
        print('turn improvement {} -> {}'.format(num_turns_orig, num_turns_final))
        return final
    return None


def get_permutations(circuit_df):
    permutations = {}
    for i in range(len(circuit_df)):
        perms  = circuit_df[(circuit_df.iloc[i]['node'] == circuit_df['node2'])  &(circuit_df.index > (i+1))].index


        if len(perms):
            # print(i, circuit_df.iloc[i]['node'], len(perms),
            #       circuit_df.groupby('node').count().xs(circuit_df.iloc[i]['node'])['augmented'])

            permutations[i] = perms.values.tolist()
    return permutations


def optimize_circuit(circuit_df):
    improving = True
    restart = None
    while improving or restart:
        print('restarting')
        restart = False
        perms = get_permutations(circuit_df)
        for k, vs in perms.items():
            if restart:
                break
            for v in vs:
                if restart:
                    break
                new_circuit = permute(circuit_df, k, v)
                if new_circuit is not None:
                    circuit_df = new_circuit
                    print('found new circuit')
                    restart = True

        improving = False
    return circuit_df

def run(query, start, name):
    circuit_df, circuit, way_segments = get_cpp_circuit(query, start )
    print(get_num_turns(circuit_df))

    generate_gpx(circuit_df, way_segments, r'C:\tmp\{}_pre.gpx'.format(name))
    draw_circuit(circuit_df, r'C:\tmp\{}_pre.jpg'.format(name))

    circuit_df = optimize_circuit(circuit_df)
    print(get_num_turns(circuit_df))

    draw_circuit(circuit_df, r'C:\tmp\{}_opt.jpg'.format(name))
    generate_gpx(circuit_df, way_segments, r'C:\tmp\{}_opt.gpx'.format(name))



if __name__ == '__main__':
    # circuit_df, circuit, way_segments = get_cpp_circuit(gurnett_query, gurnett_start)
    # print(get_num_turns(circuit_df))
    # circuit_df = optimize_circuit(circuit_df)
    # print(get_num_turns(circuit_df))
    #
    # draw_circuit(circuit_df, r'C:\tmp\gurnett_opt.jpg')
    # generate_gpx(circuit_df, way_segments, r'C:\tmp\gurnett_opt.gpx')

    # west_remove_nodes = {310609538, 310232798,310232797, 310232777, 310232796, 310232730 , 293766081,
    #                      310232778, 310232781, 310232782, 310232788, 310232736, # Elmwood
    #
    #     310247352, 310232736, 293765658,293764471,306532329,306532316,3807668803,306532317,
    #                      3807668804,293765659,3807668807, 310247540, 293765904 }
    # circuit_df, circuit, way_segments = get_cpp_circuit(west1_query, west1_start, west_remove_nodes)
    # print(get_num_turns(circuit_df))
    #
    # generate_gpx(circuit_df, way_segments, r'C:\tmp\west1_pre.gpx')
    #
    # circuit_df = optimize_circuit(circuit_df)
    # print(get_num_turns(circuit_df))
    #
    # draw_circuit(circuit_df, r'C:\tmp\west1_opt.jpg')
    # generate_gpx(circuit_df, way_segments, r'C:\tmp\west1_opt.gpx')
    #
    #
    # circuit_df, circuit, way_segments = get_cpp_circuit(gilbert_query, gilbert_start )
    # print(get_num_turns(circuit_df))
    #
    # generate_gpx(circuit_df, way_segments, r'C:\tmp\gilbert_pre.gpx')
    # draw_circuit(circuit_df, r'C:\tmp\gilbert_pre.jpg')
    #
    # circuit_df = optimize_circuit(circuit_df)
    # print(get_num_turns(circuit_df))
    #
    # draw_circuit(circuit_df, r'C:\tmp\gilbert_opt.jpg')
    # generate_gpx(circuit_df, way_segments, r'C:\tmp\gilbert_opt.gpx')
    #

    run(falkirk_west_query, falkirk_west_start, 'falkirk_west')