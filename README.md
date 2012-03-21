# CollectionSpace Minibuild
 Use this project to configure Collectionspace 2.0

 Collectionspace 2.0 will need to be installed

 as well as (fabric)[http://docs.fabfile.org/]
 _you will need to edit the variables at the top of fabfile.py_

## Using fabric to deploy to a remote machine

*  First fork this project
*  then create a custom branch with `git checkout -b custom master`
*  follow 
[these instructions](http://wiki.collectionspace.org/display/UNRELEASED/Creating+your+new+tenant+using+the+mini-build) using this repo instead of the svn repo suggested in the instructions

*  Then edit the settings at the top of fabfile.py
*  use `fab -l` to see a list of commands to run 
*  push changes with `git push origin custom`
*  deploy with `fab deploy:ui`  or `fab deploy:application`


deploy task defaults to application

to reload the application configs locally run `fab hit_init:hosts=localhost`

schema changes will need to be deployed with 
[Services](http://github.com/collectionspace/services)



## developing locally

the recommended directory structure is:
cspace/
        minibuild/
        services/
simlink minibuild/fabfile.py to services/fabfile.py for less cd'ing
after setting up the project and starting the server:

1. first do:
* `fab local_tenant_init` will login and hit the tenant init url

2. then:
* `fab local_auth_init`  will login and hit the authority/vocab init url

when extending an authority, 
and you want to see if the extension field gets created:
`fab test_authority:example,field_name=extention_field,hosts=localhost`
or for example:
`fab test_authority:location,field_name=gallery,hosts=localhost`
this does not work with the collectionobject service


compile changes locally with:
cd minibuild/application && ant deploy
cd minibuild/ui && ant deploy
cd services/services/[service-name] && ant deploy

