import winreg


FIREFOX = 'Firefox'
CHROME = "Chrome"
IE = 'IE'

PROGRAMS = {
    IE: "iexplore.exe",
    FIREFOX: "firefox.exe",
    CHROME: "chrome.exe"
}


def get_path(browser_name) -> str:

    reg_local_machine = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    reg_current_user = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
    key = f'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{PROGRAMS[browser_name]}'

    path = __get_default_value(reg_current_user, key)
    if path:
        return path

    return __get_default_value(reg_local_machine, key)


def __get_default_value(registry, key) -> str:
    result = ''
    try:
        result_key = winreg.OpenKey(registry, key)
        result = winreg.QueryValueEx(result_key, '')[0]
        result_key.Close()
    except FileNotFoundError:
        pass
    return result

