import csv
import copy
import re
import jaconv
import sys
from kanjize import kanji2int

fullwidth_pattern = r"[０-９]+"
chinese_num_pattern = r"[一二三四五六七八九十]+"
kogaki_pattern = r"[ぁぃぅぇぉっゃゅょゎゕゖァィゥェォヵㇰヶㇱㇲッㇳㇴㇵㇶㇷㇸㇹㇺャュョㇻㇼㇽㇾㇿヮ]+"
oaza_pattern = r"(^大字|^字|^小字)"
kogaki2ogaki_table = str.maketrans({
    'ぁ': 'あ',
    'ぃ': 'い',
    'ぅ': 'う',
    'ぇ': 'え',
    'ぉ': 'お',
    'っ': 'つ',
    'ゃ': 'や',
    'ゅ': 'ゆ',
    'ょ': 'よ',
    'ゎ': 'わ',
    'ゕ': 'か',
    'ゖ': 'け',
    'ァ': 'ア',
    'ィ': 'イ',
    'ゥ': 'ウ',
    'ェ': 'エ',
    'ォ': 'オ',
    'ヵ': 'カ',
    'ㇰ': 'ク',
    'ヶ': 'ケ',
    'ㇱ': 'シ',
    'ㇲ': 'ス',
    'ッ': 'ツ',
    'ㇳ': 'ト',
    'ㇴ': 'ヌ',
    'ㇵ': 'ハ',
    'ㇶ': 'ヒ',
    'ㇷ': 'フ',
    'ㇸ': 'ヘ',
    'ㇹ': 'ホ',
    'ㇺ': 'ム',
    'ャ': 'ヤ',
    'ュ': 'ユ',
    'ョ': 'ヨ',
    'ㇻ': 'ラ',
    'ㇼ': 'リ',
    'ㇽ': 'ル',
    'ㇾ': 'レ',
    'ㇿ': 'ロ',
    'ヮ': 'ワ'
})


def call_geocodeapi(pref, muni, town, apikey):
    import googlemaps
    # adastria-datalake-develop の apikey
    gmaps = googlemaps.Client(key=apikey)

    geocode_result = gmaps.geocode(address=pref + muni + town, region='jp', language='ja')

    return extract_geo(pref, muni, town, geocode_result)

def extract_administrative(info, res, key):
    # 都道府県
    api_pref = ''
    if sum(1 for x in res["address_components"] if "administrative_area_level_1" in x["types"]) != 0:
        api_pref = next(x[key] for x in res["address_components"] if "administrative_area_level_1" in x["types"])
    info.append(api_pref)
    # 市区町村
    api_muni = ''
    if sum(1 for x in res["address_components"] if "administrative_area_level_2" in x["types"]) != 0:
        api_muni += next(x[key] for x in res["address_components"] if "administrative_area_level_2" in x["types"])
    if sum(1 for x in res["address_components"] if "locality" in x["types"]) != 0:
        api_muni += next(x[key] for x in res["address_components"] if "locality" in x["types"])
    if sum(1 for x in res["address_components"] if "sublocality_level_1" in x["types"]) != 0:
        api_muni += next(x[key] for x in res["address_components"] if "sublocality_level_1" in x["types"])
    info.append(api_muni)
    # 町域名
    api_town = ''
    if sum(1 for x in res["address_components"] if "sublocality_level_2" in x["types"]) != 0:
         api_town += next(x[key] for x in res["address_components"] if "sublocality_level_2" in x["types"])
    if sum(1 for x in res["address_components"] if "sublocality_level_3" in x["types"]) != 0:
         api_town += next(x[key] for x in res["address_components"] if "sublocality_level_3" in x["types"])
    info.append(api_town)
    
    return info

