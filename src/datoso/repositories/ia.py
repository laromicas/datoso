"""
    Internet Archive Repository
"""
import os
from internetarchive import get_item


class InternetArchive:
    """ Internet Archive Wrapper. """
    dirs = set()
    path: str = None

    def __init__(self, url):
        self.url = url
        self.get_item()

    def get_item(self):
        """ Get the item from InternetArchive. """
        self.item = get_item(self.url)
        return self.item

    def get_download_path(self):
        """ Return the download path for files in InternetArchive item. """
        self.path = f"https://{self.item.item_metadata['d1']}{self.item.item_metadata['dir']}"
        return self.path

    def files_from_folder(self, folder):
        """ Return a list of files in a folder. """
        files = self.item.item_metadata['files']
        for file in files:
            if file['name'].startswith(f'{folder}/') or (folder in ('','/') and '/' not in file['name']):
                yield file

    def folders(self):
        """ Return a list of folders in InternetArchive item. """
        files = self.item.item_metadata['files']
        for file in files:
            self.dirs.add(f"{os.path.dirname(file['name'])}")
        return list(self.dirs)


if __name__ == "__main__":
    ia = InternetArchive("En-ROMs")
    for i in ia.files_from_folder("DATs"):
        print(i['name'])

    print(ia.folders())
    # , sizeof_fmt(i['size'])
    # print(json.dumps(ia.item.item_metadata, indent=4))
