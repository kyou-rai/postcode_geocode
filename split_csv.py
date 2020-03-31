from google.cloud import storage
from dateutil.relativedelta import relativedelta
import datetime
import os
import csv
import re
import six

storage_client = storage.Client()


def check_if_target(filename):
    last_month = datetime.datetime.now() + relativedelta(months=-1)
    dl_filename = last_month.strftime("%y%m")

    # x-ken-all.csv が全件のデータ、ADD_ が差分の追加データ、DEL_が差分の削除データ
    target_files = ["x-ken-all.csv"]
    target_files.append("ADD_{0}.CSV".format(dl_filename))
    target_files.append("DEL_{0}.CSV".format(dl_filename))
    
    lower_list = {v.lower(): v for v in target_files}

    if filename.lower() in lower_list:
        return True
    else:
        return False


def save_to_tmp(bucketname, filename):
    bucket = storage_client.get_bucket(bucketname)
    blob = bucket.blob(filename)
    with open("/tmp/" + filename, "wb") as file_obj:
        blob.download_to_file(file_obj)
    return "/tmp/" + filename


def upload_file(filename, content_type, bucketname):
    import codecs
    bucket = storage_client.bucket(bucketname)
    blob = bucket.blob(os.path.basename(filename))

    with open(filename, newline='') as file:
        blob.upload_from_string(
            file.read(),
            content_type=content_type)

    url = blob.public_url

    if isinstance(url, six.binary_type):
        url = url.decode('utf-8')

    return url

def process_file(data, context):
    if not check_if_target(data['name']):
        print("トリガーとなっているファイルは処理対象ではない")
        return

    # save to /tmp from GCS
    src_file = save_to_tmp(data["bucket"], data["name"])

    # 高層ビルあるデータとないデータで CSV を分ける
    with open(src_file, newline='') as source, open("/tmp/build" + data["name"], "w", newline='') as bulid, open("/tmp/nobuild" + data["name"], "w", newline='') as nobuild:
        csv_reader = csv.reader(source, delimiter=',', quotechar='"')
        csv_writer_build = csv.writer(bulid, delimiter=',',
                quotechar='"', quoting=csv.QUOTE_ALL)
        csv_writer_nobuild = csv.writer(nobuild, delimiter=',',
                quotechar='"', quoting=csv.QUOTE_ALL)
        
        for row in csv_reader:
            if re.search(r"([０-９]+階)|(階層不明)", row[8]) != None:
                # 高層ビルあるデータ
                csv_writer_build.writerow(row)
            else:
                # 高層ビルないデータ
                csv_writer_nobuild.writerow(row)

    # upload to GCS
    upload_file("/tmp/build" + data["name"], "text/csv", data["bucket"])
    upload_file("/tmp/nobuild" + data["name"], "text/csv", data["bucket"])


def main():
    data = {}
    data["bucket"] = os.environ.get('GOOGLE_STORAGE_BUCKET')
    data["name"] = "ADD_2002.CSV"
    process_file(data, "")


if __name__ == "__main__":
    main()