def compare_town_ch(with_ch, without_ch):
    # 漢数字リスト
    ch_num_list = re.findall(chinese_num_pattern, with_ch)
    # 全角数字リスト
    fullwidth_num_list = re.findall(fullwidth_pattern, without_ch)
    if len(ch_num_list) != len(fullwidth_num_list):
        print("length")
        return False
    for ch_num, fullwidth_num in zip(ch_num_list, fullwidth_num_list):
        # 漢数字 -> 半角数字 -> 全角数字という順で変換してから、比較する
        if jaconv.han2zen(str(kanji2int(ch_num)), digit=True) != fullwidth_num:
            print("ch_num")
            return False
    # 漢数字と全角数字を取り除いて、比較する
    if re.sub(chinese_num_pattern, "", with_ch) != re.sub(fullwidth_pattern, "", without_ch):
        print("other")
        return False
    
    return True

def compare(pref, muni, town, api_pref, api_muni, api_town, info):
    # クレンジング必要
    need_cleaning = 0
    # 町域名 部分一致
    is_part = 0
    # 町域名 全角数字ある

    have_fullwidth_digit = 0
    # 町域名 小書きある
    have_kogaki = 0

    if pref != api_pref:
        need_cleaning = 1
    if muni != api_muni:
        need_cleaning = 1
    if town == api_town:
        info.extend([need_cleaning, is_part, have_fullwidth_digit, have_kogaki])
        return info
    else :
        # API 結果の町域名は先頭から「大字」、「字」と「小字」を取り除く
        api_town = re.sub(oaza_pattern, "", api_town)
        if town == api_town:
            info.extend([need_cleaning, is_part, have_fullwidth_digit, have_kogaki])
            return info
        # 町域名 部分一致
        # 数字と漢数字の違い + 部分一致というパターンは未実装
        if town in api_town or api_town in town:
            need_cleaning = 1
            is_part = 1
        # 町域名 数字と漢数字の比較
        if re.search(fullwidth_pattern, town) != None or re.search(fullwidth_pattern, api_town) != None:
            # 全角数字が含まれないほうは、漢数字を全角数字へ変換してから、比較する
            # 漢数字とそのほか部分を分けて、比較する
            town_with_ch = town if re.search(fullwidth_pattern, town) == None else api_town
            town_without_ch = town if re.search(fullwidth_pattern, town) != None else api_town
            if not compare_town_ch(town_with_ch, town_without_ch):
                need_cleaning = 1
                have_fullwidth_digit = 1
                info.extend([need_cleaning, is_part, have_fullwidth_digit, have_kogaki])
                return info
        
        # 町域名 小書きと大書きの比較
        if re.search(kogaki_pattern, town) != None or re.search(kogaki_pattern, api_town) != None:
            if (town.translate(kogaki2ogaki_table) != api_town.translate(kogaki2ogaki_table)):
                need_cleaning = 1
                have_kogaki = 1
                info.extend([need_cleaning, is_part, have_fullwidth_digit, have_kogaki])
                return info
        
    info.extend([need_cleaning, is_part, have_fullwidth_digit, have_kogaki])
    return info

def extract_geo(pref, muni, town, *args):
    import json

    if len(args) == 1:
        results = args[0]
    else:
        f = open("./7.json", 'r')
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
        compare(pref, muni, town, info[0], info[1], info[2], info)
        #print(info)
        geocodes.append(info)
    
    return geocodes

def main():
    if len(sys.argv) <= 1:
        print("Please input Google Maps API key")
        sys.exit(1)

    print(extract_geo("北海道","帯広市","西十一条北"))

#    with open('./x-ken-100.csv', newline='') as source, open('./x-ken-100_geocode.csv', "w", newline='') as target:
#        csv_reader = csv.reader(source, delimiter=',', quotechar='"')
#        csv_writer = csv.writer(target, delimiter=',',
#            quotechar='"', quoting=csv.QUOTE_ALL)
#
#        for row in csv_reader:
#            geocodes = call_geocodeapi(row[6], row[7], row[8], sys.argv[1])
#            morethan_one = False
#            if len(geocodes) > 1:
#                morethan_one = True
#
#            for geocode in geocodes:
#                target_row = copy.copy(row)
#                target_row.extend(geocode)
#                target_row.append("1" if morethan_one else "0")
#                #print(target_row)
#
#                csv_writer.writerow(target_row)


if __name__ == "__main__":
    main()