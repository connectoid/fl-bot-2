import requests
import re

from rss_parser import Parser
from fake_useragent import UserAgent

from database.orm import (add_vacancy, get_new_vacancies,
                          set_vacancy_reviewed, add_vacancy_to_favorite,
                          get_user_categories_list, get_plus_filters_list, 
                          get_minus_filters_list, get_status, get_category_name_by_link
                          )
from lexicon.lexicon_ru import NO_ADDED_LINKS, NO_NEW_VACANCIES

rss_url = 'https://www.fl.ru/rss/all.xml?subcategory=37&category=5p'

categories_test = [
    'https://www.fl.ru/rss/all.xml?subcategory=279&category=5', # Программирование, разработка чат-ботов
    'https://www.fl.ru/rss/all.xml?subcategory=280&category=5', # Программирование, парсинг данных
    'https://www.fl.ru/rss/all.xml?subcategory=37&category=5', # Программирование, веб-программировние
]

freelance_cat_list = [
    'https://freelance.ru/rss/feed/list/s.116.f.635.677.5',
]


def check_filters_list(filters_list):
    if '\n' in filters_list:
        return False
    return True    


def get_feed(url):
    ua = UserAgent()
    fake_headers = {'user-agent': ua.random.strip()}

    session = requests.Session()
    session.headers.update(fake_headers)
    try:
        xml = session.get(url)
        parser = Parser(xml=xml.content, limit = 10)
        feed = parser.parse()
        return feed
    except AttributeError as error:
        print('Ошибка запроса, связи или неверная ссылка на категорию')
        return None


def get_category_name(category):
    feed = get_feed(category)
    if feed:
        category_name = feed.title
        print(category_name)
        return category_name
    return None


def get_vacancies(user_id, category):
    feed = get_feed(category)
    if feed:
        for item in feed.feed:
            print(item.description)
            print(get_plus_filters_list(category))
            print(get_minus_filters_list(category))
            plus_filters_list = get_plus_filters_list(category)
            minus_filters_list = get_minus_filters_list(category)
            description = item.description
            
            result1 = (any(map(lambda x: x in description, plus_filters_list)))
            result2 = not (any(map(lambda x: x in description, minus_filters_list)))
            print(result1, result2)
            if result1 and result2:
                title = item.title
                description = item.description
                link = item.link
                add_vacancy(user_id, title, description, link)


def update_vacancies(user_id, categories):
    for category in categories:
        get_vacancies(user_id, category)


def request_new_vacansies(user_id):
    categories = get_user_categories_list(user_id)
    new_vacancies_dict = {}
    if categories:
        update_vacancies(user_id, categories)
        new_vacancies = get_new_vacancies()
        if new_vacancies:
            for new_vacancy in new_vacancies:
                text = (f'Вакансия № {new_vacancy.id} \n'
                        f'<b>{new_vacancy.title}</b> \n'
                        f'<i>{new_vacancy.description}</i> \n'
                        f'{new_vacancy.link}')
                new_vacancies_dict[new_vacancy.id] = text
            return new_vacancies_dict
        else:
            return NO_NEW_VACANCIES
    else:
        return NO_ADDED_LINKS


def check_category_link(link: str) -> bool:
    pattern1 = re.compile(r'https://www.fl.ru/rss/all.xml\?subcategory=[0-9]+&category=[0-9]+')
    pattern2 = link.startswith('https://freelance.ru/rss/feed/list/')
    # print(pattern2)
    result = pattern1.match(link) or pattern2
    if result:
        return True
    return False

def get_status_message(user_id):
    status_dict = get_status(user_id)
    if status_dict:
        status_message_list = []
        for cat in status_dict['categories']:
            status_message_list.append(f'Категория: {cat[0]}')
            status_message_list.append(f'Фильтры: {cat[1]}')
            status_message_list.append(f'Минус-фильтры: {cat[2]}')
        status_message_list.append(f'fl.ru включен: {status_dict["fl_enabled"]}')
        status_message_list.append(f'freelance.ru включен: {status_dict["freelance_enabled"]}')
        status_message = ('\n').join(status_message_list)
        print(status_message)
        return status_message
    else:
        return NO_ADDED_LINKS


def prepare_category_name(category_name):
    if category_name[0].split()[0] == 'Заказы':
        return f'fl.ru: {category_name[0].split(":")[1][:-1]}'
    elif category_name[0].split()[0] == 'Freelance.Ru':
        return f'freelance.ru: {category_name[0].split("Проекты и вакансии")[1]}'
    return category_name[0]


def get_categories_list_menu(user_id):
    categories = get_user_categories_list(user_id)
    if categories:
        categories_list = []
        categories_list.append('Список категорий:')
        for category in categories:
            category_name = get_category_name_by_link(category)
            categories_list.append(prepare_category_name(category_name))
        text = '\n'.join(categories_list)
        return text
    return None
