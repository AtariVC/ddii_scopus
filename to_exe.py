from pathlib import Path
import os
from kpa_async_pyqt_client.utils import cwd


def to_exe() -> None:
    icon: str = '--icon ' + str(cwd().joinpath('assets', 'settings.ico'))
    flags: list[str] = ["--name КПА_БДК2М_Клиент", "--console", "--onefile",
                        "--clean", "--noconfirm"]
    main_path: str = str(Path(__file__).parent.joinpath('__main__.py'))
    ui_paths: list[str] = ['--add-data ' + str(f"\"{file};.\"")
                           for file in Path(__file__).parent.glob("*.ui")]
    ba_kv_path: str = '--add-data ' + f'\"{str(Path(__file__).parent)};kpa_async_bdk2m_pyqt\"'
    pyqt_client_path: str = '--add-data ' + f'\"{str(cwd())};kpa_async_pyqt_client\"'

    destination: str = '--distpath ' + str(Path.cwd())
    to_exe_cmd: str = ' '.join(["pyinstaller", main_path,
                                *flags,
                                destination,
                                icon,
                                pyqt_client_path,
                                ba_kv_path,
                                *ui_paths,
                                ])
    # os.system(to_exe_cmd)
    for flag in to_exe_cmd.split('--'):
        print(f'--{flag}')

if __name__ == '__main__':
    # print(cwd())
    to_exe()