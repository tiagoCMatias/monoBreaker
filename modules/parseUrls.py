import os
import re


def parse_url(directory_path):
    urls = []
    url_file = directory_path + '/url.txt'
    if os.path.isfile(url_file):  # True
        with open(url_file) as fp:
            line = fp.readline()
            cnt = 1
            while line:
                print("Line {}: {}".format(cnt, line.strip()))
                endpoint = re.findall("[^\t]+", line.replace("\n", ""))
                urls.append({
                    'name': endpoint[0],
                    'module': endpoint[1],
                    'functionCall': endpoint[2] if len(endpoint) > 2 else None
                })
                line = fp.readline()
                cnt += 1
        return urls
    else:
        raise Exception("No url file provided")