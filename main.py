import requests
import json
from datetime import datetime
import ydisk

OK_CODES = [200, 201]

class VKPhoto:

    def __init__(self, photo_data):
        self.sizes = photo_data['sizes']
        self.count_of_likes = photo_data['likes']['count']
        self.creation_date = datetime.fromtimestamp(photo_data['date'])
        self.file_name = ''

    def get_max_size(self) -> map:
        max_photo = {'height': 0, 'width': 0}
        max_type_pos, sorted_types = 0, 'smxopqryzw'

        for size in self.sizes:
            if size['height'] == 0 and size['width'] == 0:
                # фото залито ранее 2012 г., ориентируемся на type
                pos = sorted_types.find(size['type'])
                if pos > max_type_pos:
                    max_type_pos = pos
                    max_photo = size
            elif size['height'] > max_photo['height'] and size['width'] > max_photo['width']:
                max_photo = size

        return max_photo

    def set_file_name(self, incl_date=False):
        if incl_date:
            f_date = self.creation_date.strftime('%Y.%m.%d')
            self.file_name = f"{self.count_of_likes}_{f_date}.jpg"
        else:
            self.file_name = f'{self.count_of_likes}.jpg'

    def get_saving_data(self):
        max_size = self.get_max_size()
        photo_data = {
            'file_name': self.file_name,
            'size': max_size['type']
        }
        return photo_data

class VKPhotoSaver:
    CLIENT_ID = '7543688'  # идентификатор приложения
    API_VERSION = '5.120'
    VK_DIR = '/VKPhotos'

    def __init__(self, user_id, album_id = 'profile'):
        self.user_id = user_id
        self.album_id = album_id
        self.dir_path = f'{self.VK_DIR}/id_{self.user_id}/album_{self.album_id}'
        self.photos_list = []

    def __update_photos(self, album_data: map, photos_limit: int):

        result = {'error': False, 'msg': ''}
        if not 'response' in album_data.keys():
            result['error'] = True
            result['msg'] = album_data
            return result

        photos_by_likes = {
            # count_of_likes: count_of_photos,
        }
        for photo_data in album_data['response']['items']:
            if len(self.photos_list) >= photos_limit:
                break

            vk_photo = VKPhoto(photo_data)
            self.photos_list.append(vk_photo)
            photos_by_likes.setdefault(vk_photo.count_of_likes, 0)
            photos_by_likes[vk_photo.count_of_likes] += 1

        # формирование имен файлов
        for vk_photo in self.photos_list:
            date_incl = (photos_by_likes[vk_photo.count_of_likes]>1)
            vk_photo.set_file_name(date_incl)

    def load(self, access_token, photos_limit = 5):

        self.photos_list.clear()

        result = {
            'error': False,
            'count': 0, # количество фотографий, по которым загружены данные с VK
            'msg': ''
        }

        params = {
            'owner_id': self.user_id,
            'album_id': 'profile',
            'extended': 1,
            'rev':1,
            'v': VKPhotoSaver.API_VERSION,
            'access_token': access_token
        }
        print('Получение сведений VK о фотографиях пользователя')
        response = requests.get('https://api.vk.com/method/photos.get', params=params)

        if not response.status_code in OK_CODES:
             result['error'] = True
             result['msg'] = response.headers

        self.__update_photos(json.loads(response.text), photos_limit)
        result['count'] = len(self.photos_list)
        return result

    def save(self, ydisk: ydisk.YDiskClient):

        count = len(self.photos_list)
        if count == 0:
            print('Нет фотографий для загрузки на Яндекс.Диск')
            return


        dir_path = self.VK_DIR
        if not ydisk.path_exists(dir_path):
            ydisk.create_dir(dir_path)

        dir_path += f'/user_id_{self.user_id}'
        if not ydisk.path_exists(dir_path):
            ydisk.create_dir(dir_path)

        dir_path += f'/album_id_{self.album_id}'
        if not ydisk.path_exists(dir_path):
            ydisk.create_dir(dir_path)

        print(f'Начало загрузки фотографий на Яндекс.Диск в каталог: {dir_path}')

        saving_list = []
        for vk_photo in self.photos_list:
            print(f"Загрузка фотографии {len(saving_list)+1} из {count}")
            max_size = vk_photo.get_max_size()
            ydisk.upload_from_url(max_size['url'], path = f'{dir_path}/{vk_photo.file_name}')
            saving_list.append(vk_photo.get_saving_data())

        data = json.dumps(saving_list, indent=4)
        ydisk.upload(f'{dir_path}/photos.json', data=data)

        self.photos_list.clear()

if __name__ == '__main__':
    #with open("access_token.txt") as tokenfile:
    #    ydisk_token = tokenfile.read().strip()

    vk_access_token = '958eb5d439726565e9333aa30e50e0f937ee432e927f0dbd541c541887d919a7c56f95c04217915c32008'

    vk_user_id = input('Введите идентификатор пользователя VK: ')
    ydisk_token = input('Введите токен Яндекс.Диска: ')

    saver = VKPhotoSaver(vk_user_id)
    result = saver.load(vk_access_token)
    if result['error']:
        print(result['msg'])
    else:
        try:
            saver.save(ydisk=ydisk.YDiskClient(ydisk_token))
        except Exception as e:
            print(e)



