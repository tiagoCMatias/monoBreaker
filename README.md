# MonoBreaker
[![Build Status](https://travis-ci.org/tiagoCMatias/monoBreaker.svg?branch=master)](https://travis-ci.org/tiagoCMatias/monoBreaker)

MonoBreaker: A tool to guide the process of decomposing monolithic Django application into microservices


## Requirements

The Django project analyzed by MonoBreaker must follow these requirements:

    Django: 1.8+
    Django REST framework: 3.5.1+
    Python: 3.6+
    
## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install MonoBreaker Dependencies.

```bash
pip install -r requirements.txt
```
In your Django Project use [django_extensions](https://github.com/django-extensions/django-extensions) and [Silk](https://github.com/jazzband/django-silk)  

Your `settings.py` should look like the following:
```python
MIDDLEWARE = [
    ...,
    'silk.middleware.SilkyMiddleware',
    ...
]

INSTALLED_APPS = (
    ...
    'rest_framework',
    'django_extensions',
    'silk'
)
```

## Usage

Extract the following information from your project using the following commands 
```text
python manage.py graph_models app_1 app_2 --json > models.json
python manage.py show_urls > urls.txt
```
Extract the following tables as CSV files from [Silk](https://github.com/jazzband/django-silk):

```text
silk_request
silk_sqlquery
```

Add the files to the source folder of you Django Project

Run MonoBreaker:
```text
Usage: python monoBreaker.py [options]

Options:
  -h, --help           show this help message and exit
  --pydir=PYDIR        Path to Django Project

Example: python monoBreaker.py --pydir=/Projects/DjangoProject
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.


## License
[MIT](https://choosealicense.com/licenses/mit/)
