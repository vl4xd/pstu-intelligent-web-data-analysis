
import argparse

from collectors.potd import (
    PictureOfTheDayCollector,
    POTDError
)


def main():
    parser = argparse.ArgumentParser(
        description="Получение Picture of the Day из Wikimedia Commons"
    )

    parser.add_argument(
        "--output",
        default="output/potd",
        help="Папка для сохранения изображения и описания"
    )

    args = parser.parse_args()

    try:
        collector = PictureOfTheDayCollector()

        picture = collector.get_picture()

        collector.save_picture(
            picture,
            output_dir=args.output
        )

        print("\nPicture of the Day успешно получено!")

    except POTDError as error:
        print(f"\n[ОШИБКА] {error}")


if __name__ == "__main__":
    main()
