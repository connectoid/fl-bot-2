from time import sleep
from aiogram import Router, Bot
from aiogram.filters import Command, CommandStart, Text, StateFilter
from aiogram.types import CallbackQuery, Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.filters import StateFilter
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.fsm.state import default_state


from services.vacancies import (update_vacancies, check_category_link, request_new_vacansies,
                                check_filters_list, get_status_message)
from services.parser import get_details
from keyboards.bottom_post_kb import create_bottom_keyboard
from database.orm import (add_vacancy_to_favorite, get_new_vacancies,
                          get_favorite_vacancies, remove_vacancy_from_favorite,
                          get_vavancy_link, add_user, get_user_id, add_category_link,
                          get_user_categories_list, clear_user_categories_list,
                          check_categories, set_minus_filters_list, set_plus_filters_list,
                          switch_fl_flag, switch_freelance_flag, get_status)
from lexicon.lexicon_ru import LEXICON_HELP, NO_ADDED_LINKS, NO_NEW_VACANCIES

REQUEST_INTERVAL = 60

router: Router = Router()
scheduler = AsyncIOScheduler()


class FSMAddCategory(StatesGroup):
    add_category_link = State()
    add_plus_filters_list = State()
    add_minus_filters_list = State()


@router.message(Command(commands='cancel'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    await message.answer(text='Вы вышли из диалога добавления категории\n\n'
                              'Чтобы снова перейти к добавлению - '
                              'отправьте команду /addcategory')
    await state.clear()


@router.message(Command(commands='cancel'), StateFilter(default_state))
async def process_cancel_command(message: Message):
    await message.answer(text='Отменять нечего. Вы вне диалога добавления категории\n\n'
                              'Чтобы перейти к дабавлению - '
                              'отправьте команду /addcategory')
    

@router.message(Command(commands='addcategory'), StateFilter(default_state))
async def process_fillform_command(message: Message, state: FSMContext):
    await message.answer(text='Пожалуйста, введите ссылку на категорию.\n'
                         'Если хотите прервать добавелние категории, введите команду /cancel')
    await state.set_state(FSMAddCategory.add_category_link)


@router.message(StateFilter(FSMAddCategory.add_category_link))
async def process_link_sent(message: Message, state: FSMContext):
    if check_category_link(message.text):
        await state.update_data(link=message.text)
        await message.answer(text='Спасибо!\n\nА теперь добавьте список ключевых слов (через запятую)')
        await state.set_state(FSMAddCategory.add_plus_filters_list)
    else:
        await message.answer(text='Неправильная ссылка (не соотвтетствует ссылке на RSS fl.ru или freelance.ru)\n'
                             'Введите правильную ссылку на категорию')


@router.message(StateFilter(FSMAddCategory.add_plus_filters_list))
async def process_plus_sent(message: Message, state: FSMContext):
    if check_filters_list(message.text):
        await state.update_data(plus_list=message.text)
        await message.answer(text='Спасибо!\n\nА теперь добавьте список минус слов (через запятую)')
        await state.set_state(FSMAddCategory.add_minus_filters_list)
    else:
        await message.answer(text='Неправильный список')


@router.message(StateFilter(FSMAddCategory.add_minus_filters_list))
async def process_minus_sent(message: Message, state: FSMContext):
    if check_filters_list(message.text):
        await state.update_data(minus_list=message.text)
        user_data = await state.get_data()
        await state.clear()
        await message.answer(text='Спасибо!\n\nКатегория и списки добавлены')
        user_id = get_user_id(message.from_user.id)
        # print(user_data)
        if add_category_link(user_id, user_data['link']):
            set_plus_filters_list(user_data['link'], user_data['plus_list'])
            set_minus_filters_list(user_data['link'], user_data['minus_list'])
        else:
            await message.answer(text='Эта категория уже добавлена')
    else:
        await message.answer(text='Неправильный список')


@router.message(CommandStart())
async def process_start_command(message: Message):
    add_user(message.from_user.id)
    user_id = get_user_id(message.from_user.id)
    await message.answer(text='Вы запустили бот fl-bot')
    if not check_categories(user_id):
        await message.answer(text=NO_ADDED_LINKS)


@router.message(Command(commands='startpolling'))
async def start_polling(message: Message):
    if not scheduler.get_jobs():
        scheduler.add_job(
                process_request_new_vacancies_silent,
                'interval',
                seconds=REQUEST_INTERVAL,
                args=(message,),
                id='process_request_new_vacancies_silent'
            )
        scheduler.start()
        await message.answer(text='Автоматический опрос вакансий включен')
    else:
        await message.answer(text='Автоматический опрос вакансий уже работает')
      

@router.message(Command(commands='stoppolling'))
async def stop_polling(message: Message):
    if scheduler.get_jobs():
        scheduler.remove_job('process_request_new_vacancies_silent')
        scheduler.shutdown()
        await message.answer(text='Автоматический опрос вакансий выключен')
    else:
        await message.answer(text='Автоматический опрос вакансий пока не включен')


@router.message(Command(commands='help'))
async def process_help_command(message: Message):
    await message.answer(text=LEXICON_HELP, disable_web_page_preview=True)


@router.message(Command(commands='get'))
async def process_get_vacancies_command(message: Message):
    await message.answer(text='Запрашиваю новые вакансии')
    update_vacancies()


@router.message(Command(commands='request'))
async def process_request_new_vacancies_command(message: Message):
    user_id = get_user_id(message.from_user.id)
    result = request_new_vacansies(user_id)
    if isinstance(result, dict):
        for id, text in result.items():
            await message.answer(text=text, reply_markup=create_bottom_keyboard(
                        id,
                        'Подробно', '⭐️ В избранное'),
                        parse_mode='HTML')
    else:
        await message.answer(text=result)


async def process_request_new_vacancies_silent(message: Message):
    user_id = get_user_id(message.from_user.id)
    result = request_new_vacansies(user_id)
    if isinstance(result, dict):
        for id, text in result.items():
            await message.answer(text=text, reply_markup=create_bottom_keyboard(
                        id,
                        'Подробно', '⭐️ В избранное'),
                        parse_mode='HTML')


@router.message(Command(commands='favorite'))
async def process_post_favorite_vacancies_command(message: Message):
    user_id = get_user_id(message.from_user.id)
    favorite_vacancies = get_favorite_vacancies(user_id)
    if favorite_vacancies:
        await message.answer(text='Избранные вакансии:')
        for vavorite_vacancy in favorite_vacancies:
            text = (f'Вакансия № {vavorite_vacancy.id} \n'
                    f'<b>{vavorite_vacancy.title}</b> \n'
                    f'<i>{vavorite_vacancy.description}</i> \n'
                    f'{vavorite_vacancy.link}')
            await message.answer(text=text, reply_markup=create_bottom_keyboard(
                    vavorite_vacancy.id,
                    'Подробно', '❎ Из избранного'),
                    parse_mode='HTML')
    else:
        await message.answer(text='Нет избранных вакансий')


@router.callback_query(Text(startswith='⭐️ В избранное'))
async def process_add_to_favorite(callback: CallbackQuery):
    id = callback.data.split('_')[-1]
    user_id = get_user_id(callback.from_user.id)
    add_vacancy_to_favorite(user_id, id)
    await callback.answer(text='Вакансия добавлена в Избранное')
    await callback.message.edit_reply_markup(reply_markup=create_bottom_keyboard(
                    id, 'Подробно', '❎ Из избранного'))
    await callback.answer()


@router.callback_query(Text(startswith='❎ Из избранного'))
async def process_remove_from_favorite(callback: CallbackQuery):
    id = callback.data.split('_')[-1]
    user_id = get_user_id(callback.from_user.id)
    remove_vacancy_from_favorite(user_id, id)
    await callback.answer(text='Вакансия удалена из Избранного')
    await callback.message.edit_reply_markup(reply_markup=create_bottom_keyboard(
                    id, 'Подробно', '⭐️ В избранное'))
    await callback.answer()


@router.callback_query(Text(startswith='Подробно'))
async def process_details(callback: CallbackQuery):
    id = callback.data.split('_')[-1]
    link = get_vavancy_link(id)
    details = get_details(link)
    text = f'<b>Подробное описание вакансии №{id}</b> \n <i>{details}</i>'
    await callback.message.answer(text=text)


@router.message(Command(commands='clearcategories'))
async def process_clearlinks_command(message: Message):
    user_id = get_user_id(message.from_user.id)
    clear_user_categories_list(user_id)
    await message.answer(text='Список категорий очищен')


@router.message(Command(commands='showcategories'))
async def process_showlinks_command(message: Message):
    user_id = get_user_id(message.from_user.id)
    categories = get_user_categories_list(user_id)
    if categories:
        categories_list = []
        for category in categories:
            categories_list.append(str(category))
        text = '\n'.join(categories_list)
        await message.answer(text=text)
    else:
        await message.answer(text=NO_ADDED_LINKS)


@router.message(Command(commands='fl_switch'))
async def process_fl_switch(message: Message):
    user_id = get_user_id(message.from_user.id)
    is_switched = switch_fl_flag(user_id)
    if is_switched:
        await message.answer(text='Проверка по сайту fl.ru включена')
    else:
        await message.answer(text='Проверка по сайту fl.ru отключена')


@router.message(Command(commands='freelance_switch'))
async def process_fl_switch(message: Message):
    user_id = get_user_id(message.from_user.id)
    is_switched = switch_freelance_flag(user_id)
    if is_switched:
        await message.answer(text='Проверка по сайту freelance.ru включена')
    else:
        await message.answer(text='Проверка по сайту freelance.ru отключена')


@router.message(Command(commands='getstatus'))
async def process_get_status(message: Message):
    user_id = get_user_id(message.from_user.id)
    text = get_status_message(user_id)
    await message.answer(text=text)


@router.message(Command(commands='delmenu'))
async def del_main_menu(message: Message, bot: Bot):
    await bot.delete_my_commands()
    await message.answer(text='Кнопка "Menu" удалена')
