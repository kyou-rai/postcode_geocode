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
    # 英字の小文字で保存
    with open("/tmp/" + filename.lower(), "wb") as file_obj:
        blob.download_to_file(file_obj)
    return "/tmp/" + filename.lower()


def upload_file(filename, content_type):
    import codecs
    bucketname = os.environ.get('GOOGLE_STORAGE_BUCKET_TARGET')
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
    filename = data["name"]
    bucketname = data["bucket"]
    if not check_if_target(filename):
        print("トリガーとなっているファイルは処理対象ではない")
        return

    # save to /tmp from GCS
    src_file = save_to_tmp(bucketname, filename)
    filename = filename.lower()

    # 高層ビルあるデータとないデータで CSV を分ける
    if filename.startswith("add_") or filename.startswith("del_"):
        # 差分データを対象にして
        with open(src_file, newline='') as source, open("/tmp/build_" + filename, "w", newline='') as bulid, open("/tmp/nobuild_" + filename, "w", newline='') as nobuild:
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
    else:
        # 全件データを対象にして
        # step1: 高層ビルリストの作成(階を含む行により)
        bulidlist = []
        with open(src_file, newline='') as source, open("/tmp/buildlist_" + filename, "w", newline='') as bl:
            csv_reader = csv.reader(source, delimiter=',', quotechar='"')
            
            for row in csv_reader:
                buildname = re.sub(r"(　[０-９]+階)", "", row[8])
                if re.search(r"([０-９]+階)", row[8]) != None and buildname not in bulidlist:
                    bulidlist.append(buildname)

            lst = [[x] for x in bulidlist]
            csv_writer_buildlist = csv.writer(bl, delimiter=',',
                    quotechar='"', quoting=csv.QUOTE_ALL)
            csv_writer_buildlist.writerows(lst)

        # step2: 高層ビルリストにより、CSV を分ける
        with open(src_file, newline='') as source, open("/tmp/build_" + filename, "w", newline='') as bulid, open("/tmp/nobuild_" + filename, "w", newline='') as nobuild:
            csv_reader = csv.reader(source, delimiter=',', quotechar='"')
            csv_writer_build = csv.writer(bulid, delimiter=',',
                    quotechar='"', quoting=csv.QUOTE_ALL)
            csv_writer_nobuild = csv.writer(nobuild, delimiter=',',
                    quotechar='"', quoting=csv.QUOTE_ALL)
            
            for row in csv_reader:
                buildname = re.sub(r"(　[０-９]+階)", "", row[8])
                if buildname in bulidlist :
                    # 高層ビルあるデータ
                    csv_writer_build.writerow(row)
                else:
                    # 高層ビルないデータ
                    csv_writer_nobuild.writerow(row)

    # upload to GCS
    upload_file("/tmp/build_" + filename, "text/csv")
    upload_file("/tmp/nobuild_" + filename, "text/csv")
    if os.path.isfile("/tmp/buildlist_" + filename):
        upload_file("/tmp/buildlist_" + filename, "text/csv")



def main():
    data = {}
    data["bucket"] = os.environ.get('GOOGLE_STORAGE_BUCKET')
    data["name"] = "x-ken-all.csv"
    process_file(data, "")


if __name__ == "__main__":
    main()
