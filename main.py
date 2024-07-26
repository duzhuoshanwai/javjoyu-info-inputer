"""
version: alpha-1
赞美GPT,让prompt engineer也能写代码
"""
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import re
import time

# 获取所有演员信息的字典
# 返回list中包含演员信息的dict
def get_actors_dict(session, jellyfin_host, userId):
    try:
        response = session.get(f'{jellyfin_host}/Persons?userId={userId}')
        response.raise_for_status()
        full_json = response.json()
        cleaned_data = [person for person in full_json.get("Items", [])]
        list = []
        for person in cleaned_data:
            data = session.get(f'{jellyfin_host}/Persons/{person["Name"]}?userId={userId}').json()
            if data.get("ChildCount", 0) > 0:
                list.append(data)
        return list
    except requests.RequestException as e:
        print(f"获取演员列表时出错: {e}")
        return []
    except ValueError as e:
        print(f"解析JSON时出错: {e}")
        return []

# 检查演员的Overview是否为空
def is_blank_Overview(actor):
    # Get the value of 'Overview' if it exists, otherwise use an empty string
    overview = actor.get("Overview", "")
    # Return True if 'Overview' does not exist or is empty; otherwise, return False
    return not overview.strip()

# 从 av2ch 获取演员详细信息
def get_av2ch_data(name, session):
    av2ch_url = "https://av2ch.net/avsearch/avs.php"
    data = {
        "keyword": name,
        "gte_height": "min",
        "lte_height": "max",
        "gte_bust": "min",
        "lte_bust": "max",
        "gte_waist": "min",
        "lte_waist": "max",
        "gte_hip": "min",
        "lte_hip": "max",
        "gte_cup": "min",
        "lte_cup": "max",
        "gte_age": "min",
        "lte_age": "max",
        "genre_01": "",
        "genre_02": "",
    }

    try:
        response = session.post(av2ch_url, data=data)
        response.raise_for_status()
        time.sleep(1)
        soup = BeautifulSoup(response.content, "html.parser")
        div_list = soup.find_all("div", class_="box_actress")
        
        for div in div_list:
            h2 = div.find("h2", class_="h2_actress")
            if h2 and h2.get_text(strip=True) == name:
                p_element = div.find("div", class_="text_actress").find("p")
                if p_element:
                    text = p_element.get_text(separator=" ", strip=True)
                    return text
    except requests.RequestException as e:
        print(f"请求失败: {e}")
    except Exception as e:
        print(f"解析或提取数据时出错: {e}")
    return None

# 清理详细数据
def clean_detail_data(text):
    if text is None:
        return None

    patterns = {
        "生日": r"(\d{4}年\d{1,2}月\d{1,2}日)生まれ",
        "身高": r"身長 (\d{1,3}) cm",
        "胸围": r"Ｂ (\d{1,3}) cm",
        "腰围": r"Ｗ (\d{1,3}) cm",
        "臀围": r"Ｈ (\d{1,3}) cm",
        "Bra": r"ブラ ([A-Z]) カップ",
    }

    count = 0
    result = {}

    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        result[key] = match.group(1) if match else "?"
        if not match:
            count += 1

    result_str = f"""<br>
生日：{result['生日']}<br>
身高：{result['身高']}<br>
胸围：{result['胸围']}
腰围：{result['腰围']}
臀围：{result['臀围']}<br>
胸罩杯：{result['Bra']}"""

    if count != 0:
        result_str += '''<br>有缺少'''

    return result_str

# 提交数据到Jellyfin
def post_data(userId, session, actor_id, data_dict):
    try:
        response = session.post(f'{jellyfin_host}/Items/{actor_id}?userId={userId}', json=data_dict)
        response.raise_for_status()
        return response.status_code
    except requests.RequestException as e:
        print(f"提交数据时出错: {e}")
        return None

if __name__ == "__main__":
    print("适配jellyfin版本: 10.9.8")
    #这部分修改
    jellyfin_apiKey = "3287a30a2cb9422eaa6e1dc9a5f23c24"
    jellyfin_host = "http://192.168.2.202:8096"
    jellyfin_userId = "99e7058d98d34f74cd369738f432a0e2"

    jellyfin_headers = {
        'accept': '*/*',
        "Authorization": f'MediaBrowser Token="{jellyfin_apiKey}"',
        "Content-Type": "application/json",
    }

    jellyfin_session = requests.Session()
    jellyfin_session.headers.update(jellyfin_headers)

    # 获取所有演员信息
    full_actor_json_list = get_actors_dict(jellyfin_session, jellyfin_host, jellyfin_userId)
    print(f'总共找到Persons: {len(full_actor_json_list)}')

    # 找出有作品并缺少 Overview 的演员
    blank_Overview_list = []
    for actor in full_actor_json_list:
        print(actor)
        if is_blank_Overview(actor):
            blank_Overview_list.append(actor)

    print(f'缺少个人信息的有: {len(blank_Overview_list)}')

    # 设置爬虫的 User Agent 和 Headers
    scraper_ua = UserAgent(browsers=["edge", "chrome"], os="windows")
    scraper_headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://av2ch.net",
        "referer": "https://av2ch.net/avsearch/",
        "user-agent": scraper_ua.random,
    }

    scraper_session = requests.Session()
    scraper_session.headers.update(scraper_headers)

    post_list = []
    # 获取并清理每个缺少 Overview 的演员的信息
    for actor in blank_Overview_list:
        name = actor["Name"]
        print(f"正在处理: {name}")
        detail = get_av2ch_data(name, scraper_session)
        detail = clean_detail_data(detail)
        if detail is  not None:
            actor["Overview"] = str(detail)
            print(actor)
            print(post_data(jellyfin_userId,jellyfin_session,actor["Id"],actor))
        
    scraper_session.close()
    jellyfin_session.close()