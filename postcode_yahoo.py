import csv
import copy
import sys

def request_yahooapi(pref, muni, town, apikey):
    import requests
    import json
    url = "https://map.yahooapis.jp/geocode/V1/geoCoder"
    params = {
        "query": pref + muni + town,
        "appid": apikey,
        "output": "json"
    }

    result_json = json.loads(requests.get(url, params=params).text)

    if result_json["ResultInfo"]["Count"] == 0:
        return []
    else:
        return extract_geo(pref, muni, town, result_json)

def extract_geo(pref, muni, town, *args):
    import json

    if len(args) == 1:
        results = args[0]

    geocodes = []
    for res in results["Feature"]:
        # 完全一致
        if (res["Name"] == pref + muni + town):
            info = []

            # 同じな構造でデータを作る
            info.append(pref)
            info.append(muni)
            info.append(town)
            info.append(pref)
            info.append(muni)
            info.append(town)
    
            # formatted_address
            info.append(res["Name"])
            # 経緯度
            coord = res["Geometry"]["Coordinates"].split(",")
            info.append(coord[0])
            info.append(coord[1])

            info.extend([0, 0, 0, 0, 0])
            geocodes.append(info)

    return geocodes

def main():
    if len(sys.argv) <= 1:
        print("Please input Yahoo Maps API key")
        sys.exit(1)

    # 郵便番号データをもとに、クレンジング対象だけ絞って、YOLP API を使う
    with open('./x-ken-100.csv', newline='') as source, open('./x-ken-100_geocode.csv', "w", newline='') as target:
        csv_reader = csv.reader(source, delimiter=',')
        # skip header
        next(csv_reader)
        csv_writer = csv.writer(target, delimiter=',',
            quotechar='"', quoting=csv.QUOTE_ALL)

        for row in csv_reader:
            geocodes = request_yahooapi(row[6], row[7], row[8], sys.argv[1])
            # 結果が0の場合はスキップする
            if len(geocodes) == 0:
                #target_row = copy.copy(row)
                #target_row.extend(["", "", ""])
                #csv_writer.writerow(target_row)
                continue

            for geocode in geocodes:
                target_row = copy.copy(row)
                target_row.extend(geocode)
                #print(target_row)

                csv_writer.writerow(target_row)


if __name__ == "__main__":
    main() 