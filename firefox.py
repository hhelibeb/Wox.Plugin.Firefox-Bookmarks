from util import WoxEx, WoxAPI, load_module, Log

with load_module():
    import sqlite3
    import configparser
    import os
    import webbrowser
    import json
    import browser
    from os import path
    from typing import List

PROFILE_INI = "profiles.ini"
PLACES_SQLITE = 'places.sqlite'
CONFIG_JSON = 'config.json'

CONFIG_JSON_PATH = os.path.abspath(os.getcwd()) + '\\' + CONFIG_JSON

DEFAULT_CONFIG = {
    "db_path" : "",
    "enable_history" : False
}

DEFAULT_CONTEXT = [{
    'Title': f'Open config.json',
    'SubTitle': f'',
    'IcoPath': 'img\\config.ico',
    'JsonRPCAction': {
        'method': 'open_config',
        'parameters': [CONFIG_JSON_PATH]
    }
},{
    'Title': f'Enable/Disable history search',
    'SubTitle': f'',
    'IcoPath': 'img\\history.ico',
    'JsonRPCAction': {
        'method': 'switch_history',
        'parameters': []
    }
}]


class Main(WoxEx):

    def query(self, param):

        q = param.strip()
        if not q:
            return DEFAULT_CONTEXT

        db_path = self.get_config()['db_path']

        if not db_path:
            results = [{
                'Title': f'Cannot find {PLACES_SQLITE}',
                'SubTitle': f'Please set up the "db_path" in your {CONFIG_JSON} in the plugin dir',
                'IcoPath': 'img\\firefox.ico',
                'JsonRPCAction': {
                    'method': 'open_config',
                    'parameters': [CONFIG_JSON_PATH]
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

    def get_config(self) -> dict:

        if not path.exists(CONFIG_JSON_PATH):
            self.set_config({})

        try:
            with open(CONFIG_JSON_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (IOError, ValueError) as e:
            return

        return data

    def set_config(self, data: dict):
        if not data:
            db_path = self.search_db()
            data = DEFAULT_CONFIG
            data['db_path'] = db_path

        with open(CONFIG_JSON_PATH, 'w', encoding='utf-8') as outfile:
            json.dump(data, outfile, indent=4)

    def generate_sql(self, keyword: str) -> List[str]:

        results = []

        new_keyword = '%'.join(keyword.split())

        cond1 = f"'{new_keyword}%'"
        cond2 = f"'%{new_keyword}%'"

        enable_history = self.get_config()["enable_history"]

        if enable_history:
            results.append(f'''select case when b.title is not null then b.title
                                      else                               p.title
                                      end as title,
                                      visit_count,
                                      url, 
                                      frecency  
                               from moz_places               as p 
                               left outer join moz_bookmarks as b on b.fk = p.id 
                               where lower(b.title) like {cond2} or lower(p.title) like {cond2}
                                  or lower(p.url) like {cond2}
                               order by frecency desc 
                               limit 100'''
                           )
        else:
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
                    'method': 'open_config',
                    'parameters': [CONFIG_JSON_PATH]
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

    def open_config(self, dir=None):
        self.get_config()
        if dir:
            os.startfile(dir)

    def switch_history(self):
        data = self.get_config()
        if data["enable_history"]:
            data["enable_history"] = False
        else:
            data["enable_history"] = True
        self.set_config(data)

if __name__ == '__main__':
    Main()
