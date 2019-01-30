import click

FILE_BUF_SIZ = 32768
@click.command()
def one():
    print("cmd one")
    with open('/tmp/myfile', 'r+', FILE_BUF_SIZ) as f:
        for l in f.readlines():
            print(l, end='')
        print(dir(f))
        print(type(f).__name__)


@click.command()
def two():
    print("cmd two")


@click.group()
def cli():
    pass


for cmd in [one, two]:
    cli.add_command(cmd)


def main(args=None):
    print("main cli...")
    cli()


if __name__ == '__main__':
    main()

