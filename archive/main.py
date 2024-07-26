import sys
import requests
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import Settings
from DrissionPage.errors import ElementNotFoundError
from old_staff.CloudflareBypasser import CloudflareBypasser
import time
from DrissionPage.common import Settings

# 设置元素查找不到快速返回
Settings.raise_when_ele_not_found = True


def get_persons(raw_json):
    cleaned_data = []

    for person in raw_json.get("Items", []):
        cleaned_data.append(person)

    return cleaned_data


def init_browser(browser_path, proxy):
    co = ChromiumOptions().headless(False)
    co.set_browser_path(browser_path)
    co.set_proxy(proxy)
    arguments = [
        "-no-first-run",
        "-force-color-profile=srgb",
        "-metrics-recording-only",
        "-password-store=basic",
        "-use-mock-keychain",
        "-export-tagged-pdf",
        "-no-default-browser-check",
        "-disable-background-mode",
        "-enable-features=NetworkService,NetworkServiceInProcess,LoadCryptoTokenExtension,PermuteTLSExtensions",
        "-disable-features=FlashDeprecationWarning,EnablePasswordsAccountStorage",
        "-deny-permission-prompts",
        "-disable-gpu",
        "-accept-lang=en-US",
        "--blink-settings=imagesEnabled=true",
    ]
    

    for argument in arguments:
        co.set_argument(argument)
    page = ChromiumPage(addr_or_opts=co)
    return page


# def is_actors_without_overview(actor_name, url, headers):
#     url = f"{url}/{actor_name}"
#     response = requests.get(url, headers=headers)
#     overview = response.json().get("Overview")
#     if overview is None:
#         return True
#     else:
#         return False

def get_actor_detail(name,url,headers):
    url = f"{url}/{name}"
    response = requests.get(url,headers=headers)
    return response.json()


def search_name_in_xslist(page, name):
    tab0 = page.new_tab(url=f"https://xslist.org/search?lg=zh&query={name}")
    CloudflareBypasser(tab0).bypass()
    print("Enjoy the content!")
    # print(driver.html) # You can extract the content of the page.
    print("Title of the page: ", tab0.title)

    try:
        tab0.ele("No results found.")
        time.sleep(1)
        tab0.close()
        return None
    except ElementNotFoundError:
        link = tab0.ele(f"xpath:/html/body/ul/li/h3/a[contains(text(), '{name}')]").attr('href')
        tab1 = page.new_tab(url=link)
        CloudflareBypasser(tab1).bypass()
        detail = tab1.ele('xpath://*[@id="layout"]/div/p[1]').text
        cleaned_detail = detail.replace("\n", "<br>")
        time.sleep(1)
        tab0.close()
        tab1.close()
        return cleaned_detail


def post_overview(name, id, session):
    return


if __name__ == "__main__":
    # 手动填写部分
    host_url = "http://192.168.2.202:8096"
    token = "3287930a2ab9422eaa6e1dc4a5f23c24"
    userId = "99e7058d92d34f74bd369728f432a0e2"

    persons_url = f"{host_url}/Persons"

    headers = {
        "Authorization": f'MediaBrowser Token="{token}"',
        "Content-Type": "application/json",
    }

    persons_response = requests.get(persons_url, headers=headers)
    session = requests.Session()

    if persons_response.status_code == 200:
        json_response = persons_response.json()
        name_list = get_persons(json_response)
        print(f"仓库中总共搜索到{len(name_list)}名演员")
    else:
        print(f"Error: {persons_response.status_code}")
        sys.exit()

    need_search_overview_list = []
    # 获取没有个人信息的演员
    for actor in name_list:
        name = actor["Name"]
        id = actor["Id"]
        # print((name, id))
        actor_detail = get_actor_detail(name,persons_url,headers)        
        if not actor_detail.get("Overview"):
            need_search_overview_list.append(actor_detail)

    print(f"没有个人信息的演员：{need_search_overview_list}")

    print("启动浏览器")

    page = init_browser(r'/usr/bin/chromium','http://localhost:20171')

    need_search_overview_list = need_search_overview_list[310:340]

    need_to_post_list = []
    for person in need_search_overview_list:
        name = person["Name"]
        print(f"正在处理：{name}")
        info = search_name_in_xslist(page,name)
        if info is None:
            print(f"{name} 未找到信息")
        else:
            print(f"{name} \n{info}")

    # page.close()
