import logging
import requests

class CVATAPI(object):

    def __init__(self, server_host='localhost', server_port='8080', username='', password='', use_https=False):
        self.server_host = server_host
        self.server_port = server_port
        if (use_https):
            self.base_url = 'https://' + self.server_host + ':' + self.server_port + '/api/v1/'
        else:
            self.base_url = 'http://' + self.server_host + ':' + self.server_port + '/api/v1/'
        self.session = requests.Session()

        self.tasks = None

        # Login
        self.login(username=username, password=password)


    def url(self, relative_paths):
        return '/'.join(map(lambda x: x.rstrip('/'), [self.base_url] + relative_paths))
        # return self.server_host + ':' + self.server_port + '/api/v1/'

    def login(self, username='', password=''):
        url = self.url(['auth', 'login'])
        auth = {'username': username, 'password': password}
        response = self.session.post(url, auth)
        response.raise_for_status()
        if 'csrftoken' in response.cookies:
            self.session.headers['X-CSRFToken'] = response.cookies['csrftoken']

    def get_tasks(self, search='', task_id=None, name='', owner=None, mode=None, status=None, assignee=None, ordering=None):

        url = self.url(['tasks'])

        response = self.session.get(url)
        response.raise_for_status()
        page = 1
        tasks = []
        while True:
            response_json = response.json()
            for r in response_json['results']:
                tasks.append(task(self.session, r))
            if not response_json['next']:
                break
            page += 1
            url = self.url(['tasks']) + '?page=' + str(page)
            response = self.session.get(url)
            response.raise_for_status()

        self.tasks = tasks
        return tasks

    def create_task(self, name, labels, segment_size=0, overlap=0, z_order=False, bug_tracker='', project=None):
        # tasks_create
        url = self.url(['tasks'])

        data = {'name': name,
                'labels': labels,
                'overlap': overlap,
                'segment_size': segment_size,
                'z_order': z_order,
                'bug_tracker': bug_tracker
        }
        if project is not None:
            data['project'] = project

        response = self.session.post(url, json=data)
        response.raise_for_status()
        response_json = response.json()

        _task = task(self.session, response_json)

        if self.tasks is None:
            self.tasks = [_task]
        else:
            self.tasks.append(_task)

        return _task

    def get_task(self):
        # tasks_read
        raise NotImplementedError()
        pass

class task():

    def __init__(self, session, json):
        self.id = json['id']
        self.url = json['url']
        self.name = json['name']
        self.mode = json['mode']
        self.labels = json['labels']
        if 'size' in json:
            self.size = json['size']
        else:
            self.size = None
        self._json = json
        self._session = session

    def __str__(self):
        return 'Name: ' + self.name + ', url: ' + self.url

    def add_data(self, client_files=None, remote_files=None, share_files=None, image_quality=80):
        url = self.url + '/data'

        _files = [client_files, remote_files, share_files]

        if all([f is None for f in _files]):
            raise ValueError('Either client_files, remove_files and share_files must be specified.')
        if sum([f is not None for f in _files]) > 1:
            raise ValueError('Only one of either client_files, remove_files and share_files can be specified.')

        data = {}
        files = None
        if client_files is not None:
            files = {'client_files[{}]'.format(i): open(f, 'rb') for i, f in enumerate(client_files)}
        elif remote_files is not None:
            data = {'remote_files[{}]'.format(i): f for i, f in enumerate(remote_files)}
        elif share_files is not None:
            data = {'server_files[{}]'.format(i): f for i, f in enumerate(share_files)}
        data['image_quality'] = image_quality
        response = self._session.post(url, data=data, files=files)
        response.raise_for_status()




    def update(self):
        # tasks_update
        # tasks_partial?
        raise NotImplementedError()
        pass

    def delete(self):
        # tasks_delete
        raise NotImplementedError()
        pass

    def get_annotations(self):
        # tasks_annotations_read
        raise NotImplementedError()
        pass

    def update_annotations(self):
        # tasks_annotations_update
        # tasks_annotations_update_partial?
        raise NotImplementedError()
        pass

    def delete_annotations(self):
        # tasks_annotations_delete
        raise NotImplementedError()
        pass

    def get_data(self):
        # tasks_data_read
        raise NotImplementedError()
        pass

    def create_data(self):
        # tasks_data_create
        raise NotImplementedError()
        pass

    def get_data_info(self):
        # tasks_data_data_info
        raise NotImplementedError()
        pass

    def export_dataset(self):
        # task_dataset_export
        raise NotImplementedError()
        pass

    def get_jobs(self):
        # task_dataset_export
        raise NotImplementedError()
        pass

    def status(self):
        url = self.url + '/status'

        response = self._session.get(url)
        response.raise_for_status()

        return response.json()
