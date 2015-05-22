import csv
from website.app import init_app

alphabet = '23456789abcdefghijkmnpqrstuvwxyz'


def main():
    init_app(set_backends=True)
    generate_whitelist()


def generate_whitelist():
    whitelist = open('clean_guids.csv', 'wb')
    writer = csv.writer(whitelist)
    for a in alphabet:
        for b in alphabet:
            for c in alphabet:
                for d in alphabet:
                    for e in alphabet:
                        guid = a + b + c + d + e
                        writer.writerow([guid])


if __name__ == '__main__':
    main()