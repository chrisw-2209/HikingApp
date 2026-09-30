import math

def bearing(lat1,lon1,lat2,lon2):       #lat1,lon1 = mountain
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    d_lon = math.radians(lon2-lon1)
    x = math.sin(d_lon) * math.cos(lat2_rad)
    y = (math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(d_lon))
    initial_bearing_rad = math.atan2(x, y)
    initial_bearing_deg = math.degrees(initial_bearing_rad)
    compass_bearing = (initial_bearing_deg + 360) % 360
    directions = [
        "N", "NNE", "NE", "ENE", 
        "E", "ESE", "SE", "SSE", 
        "S", "SSW", "SW", "WSW", 
        "W", "WNW", "NW", "NNW"
    ]
    index = int((compass_bearing + 11.25) % 360 / 22.5)
    return directions[index]

latitude1 = 0
longitude1 = 0
latitude2 = 10
longitude2 = 10
angle = bearing(latitude1,longitude1,latitude2,longitude2)
print(angle)