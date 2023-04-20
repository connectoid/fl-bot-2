from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from .models import Base, Vacancy, User, CategoryLink
from config_data.config import load_config, Config

config: Config = load_config()

database_url = f'postgresql://postgres:postgres@{config.db.db_host}:5432/{config.db.database}'

engine = create_engine(database_url, echo=False, pool_size=20, max_overflow=0)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def get_category_type(link: str):
    if link.startswith('https://www.fl.ru'):
        return 'fl'
    return 'freelance'


def add_user(tg_id):
    session = Session()
    user = session.query(User).filter(User.tg_id == tg_id).first()
    if user is None:
        new_user = User(tg_id=tg_id)
        session.add(new_user)
        session.commit()


def get_user_id(tg_id):
    session = Session()
    user = session.query(User).filter(User.tg_id == tg_id).first()
    return user.id


def add_vacancy(user_id, title, description, link):
    session = Session()
    vacancy = session.query(Vacancy).filter(Vacancy.title == title, Vacancy.owner == user_id).first()
    if vacancy is None:
        new_vacancy = Vacancy(title=title, description=description, link=link, owner=user_id)
        session.add(new_vacancy)
        session.commit()


def set_vacancy_reviewed(user_id, id):
    session = Session()
    vacancy = session.query(Vacancy).filter(Vacancy.id == id, Vacancy.owner == user_id).first()
    vacancy.is_new = False
    session.add(vacancy)
    session.commit()


def add_vacancy_to_favorite(user_id, id):
    session = Session()
    vacancy = session.query(Vacancy).filter(Vacancy.id == id, Vacancy.owner == user_id).first()
    vacancy.is_favorite = True
    session.add(vacancy)
    session.commit()


def remove_vacancy_from_favorite(user_id, id):
    session = Session()
    vacancy = session.query(Vacancy).filter(Vacancy.id == id, Vacancy.owner == user_id).first()
    vacancy.is_favorite = False
    session.add(vacancy)
    session.commit()


def get_new_vacancies():
    session = Session()
    vacancies = session.query(Vacancy).filter(Vacancy.is_new == True).all()
    for vacancy in vacancies:
        set_vacancy_reviewed(vacancy.owner, vacancy.id)
    return vacancies


def get_favorite_vacancies(user_id):
    session = Session()
    vacancies = session.query(Vacancy).filter(Vacancy.is_favorite == True, Vacancy.owner == user_id).all()
    return vacancies


def get_vavancy_link(id):
    session = Session()
    vacancy = session.query(Vacancy).filter(Vacancy.id == id).first()
    return vacancy.link


def category_exists(user_id, link) -> bool:
    session = Session()
    if session.query(CategoryLink).filter(CategoryLink.owner == user_id, CategoryLink.link == link).first():
        return True
    return False
    

def add_category_link(user_id, link, name) -> bool:
    session = Session()
    if not category_exists(user_id, link):
        print('=========', name)
        type = get_category_type(link)
        new_link = CategoryLink(name=name, link=link, owner=user_id, type=type)
        session.add(new_link)
        session.commit()
        return True
    return False


def clear_user_categories_list(user_id):
    session = Session()
    session.query(CategoryLink).filter(CategoryLink.owner == user_id).delete()
    session.commit()


def get_user_categories_list(user_id):
    categories_fl_list = []
    categories_freelance_list = []
    session = Session()
    user = session.query(User).filter(User.id == user_id).first()
    if user.fl_enable:
        categories_fl_list = session.query(CategoryLink).filter(
            CategoryLink.owner == user_id,
            CategoryLink.type == 'fl').all()
    if user.freelance_enable:
        categories_freelance_list = session.query(CategoryLink).filter(
            CategoryLink.owner == user_id,
            CategoryLink.type == 'freelance').all()
    categories_list = categories_fl_list + categories_freelance_list
    return categories_list


def check_categories(user_id):
    session = Session()
    category = session.query(CategoryLink).filter(CategoryLink.owner == user_id).first()
    if category:
        return True
    return False


def is_auto_enabled(user_id):
    session = Session()
    user = session.query(User).filter(User.id == user_id).first()
    if user.is_scheduled:
        return True
    return False


def set_plus_filters_list(category_link, filters_list):
    session = Session()
    category = session.query(CategoryLink).filter(CategoryLink.link == str(category_link)).first()
    category.plus_filters = filters_list
    session.add(category)
    session.commit()


def set_minus_filters_list(category_link, filters_list):
    session = Session()
    category = session.query(CategoryLink).filter(CategoryLink.link == str(category_link)).first()
    category.minus_filters = filters_list
    session.add(category)
    session.commit()


def get_plus_filters_list(category_link):
    filters_list = []
    session = Session()
    category = session.query(CategoryLink).filter(CategoryLink.link == str(category_link)).first()
    if category.plus_filters:
        filters_list = category.plus_filters.split(',')
    return filters_list


def get_minus_filters_list(category_link):
    filters_list = []
    session = Session()
    category = session.query(CategoryLink).filter(CategoryLink.link == str(category_link)).first()
    if category.minus_filters:
        filters_list = category.minus_filters.split(',')
    return filters_list


def switch_exchange_flag(user_id, exchange: str):
    session = Session()
    user = session.query(User).filter(User.id == user_id).first()
    if exchange == 'fl':
        user.fl_enable = not user.fl_enable
        session.add(user)
        session.commit()
        return user.fl_enable
    elif exchange == 'freelance':
        user.freelance_enable = not user.freelance_enable
        session.add(user)
        session.commit()
        return user.freelance_enable


def switch_freelance_flag(user_id):
    session = Session()
    user = session.query(User).filter(User.id == user_id).first()
    user.freelance_enable = not user.freelance_enable
    session.add(user)
    session.commit()
    return user.freelance_enable


def get_exchange_status(user_id, exchange: str):
    session = Session()
    user = session.query(User).filter(User.id == user_id).first()
    if exchange == 'fl':
        return user.fl_enable
    elif exchange == 'freelance':
        return user.freelance_enable


def get_status(user_id):
    session = Session()
    categories = get_user_categories_list(user_id)
    status_dict = {}
    if categories:
        cats_list = []
        for category in categories:
            full_category = []
            full_category.append(category)
            full_category.append(get_plus_filters_list(category))
            full_category.append(get_minus_filters_list(category))
            cats_list.append(full_category)
        status_dict['categories'] = cats_list
        user = session.query(User).filter(User.id == user_id).first()
        status_dict['fl_enabled'] = user.fl_enable
        status_dict['freelance_enabled'] = user.freelance_enable
        return status_dict
    return None


def get_category_name_by_link(category_link):
    session = Session()
    category_name = session.query(CategoryLink.name).filter(CategoryLink.link == str(category_link)).first()
    return category_name