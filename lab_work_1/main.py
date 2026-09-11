import requests
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Конскольное приложение для поиска по архиву Common Crawl и вывода результатов',
        epilog='Пример: python main.py '
    )
    parser.add_argument('keywords', nargs='+', type=str, help='Одно или несколько ключевых слов для поиска')
    parser.add_argument('-d', '--domain', nargs='+', type=str, help='Фильтр по домену (например: pstu.ru)')
    parser.add_argument('-l', '--limit', type=int, default=10, help='Ограничение числа результатов (по умолчанию: 10)')
    parser.add_argument('-st', '--show-text', action='store_true', help='Загрузить и показать фрагмент текста страницы')
    args = parser.parse_args()
    print(f'{args.keywords=}')
    print(f'{args.domain=}')
    print(f'{args.limit=}')
    print(f'{args.show_text=}')


if __name__ == '__main__':
    main()