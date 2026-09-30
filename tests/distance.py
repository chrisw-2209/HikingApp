import math

def haversine(lat1,lon1,lat2,lon2):
    r = 6378*1000                           #radius of earth in m
    dlat = (lat1-lat2)*math.pi/180          #delta angle of latitude in radians
    dlon = (lon1-lon2)*math.pi/180          #delta angle of longitude in radians
    a = math.sin(dlat/2)**2 + math.cos(lat1*math.pi/180) * math.cos(lat2*math.pi/180) * math.sin(dlon/2)**2
    c = 2* math.atan2(math.sqrt(a),math.sqrt(1-a))
    d = r*c
    return d

latitude1 = 49.243824
longitude1 = -121.887340
latitude2 = 49.227648
longitude2 = -121.89631

distance = haversine(latitude1,longitude1,latitude2,longitude2)
print(distance)


#https://www.movable-type.co.uk/scripts/latlong.html?from=49.243824,-121.887340&to=49.227648,-121.89631
