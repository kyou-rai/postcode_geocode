import csv
import copy

def call_geocodeapi(pref, muni, town):
    import googlemaps
    # adastria-datalake-develop の apikey
    gmaps = googlemaps.Client(key='')

    geocode_result = gmaps.geocode(address=pref + muni + town, region='jp', language='ja')

    return extract_geo(pref, muni, town, geocode_result)

def extract_administrative(info, res, key):
    # 都道府県
    if sum(1 for x in res["address_components"] if "administrative_area_level_1" in x["types"]) == 0:
        info.append("")
    else:
        info.append(next(x[key] for x in res["address_components"] if "administrative_area_level_1" in x["types"]))
    # 市区町村
    if sum(1 for x in res["address_components"] if "locality" in x["types"]) == 0:
        info.append("")
    else:
        # 和歌山県/伊都郡かつらぎ町 福岡県/糟屋郡篠栗町
        if sum(1 for x in res["address_components"] if "administrative_area_level_2" in x["types"]) != 0:
            info.append(next(x[key] for x in res["address_components"] if "administrative_area_level_2" in x["types"]) + 
                        next(x[key] for x in res["address_components"] if "locality" in x["types"]))
        # 鳥取県/鳥取市/瀬田蔵 福岡県/福岡市中央区/荒戸
        else:
            if sum(1 for x in res["address_components"] if "sublocality_level_1" in x["types"]) == 0:
                info.append(next(x[key] for x in res["address_components"] if "locality" in x["types"]))
            else:
                info.append(next(x[key] for x in res["address_components"] if "locality" in x["types"]) + 
                            next(x[key] for x in res["address_components"] if "sublocality_level_1" in x["types"]))
    # 町域名
    if sum(1 for x in res["address_components"] if "sublocality_level_2" in x["types"]) == 0:
        info.append("")
    else:
        info.append(next(x[key] for x in res["address_components"] if "sublocality_level_2" in x["types"]))
    
    return info

def extract_geo(pref, muni, town, *args):
    import json

    if len(args) == 1:
        results = args[0]
    else:
        f = open("./result.json", 'r')
        results = (json.load(f))['results']

    geocodes = []
    for res in results:
        info = []

        info = extract_administrative(info, res, "long_name")
        #print(info)
        info = extract_administrative(info, res, "short_name")
        #print(info)

        # formatted_address
        info.append(res['formatted_address'])
        # 経度
        info.append(res['geometry']['location']['lng'])
        # 緯度
        info.append(res['geometry']['location']['lat'])
        # クレンジング対象と判断する条件
        if pref != info[0] or muni != info[1] or town != info[2]:
            info.append(1)
        else:
            info.append(0)
        #print(info)
        geocodes.append(info)
    
    return geocodes

def main():
    #print(extract_geo("京都府", "京丹後市", "久美浜町島"))

    with open('./x-ken-100.csv', newline='') as source, open('./x-ken-100_geocode.csv', "w", newline='') as target:
        csv_reader = csv.reader(source, delimiter=',', quotechar='"')
        csv_writer = csv.writer(target, delimiter=',',
            quotechar='"', quoting=csv.QUOTE_ALL)

        for row in csv_reader:
            geocodes = call_geocodeapi(row[6], row[7], row[8])
            morethan_one = False
            if len(geocodes) > 1:
                morethan_one = True

            for geocode in geocodes:
                target_row = copy.copy(row)
                target_row.extend(geocode)
                target_row.append("1" if morethan_one else "0")
                #print(target_row)

                csv_writer.writerow(target_row)


if __name__ == "__main__":
    main()