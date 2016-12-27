# The Open edX Platform by INTEF
### MOOC.EDUCALAB.ES
### NOOC.EDUCALAB.ES
###SPOOC.EDUCALAB.ES 

[![Educalab](/educalab_linea.jpg](http://educalab.es)
[![Mooc INTEF](/logo_moocintef.png)](http://mooc.educalab.es)


**Powered By**

[![Open edX](/open_edX-logo.png)](https://open.edx.org/)
[![BeDjango](/BeDjango_logo.jpg)](http://www.bedjango.com/)

The code in this repository is the result of the adaptation of an open edx release based on the tag named-release/dogwood.1 ([SEE edx-platform repo](https://github.com/edx/edx-platform))

INTEF MOOC is a new Teacher Training model more focused on the development of competences, especially those related to collaboration through the net, management of autonomous learning and participation in educational communities. This new model of Teacher Training offered by INTEF intends to develop massive training processes based on open and social learning through activities that generate interaction, aggregated production, shared knowledge and the building of professional networks. In this sense, the MOOC experience presented here is designed as a social event for teachers who wish to share their learning experience.

The design of every MOOC created by INTEF will allow us to achieve the objectives initially planned through a combination of tasks, activities and contents to be addressed in an established time frame. The goal of INTEF MOOC is for every user to be able to develop self-sufficiency regarding digital environments, connect with professional communities and generate and share valuable content for his or her own community regarding the different topics covered in each MOOC. 

## Installation

You need a [fullstack dogwood instance](https://s3.amazonaws.com/edx-static/vagrant-images/20151221-dogwood-fullstack-rc2.box?torrent) of Open edX to install this repo.

Log in with edxapp user and activate the virtualenv
```sh
$ cd /edx/app/edxapp
$ source edxapp_en
```
Backup of the current edx-platform repo
```sh
$ mv edx-platform/ edx-platform-default/
```

Clone this repo in edx-platform
```sh
$ git clone https://github.com/BeDjango/intef-openedx edx-platform/
```
Override the next variables in your lms.env.json file

     "REGISTRATION_EXTRA_FIELDS": {
          "city": "optional",
          "country": "required",
          "gender": "hidden",
          "goals": "hidden",
          "honor_code": "required",
          "level_of_education": "optional",
          "mailing_address": "hidden",
          "year_of_birth": "optional",
          "comuni": "required",
          "esdoce": "required",
          "camp1": "optional",
          "camp2": "optional",
          "camp3": "optional",
          "camp4": "optional",
          "camp5": "optional"
      },
      ...
      "ENABLE_COMBINED_LOGIN_REGISTRATION": false,
      ...

Install node nodules
```sh
$ cd edx-platform/
$ npm install
```
Update the database model
```sh
  $  paver update_db
```
Update assets

```sh
$   paver update_assets lms --settings=aws
$   paver update_assets cms --settings=aws
```
9. Restart all services

```sh
   exit
   sudo /edx/bin/supervisorctl restart all
   sudo service nginx restart
```
## License
The code in this repository is licensed under version 3 of the AGPL
unless otherwise noted. Please see the `LICENSE`_ file for details.

SEE: [LICENSE](LICENSE)
