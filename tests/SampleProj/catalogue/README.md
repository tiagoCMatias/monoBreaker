
### Migrate Database
`python manage.py makemigrations catalogue`

`python manage.py migrate catalogue`

### Sync Database with information (Only if needed)
`python manage.py loaddata catalogue/fixtures/*`

### Run Unit Tests
`coverage run manage.py test catalogue`

### Get Coverage Report in HTML
`coverage html`

### Install dependencies
activate virtualenv and then run `pip install -r requirements.txt`

### Run Server
`python manage.py runserver`


### Routes:
##### Catalogue:

```
GET: `http://localhost:8000/api/catalogue`
```



##### Category:

```
GET: `http://localhost:8000/api/category`
```