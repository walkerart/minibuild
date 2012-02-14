# CollectionSpace Minibuild
 Use this project to configure Collectionspace 2.0
 Collectionspace 2.0 will need to be installed


This project uses fabric to deploy to a remote machine 

*  First fork this project
*  then create a custom branch with
the fork may or may not come with a custom branch already
  `git checkout -b custom master`
*  Then edit the settings at the top of fabfile.py
*  use `fab -l` to see a list of commands to run 
*  push changes with `git push origin custom`
*  deploy with `fab deploy:ui`  or just `fab deploy`  instead of 
`fab deploy:application`
because the deploy task defaults to application
changes to the application layer should be immediate because of 
the hit_init fab task which logs into the server and initializes the 
configs

schema changes will need to be deployed with 
[Services](http://github.com/collectionspace/services)



