import sys

from dumper import Dumper


def main():
    print('pin init')
    dumper = Dumper()
    print('ready')
    while True:
        line = sys.stdin.readline()
        if line[0:4] == 'dump':
            dumper.dump(*line[5:].split(' '))
        elif line == 'exit\n':
            break
        else:
            print(f'unknown command: {line[:-1]}')


if __name__ == '__main__':
    main()
