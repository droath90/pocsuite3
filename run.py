#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
import time
import requests
import traceback
import tempfile
import shutil
import hashlib
import json
import re

requests.packages.urllib3.disable_warnings()


class GithubClient:

    def __init__(self, token):
        self.url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'{token}',
            'Connection': 'close',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.119 Safari/537.36'
        }
        self.limit = 0
        self.users_octocat()

    def connect(self, method, resource, data=None):
        '''访问api'''
        time.sleep(0.1)
        if method == 'GET':
            r = requests.get('{0}{1}'.format(
                self.url, resource), params=data, headers=self.headers, verify=False, allow_redirects=False)
        elif method == 'POST':
            r = requests.post('{0}{1}'.format(
                self.url, resource), data=data, headers=self.headers, verify=False, allow_redirects=False)
        r.encoding = r.apparent_encoding
        if 'X-RateLimit-Remaining' in r.headers.keys():
            self.limit = int(r.headers['X-RateLimit-Remaining'])
        try:
            return r.status_code, r.headers, r.json()
        except:
            return r.status_code, r.headers, r.content

    def search_code(self, keyword, page=1, per_page=10):
        '''搜索代码'''
        try:
            time.sleep(2)
            data = {'q': keyword, 'sort': 'indexed',
                    'order': 'desc', 'page': page, 'per_page': per_page}
            _, _, rs = self.connect("GET", '/search/code', data=data)
            return rs
        except:
            return {}

    def search_repositories(self, keyword, page=1, per_page=10):
        '''搜索项目'''
        try:
            time.sleep(2)
            data = {'q': keyword, 'sort': 'updated',
                    'order': 'desc', 'page': page, 'per_page': per_page}
            _, _, rs = self.connect("GET", '/search/repositories', data=data)
            return rs
        except:
            return {}

    def repos(self, author, repo):
        '''项目信息'''
        try:
            _, _, rs = self.connect("GET", f'/repos/{author}/{repo}')
            return rs
        except:
            return {}

    def repos_commits(self, author, repo):
        '''项目commit信息'''
        try:
            _, _, rs = self.connect(
                "GET", f'/repos/{author}/{repo}/commits')
            if isinstance(rs, dict):
                if rs.get('message', '') == 'Moved Permanently' and 'url' in rs:
                    _, _, rs1 = self.connect("GET", rs['url'][18:])
                    if isinstance(rs1, list):
                        return rs1
            elif isinstance(rs, list):
                return rs
        except:
            pass
        return []

    def repos_releases_latest(self, author, repo):
        '''项目最新release'''
        try:
            _, _, rs = self.connect(
                "GET", f'/repos/{author}/{repo}/releases/latest')
            return rs
        except:
            return {}

    def users_octocat(self):
        '''检查速率限制'''
        try:
            _, _, _ = self.connect(
                "GET", '/users/octocat')
        except:
            pass

def _md5(file):
    with open(file,'rb') as f:
        s = re.sub('\s+','',f.read().decode('utf8',errors='ignore'))
        return hashlib.md5(s.encode('utf8')).hexdigest()

def clone_repo(url):
    temp_dir = tempfile.TemporaryDirectory().name
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    os.chdir(temp_dir)
    os.system('git clone {}'.format(url))
    return os.path.join(temp_dir, url[19:].split('/', 1)[1])

def chr_len2(s):
    return int((len(s.encode('utf-8')) - len(s))/2 + len(s))


def parse(x, y):
    s = ''
    n = 0
    for i in re.sub('\s{2,}', '', x if x else ''):
        n += chr_len2(i)
        if n >= y:
            s += '<br>'
            n = 0
        s += i
    return s

if __name__ == '__main__':
    # 更新历史
    data = {}
    data_file = 'data.json'
    if os.path.exists(data_file):
        try:
            data = json.loads(open(data_file, 'r', encoding='utf8').read())
        except:
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
    else:
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    # 项目主页
    html_urls = []
    gc = GithubClient(os.getenv('GH_TOKEN'))
    # 搜索项目
    try:
        rs = gc.search_repositories("pocsuite3", page=1, per_page=100)
        html_urls += [item['html_url']
                      for item in rs.get('items', []) if item.get('html_url')]
    except:
        traceback.print_exc()
    # 本地路径
    root_path = os.path.dirname(os.path.abspath(__file__))

    # 搜索代码,获取项目主页
    try:
        rs = gc.search_code("pocsuite3.api+language:Python",
                            page=1, per_page=100)
        html_urls += [item['repository']['html_url']
                      for item in rs.get('items', []) if item.get('repository', {}).get('html_url')]
    except:
        traceback.print_exc()
    html_urls = set(html_urls)
    print(f'[+] html_urls: {len(html_urls)}')

    # 克隆项目代码并复制poc
    for url in html_urls:
        print(url)
        try:
            repo_path = clone_repo(url)
            if not os.path.exists(repo_path):
                continue
            for root, _, files in os.walk(repo_path):
                for file in files:
                    if not file.endswith('.py'):
                        continue
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf8') as f:
                            content = f.read()
                        if 'from pocsuite3.api' in content and 'register_poc' in content:
                            md5 = _md5(file_path)
                            if md5 not in data:
                                shutil.copyfile(file_path, os.path.join(
                                    root_path, 'poc', file))
                                data[md5] = {'name': file, 'from': url, "up_time": time.strftime(
                                    "%Y-%m-%d %H:%M:%S")}
                    except:
                        traceback.print_exc()
        except:
            traceback.print_exc()
    os.chdir(root_path)
    # 清理无效data
    md5s = []
    for file in os.listdir(os.path.join(root_path, 'poc')):
        if not file.endswith('.py') and file in ['run.py','__init__.py']:
            continue
        md5 = _md5(os.path.join(root_path, 'poc', file))
        md5s.append(md5)
    for md5 in [md5 for md5 in data.keys() if md5 not in md5s]:
        del data[md5]
    # 写入README.md
    readme_md = '## pocsuite3 (共{}个) 最近一次检查时间 {}\n'.format(
        len(os.listdir('poc')) - 1, time.strftime("%Y-%m-%d %H:%M:%S"))
    readme_md += '### 收集记录\n| 文件名称 | 收录时间 |\n| :----| :---- |\n'
    _data = sorted(data.values(), key=lambda x: x['up_time'], reverse=True)
    for item in _data:
        readme_md += '| [{}]({}) | {} |\n'.format(parse(item['name'], 50),
                                                  item['from'], item['up_time'])
    with open('README.md', 'w', encoding='utf8') as f:
        f.write(readme_md)
    # 写入data
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
