poly_coords = '''
-79.9120188, 43.2329629
-79.9089611, 43.2391066
-79.8992085, 43.2365741
-79.9017084, 43.2311650
-79.9119651, 43.2330176
'''

QUERY_TEMPLATE = '''
((way(poly:"{coords}")[highway~"(residential|secondary)"];
 /*way(id:231214779,231214774);*/
 ); 
 /*- way(id:187959876);*/
 );
out body;
>;
out skel qt;
'''


# https://www.keene.edu/campus/maps/tool/

if __name__ == '__main__':
    coords_list = []
    for c in poly_coords.split('\n'):
        if c == '':
            continue
        coords_list.append([float(x.strip()) for x in c.split(',')])

    coords_str = ''
    for c in coords_list:
        coords_str += '{} {} '.format(c[1], c[0])
    coords_str = coords_str[:-1]

    print(QUERY_TEMPLATE.format(coords=coords_str))


    pass