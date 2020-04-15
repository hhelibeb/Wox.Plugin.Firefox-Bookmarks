from util import WoxEx, WoxAPI, load_module, Log

with load_module():
    import sqlite3
    import configparser
    import winreg
    import os
    import webbrowser
    import json
    import browser
    from os import path
    from typing import List

PROFILE_INI = "profiles.ini"
PLACES_SQLITE = 'places.sqlite'
CONFIG_JSON = 'config.json'


class Main(WoxEx):

    def query(self, param):

        q = param.strip()
        if not q:
            return

        db_path = self.get_db()

        if not db_path:
            results = [{
                'Title': f'Cannot find {PLACES_SQLITE}',
                'SubTitle': f'Please set up the "db_path" in your {CONFIG_JSON} in the plugin dir',
                'IcoPath': 'img\\firefox.ico',
                'JsonRPCAction': {
                    'method': 'open_dir',
                    'parameters': [os.path.abspath(os.getcwd())]
                }
            }]
            return results

        results = self.get_results(db_path=db_path, sql=self.generate_sql(q))
        return results

    def context_menu(self, data):

        results = []
        for browser_name in browser.PROGRAMS:
            if browser.get_path(browser_name):
                results.append({
                    "Title": f"Open With {browser_name}",
                    "SubTitle": str(data),
                    "IcoPath": f"img\\{browser_name}.ico",
                    'JsonRPCAction': {
                        'method': 'open_url',
                        'parameters': [str(data), browser_name]
                    }
                })
        return results

    def get_db(self) -> str:

        dir = os.path.abspath(os.getcwd())
        config_file = dir + '\\' + CONFIG_JSON

        db_path = ''

        if not path.exists(config_file):
            db_path = self.search_db()
            data = dict()
            data['db_path'] = db_path
            with open(config_file, 'w', encoding='utf-8') as outfile:
                json.dump(data, outfile)
        else:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data:
                        db_path = data['db_path']
            except (IOError, ValueError) as e:
                return

        return db_path

    def generate_sql(self, keyword: str) -> List[str]:

        results = []

        cond1 = f"'{keyword}%'"
        cond2 = f"'%{keyword}%'"

        results.append(f'''select b.title, visit_count, url, frecency, b.guid
                              from moz_bookmarks as b
                              join moz_places    as p on b.fk = p.id
                              where lower(b.title) like {cond1}
                              order by frecency desc '''
                       )
        results.append(f'''select b.title, visit_count, url, frecency, b.guid  
                             from moz_bookmarks as b 
                             join moz_places    as p on b.fk = p.id
                             where lower(b.title) like {cond2} 
                               and lower(b.title) not like {cond1} 
                             order by frecency desc '''
                       )
        results.append(f'''select b.title, visit_count, url, frecency, b.guid 
                             from moz_bookmarks as b 
                             join moz_places    as p on b.fk = p.id
                             where lower(p.url) like {cond2}  
                             order by frecency desc '''
                       ) 

        return results

    def search_db(self) -> str:

        results = []

        for root, dirs, files in os.walk(os.environ['APPDATA']):
            if PROFILE_INI in files:
                temp = dict()
                temp['path'] = path.join(root, PROFILE_INI)
                temp['root'] = root
                temp['mtime'] = os.stat(temp['path']).st_mtime
                results += [temp]

        results.sort(key=lambda k: k['mtime'], reverse=True)

        profiles_ini_path = ''
        if results:
            profiles_ini_path = results[0]
        else:
            return

        config = configparser.ConfigParser()
        config.read(profiles_ini_path['path'], encoding='utf-8')
        install = config.sections()[0]
        profile_path = config[install]['Default']

        if not profile_path:
            return

        if os.path.isabs(profile_path):
            db_path = profile_path + '\\' + PLACES_SQLITE
        else:
            os.chdir(profiles_ini_path['root'])
            db_path = os.path.abspath(profile_path) + '\\' + PLACES_SQLITE

        return db_path

    def get_results(self, db_path: str, sql: List[str]) -> List[dict]:

        results = []

        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            for statement in sql:
                for item in c.execute(statement):
                    result = dict()
                    title = item[0]
                    url = item[2]
                    result = {
                        'Title': title,
                        'SubTitle': url,
                        'IcoPath': 'img\\Firefox.ico',
                        "ContextData": url,
                        'JsonRPCAction': {
                            'method': 'open_url',
                            'parameters': [url]
                        }
                    }
                    results += [result]
            conn.close()
        except sqlite3.OperationalError:
            results = [{
                'Title': f'Cannot get data from "{db_path}"',
                'SubTitle': f'Check the "db_path" configuration in your {CONFIG_JSON} in the plugin dir',
                'IcoPath': 'img\\firefox.ico',
                'JsonRPCAction': {
                    'method': 'open_dir',
                    'parameters': [os.path.abspath(os.getcwd())]
                }
            }]
        return results

    def open_url(self, url=None, browser_name=None):
        if not browser_name:
            webbrowser.open(url)
        else:
            browser_path = browser.get_path(browser_name)
            webbrowser.register(browser_name, None, webbrowser.BackgroundBrowser(browser_path))
            webbrowser.get(browser_name).open_new_tab(url)

    def open_dir(self, dir=None):
        if dir:
            os.startfile(dir)


if __name__ == '__main__':
    Main()
